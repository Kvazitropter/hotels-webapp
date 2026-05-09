from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import BlacklistedToken, OutstandingToken, RefreshToken

from app.accounts.permissions import AdminOnly, GuestOnly, ModeratorOnly
from app.accounts.serializers import (
    AdministratorSerializer,
    AssignRoleSerializer,
    ContactChangeConfirmSerializer,
    ContactChangeRequestSerializer,
    GuestSerializer,
    MeSerializer,
    ModeratorSerializer,
    ResetPasswordConfirmSerializer,
    ResetPasswordRequestSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)


User = get_user_model()


class AdminViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.filter(admin__isnull=False).select_related('admin')
    serializer_class = AdministratorSerializer
    permission_classes = [IsAuthenticated, AdminOnly]
    filterset_fields = ['is_active']
    search_fields = ['email', 'phone_number', 'last_name']
    ordering_fields = ['email', 'last_name', 'last_login']


class GuestViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.filter(guest__isnull=False).select_related('guest') \
        .prefetch_related('guest__bookings')
    serializer_class = GuestSerializer
    permission_classes = [IsAuthenticated, (ModeratorOnly|AdminOnly)]
    filterset_fields = ['is_active', 'guest__bookings__status']
    search_fields = ['email', 'phone_number', 'last_name']
    ordering_fields = ['email', 'last_name', 'last_login']


class ModeratorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.filter(moderator__isnull=False).select_related('moderator')
    serializer_class = ModeratorSerializer
    permission_classes = [IsAuthenticated, (ModeratorOnly|AdminOnly)]
    filterset_fields = ['is_active']
    search_fields = ['email', 'phone_number', 'last_name']
    ordering_fields = ['email', 'last_name', 'last_login']


class MeView(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
):
    serializer_class = MeSerializer

    def get_object(self):
        return User.objects.select_related('guest', 'moderator', 'admin') \
            .prefetch_related('guest__bookings').get(pk=self.request.user.pk)

    def get_permissions(self):
        if self.action == 'confirm_change':
            return [AllowAny()]
        if self.action == 'retrieve':
            return [IsAuthenticated()]
        return [IsAuthenticated(), GuestOnly()]

    @action(detail=False, methods=['delete'])
    @transaction.atomic
    def deactivate(self, request):
        request.user.is_active = False
        request.user.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['patch'])
    def request_change(self, request):
        serializer = ContactChangeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        change_type, new_value, uid, token = serializer.save(user=request.user)

        confirm_url = f"{settings.FRONTEND_URL}/me/confirm-change?uid={uid}&token={token}"

        if change_type == 'email':
            recipient = new_value
            subject = 'Подтверждение смены email'
        else:
            recipient = request.user.email
            subject = 'Подтверждение смены номера телефона'

        send_mail(
            subject=subject,
            message=f'Для подтверждения перейдите по ссылке: {confirm_url}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
        )
        return Response(
            {'detail': f'Письмо с подтверждением отправлено на {recipient}'},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['patch'])
    @transaction.atomic
    def confirm_change(self, request):
        serializer = ContactChangeConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        pending = serializer.validated_data['pending']

        if pending['change_type'] == 'email':
            user.email = pending['new_value']
            user.save(update_fields=['email'])
        else:
            user.phone_number = pending['new_value']
            user.save(update_fields=['phone_number'])

        cache.delete(f'contact_change:{user.pk}')
        return Response({'detail': 'Данные успешно обновлены'}, status=status.HTTP_200_OK)


class UserViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, AdminOnly]
    queryset = User.objects.all()

    @action(detail=True, methods=['post'], url_path='assign-role')
    def assign_role(self, request, pk):
        user = self.get_object()
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        role = serializer.validated_data['role']

        try:
            user.assign_role(role=role)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {'detail': f'Роль "{role}" успешно добавлена пользователю {user.email}.'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['delete'], url_path='remove-role')
    def remove_role(self, request, pk):
        user = self.get_object()
        role = request.data.get('role')

        try:
            user.remove_role(role=role)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, pk):
        user = self.get_object()

        if not user.is_active:
            return Response(
                {'detail': 'Аккаунт уже неактивен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response(
            {'detail': 'Аккаунт успешно деактивирован'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, pk):
        user = self.get_object()

        if user.is_active:
            return Response(
                {'detail': 'Аккаунт уже активен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_active = True
        user.save(update_fields=['is_active'])
        return Response(
            {'detail': 'Аккаунт успешно активирован'},
            status=status.HTTP_200_OK
        )


class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = ResetPasswordRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email, is_active=True)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"

            send_mail(
                subject='Сброс пароля',
                message=f'Для сброса пароля перейдите по ссылке: {reset_url}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )
        except User.DoesNotExist:
            pass

        return Response(
            {'detail': 'Если такой email зарегистрирован, письмо отправлено.'},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = ResetPasswordConfirmSerializer
    permission_classes = [AllowAny]

    @transaction.atomic()
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])

        tokens = OutstandingToken.objects.filter(user=user)
        for token in tokens:
            BlacklistedToken.objects.get_or_create(token=token)

        return Response(
            {'detail': 'Пароль успешно изменён.'},
            status=status.HTTP_200_OK,
        )


class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user, context=self.get_serializer_context()).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)


class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'detail': 'Необходимо передать refresh токен.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh_token).blacklist()
        except (TokenError, InvalidToken):
            return Response(
                {'detail': 'Токен недействителен или уже отозван.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
