import random
from typing import Any, Optional

from django.db import transaction
from django.core.management.base import BaseCommand, CommandParser
from django.conf import settings
from django.contrib.auth import get_user_model
from app.accounts.models import Group
from faker import Faker

from utils.normalizers import normalize_email, normalize_phone
from utils.validators import validate_email, validate_phone


User = get_user_model()
fake = Faker('ru_RU')


class Command(BaseCommand):
    help = 'Генерирует тестовых пользователей'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--users',
            '-u',
            type=int,
            default=5,
            help='Количество обычных пользователей для создания (по умолчанию 5)'
        )
        parser.add_argument(
            '--group',
            '-g',
            type=str,
            default=settings.USER_GROUP_NAME,
            help='Группа, в которую добавить пользователей (по умолчанию '
            f'берется из settings.USER_GROUP_NAME, текущее значение: {settings.USER_GROUP_NAME})'
        )

    def handle(self, *_args: Any, **options: Any) -> Optional[str]:
        user_count: int = options.get('users')
        user_group: Optional[str] = options.get('group')

        group = None
        if user_group:
            try:
                group = Group.objects.get(name=user_group.strip())
            except Group.DoesNotExist:
                self.stderr.write(
                    f'Группы "{user_group}" не существует. Создание пользователей'
                    ' отменено.'
                )
                return

        self._create_users(user_count, group)
        return None

    def _create_users(self, user_count: int, group: Optional[Group]) -> None:
        existing_emails = set(User.objects.values_list('email', flat=True))
        existing_phones = set(User.objects.values_list('phone_number', flat=True))
        new_users = []

        for _ in range(user_count):
            email = normalize_email(fake.email())
            while email in existing_emails or not validate_email(email):
                email = normalize_email(fake.email())
            existing_emails.add(email)

            phone = normalize_phone(fake.phone_number())
            while phone in existing_phones or not validate_phone(phone):
                phone = normalize_phone(fake.phone_number())
            existing_phones.add(phone)

            gender = random.choice(['male', 'female'])
            if gender == 'male':
                first_name = fake.first_name_male()
                middle_name = fake.middle_name_male()
                last_name = fake.last_name_male()
            else:
                first_name = fake.first_name_female()
                middle_name = fake.middle_name_female()
                last_name = fake.last_name_female()
            date_of_birth = fake.date_of_birth(minimum_age=18)
            password = 'qwert543'

            user = User(
                email=email,
                phone_number=phone,
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                date_of_birth=date_of_birth
            )
            user.set_password(password)

            new_users.append(user)

        with transaction.atomic():
            User.objects.bulk_create(new_users)
            if group:
                group.user_set.add(*new_users)

        for user in new_users:
            self.stdout.write(self.style.SUCCESS(
                f'Создан пользователь {user.full_name}, email {user.email},'
                f' пароль {password}, номер телефона {user.phone_number}, '
                f'дата рождения {user.date_of_birth}, роль: {user.role}'
            ))
