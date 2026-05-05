from django.db import transaction
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers

from utils.validators import validate_email, validate_phone
from utils.normalizers import normalize_email, normalize_phone


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    short_name = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = (
            'email', 'phone_number', 'first_name', 'middle_name', 'last_name', 'full_name',
            'short_name', 'date_of_birth', 'last_login', 'date_joined', 'password', 'role'
        )
        read_only_fields = ('full_name', 'short_name', 'last_login', 'date_joined', 'role')


class GuestSerializer(UserSerializer):
    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        user.assign_role(User.Role.GUEST)
        return user


class ModeratorSerializer(UserSerializer):
    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        user.assign_role(User.Role.MODERATOR)
        return user


class AdministratorSerializer(UserSerializer):
    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        user.assign_role(User.Role.ADMIN)
        return user


class MeSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        read_only_fields = UserSerializer.Meta.read_only_fields + ('email', 'phone_number')


class _ConfirmLinkSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)

    def validate(self, data):
        try:
            uid = force_str(urlsafe_base64_decode(data['uid']))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError) as e:
            raise serializers.ValidationError({'uid': 'Недействительная ссылка'}) from e

        if not default_token_generator.check_token(user, data['token']):
            raise serializers.ValidationError({'token': 'Токен недействителен или истёк'})

        data['user'] = user
        return data


class ResetPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        if not validate_email(value):
            raise serializers.ValidationError('Не является валидным email')
        return normalize_email(value)


class ResetPasswordConfirmSerializer(_ConfirmLinkSerializer):
    new_password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError(
                {'new_password_confirm': 'Пароли не совпадают'}
            )

        return super().validate(data)


class ContactChangeRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(required=False, max_length=20)

    def validate_email(self, value):
        if not validate_email(value):
            raise serializers.ValidationError('Не является валидным email')
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Этот email уже используется')
        return normalize_email(value)

    def validate_phone_number(self, value):
        if not validate_phone(value):
            raise serializers.ValidationError('Не является валидным номером телефона')
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError('Этот номер уже используется')
        return normalize_phone(value)

    def validate(self, data):
        if not data.get('email') and not data.get('phone_number'):
            raise serializers.ValidationError('Укажите email или номер телефона')
        if data.get('email') and data.get('phone_number'):
            raise serializers.ValidationError('Изменяйте email и телефон по отдельности')
        return data

    def save(self, user):
        if self.validated_data.get('email'):
            change_type = 'email'
            new_value = self.validated_data['email']
        else:
            change_type = 'phone'
            new_value = str(self.validated_data['phone_number'])

        cache.set(
            key=f'contact_change:{user.pk}',
            value={'change_type': change_type, 'new_value': new_value},
            timeout=settings.PASSWORD_RESET_TIMEOUT,
        )

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        return change_type, new_value, uid, token


class ContactChangeConfirmSerializer(_ConfirmLinkSerializer):
    def validate(self, data):
        data = super().validate(data)
        user = data['user']

        pending = cache.get(f'contact_change:{user.pk}')
        if not pending:
            raise serializers.ValidationError('Ссылка недействительна или истекла')

        data['pending'] = pending
        return data


class AssignRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.Role.choices, required=True)

    def validate(self, data):
        role = data['role']
        if role not in User.Role.values:
            raise serializers.ValidationError(f'Невозможно присвоить пользователю роль "{role}"')
        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            'email', 'first_name', 'last_name',
            'phone_number', 'password', 'password_confirm'
        )

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Пользователь с таким email уже существует')
        return value

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError('Номер телефона уже используется')
        return value

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Пароли не совпадают'})
        return data

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        user.assign_role(User.Role.GUEST)
        return user
