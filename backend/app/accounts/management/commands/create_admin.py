from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandParser
from django.conf import settings
from django.contrib.auth import get_user_model
from app.accounts.models import Group
from utils.validators import validate_email, validate_phone


User = get_user_model()


class Command(BaseCommand):
    help = 'Создает пользователя с правами администратора'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--admin-name',
            '-n',
            type=str,
            help='Фамилия Имя (Отчество) суперпользователя'
        )
        parser.add_argument(
            '--admin-email',
            '-e',
            type=str,
            help='Email суперпользователя'
        )
        parser.add_argument(
            '--admin-phone',
            '-ph',
            type=str,
            help='Номер телефона суперпользователя'
        )
        parser.add_argument(
            '--admin-pswd',
            '-ps',
            type=str,
            help='Пароль суперпользователя'
        )
        parser.add_argument(
            '--admin-group',
            '-g',
            type=str,
            default=settings.ADMIN_GROUP_NAME,
            help='Группа, в которую добавить суперпользователя(по умолчанию '
            f'берется из settings.ADMIN_GROUP_NAME, текущее значение: {settings.ADMIN_GROUP_NAME})'
        )

    def handle(self, *_args: Any, **options: Any) -> Optional[str]:
        admin_name: Optional[str] = options.get('admin_name')
        admin_email: Optional[str] = options.get('admin_email')
        admin_phone: Optional[str] = options.get('admin_phone')
        admin_password: Optional[str] = options.get('admin_pswd')
        admin_group: Optional[str] = options.get('admin_group')

        group = None
        if admin_group is not None:
            try:
                group = Group.objects.get(name=admin_group)
            except Group.DoesNotExist:
                self.stderr.write(
                    f'Группы "{admin_group}" не существует. Создание суперпользователя'
                    ' отменено.'
                )
                return

        self._create_admin(
            admin_name, admin_email, admin_phone, admin_password, group
        )
        return None

    def _create_admin(
        self,
        admin_name: Optional[str],
        admin_email: Optional[str],
        admin_phone: Optional[str],
        admin_password: Optional[str],
        admin_group: Optional[Group],
    ) -> None:
        if not all([admin_name, admin_email, admin_phone, admin_password]):
            self.stderr.write(
                'Для создания администратора необходимо указать: '
                '--admin-name, --admin-email, --admin-phone, --admin-pswd'
            )
            return

        if not validate_email(admin_email):
            self.stderr.write(
                f'Email {admin_email} не является валидным'
            )
            return

        if not validate_phone(admin_phone):
            self.stderr.write(
                f'Номер телефона {admin_phone} не является валидным'
            )
            return

        names = admin_name.split(maxsplit=2)

        if len(names) == 2:
            last_name, first_name = names
            middle_name = None
        elif len(names) == 3:
            last_name, middle_name, first_name = names
        else:
            self.stdout.write(self.style.ERROR(
                '--admin-name должно содержать фамилию имя (отчество) через пробел, '
                'например "Иванов Иван" или "Иванов Иван Иванович"'
            ))
            return

        existing_data = []
        if User.objects.filter(email=admin_email).exists():
            existing_data.append(f'email {admin_email}')
        if User.objects.filter(phone_number=admin_phone).exists():
            existing_data.append(f'номером телефона {admin_phone}')

        if existing_data:
            self.stdout.write(self.style.WARNING(
                f'Пользователь с {" или/и ".join(existing_data)} уже существует. '
                'Создание администратора пропущено.'
            ))
            return

        try:
            admin = User.objects.create_superuser(
                email=admin_email,
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                phone_number=admin_phone,
                password=admin_password
            )
            if admin_group:
                admin.groups.add(admin_group)
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'Не удалось создать суперпользователя: {e}'
            ))
            return

        self.stdout.write(self.style.SUCCESS(
            f'Создан суперпользователь ФИ: {admin.full_name}, email: {admin.email}, '
            f'номер телефона: {admin.phone_number}, пароль: {admin_password}, роль: {admin.role}'
        ))
