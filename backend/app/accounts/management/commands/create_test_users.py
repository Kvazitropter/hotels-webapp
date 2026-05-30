import random
from typing import Any, Optional

from decouple import config
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandParser
from faker import Faker

from app.accounts.models import Guest, Moderator, Administrator
from utils.normalizers import normalize_email, normalize_phone
from utils.validators import validate_email, validate_phone


fake = Faker('ru_RU')
User = get_user_model()
ROLE_MODEL_MAP = {
    User.Role.GUEST: Guest,
    User.Role.MODERATOR: Moderator,
    User.Role.ADMIN: Administrator,
}


class Command(BaseCommand):
    help = 'Генерирует тестовых пользователей с разными ролями'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--users',
            '-u',
            type=int,
            default=5,
            help='Количество пользователей для создания (по умолчанию 5)'
        )
        parser.add_argument(
            '--role',
            '-r',
            type=str,
            choices=(User.Role.GUEST, User.Role.MODERATOR, User.Role.ADMIN),
            default=User.Role.GUEST,
            help='Роль создаваемых пользователей (по умолчанию Гость)'
        )

    def handle(self, *_args: Any, **options: Any) -> Optional[str]:
        user_count: int = options['users']
        role: str = options['role']

        self._create_users(user_count, role)
        return None

    def _get_unique_email(self, existing_emails: set) -> str:
        email = normalize_email(fake.email())
        while email in existing_emails or not validate_email(email):
            email = normalize_email(fake.email())
        existing_emails.add(email)
        return email

    def _get_unique_phone(self, existing_phones: set) -> str:
        phone = normalize_phone(fake.phone_number())
        while phone in existing_phones or not validate_phone(phone):
            phone = normalize_phone(fake.phone_number())
        existing_phones.add(phone)
        return phone

    def _get_fullname_for_gender(self, gender: str) -> tuple[str, str, str]:
        if gender == 'male':
            first_name = fake.first_name_male()
            middle_name = fake.middle_name_male()
            last_name = fake.last_name_male()
        else:
            first_name = fake.first_name_female()
            middle_name = fake.middle_name_female()
            last_name = fake.last_name_female()
        return first_name, middle_name, last_name

    def _create_user(self, existing_emails: dict, existing_phones: dict) -> User:
        gender = random.choice(['male', 'female'])
        first_name, middle_name, last_name = self._get_fullname_for_gender(gender)
        date_of_birth = fake.date_of_birth(minimum_age=18)

        user = User(
            email=self._get_unique_email(existing_emails),
            phone_number=self._get_unique_phone(existing_phones),
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
        )
        user.set_password(config('TEST_USER_PASSWORD', default='qwert543@'))
        return user 

    def _create_users(self, user_count: int, role: str) -> None:
        RoleModel = ROLE_MODEL_MAP[role]
        existing_emails = set(User.objects.values_list('email', flat=True))
        existing_phones = set(User.objects.values_list('phone_number', flat=True))
        new_users = []

        for _ in range(user_count):
            new_users.append(self._create_user(existing_emails, existing_phones))

        with transaction.atomic():
            created_users = User.objects.bulk_create(new_users)
            roles = [RoleModel(user=user) for user in created_users]
            RoleModel.objects.bulk_create(roles)

        for user in created_users:
            self.stdout.write(self.style.SUCCESS(
                f'Создан пользователь: {user.full_name}, email: {user.email}, '
                f'телефон: {user.phone_number}, дата рождения: {user.date_of_birth}, '
                f'роль: {role}'
            ))
