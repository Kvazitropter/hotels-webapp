from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandParser
from django.contrib.auth import get_user_model

from utils.validators import validate_lookup_str, validate_lookup_params
from utils.parsers import parse_lookup


User = get_user_model()


class Command(BaseCommand):
    help = 'Удаляет данные о пользователях'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--user-lookup',
            '-l',
            type=str,
            default='',
            help='Фильтрация пользователей: параметр1=значение1,параметр2=значение2'
        )

    def handle(self, *_args: Any, **options: Any) -> Optional[str]:
        user_lookup: str = options['user_lookup']

        is_valid, error_msg = validate_lookup_str(user_lookup)
        if not is_valid:
            self.stdout.write(self.style.ERROR(error_msg))
            return

        user_lookup_params = parse_lookup(user_lookup)
        if not user_lookup_params:
            confirm = input(self.style.WARNING('Удалить всех пользователей? [y/n]: '))
            if confirm.lower() != 'y' and confirm.lower() != 'yes':
                self.stdout.write('Отменено')
                return

        is_valid, wrong, suggestions = validate_lookup_params(User, user_lookup_params)
        if not is_valid:
            for field in wrong:
                simular = suggestions.get(field, [])
                if simular:
                    self.stdout.write(self.style.ERROR(
                        f'Поле "{field}" не существует. '
                        f'Возможно, вы имели в виду: {", ".join(simular)}?'
                    ))
                else:
                    self.stdout.write(self.style.ERROR(f'Поле "{field}" не существует.'))
            return

        self._delete_users(user_lookup_params)

    def _delete_users(self, user_lookup_params: dict) -> None:
        users = User.objects.filter(**user_lookup_params)

        if not users.exists():
            self.stdout.write(self.style.WARNING('Нет пользователей для удаления'))
            return

        for user in users:
            self.stdout.write(self.style.WARNING(str(user)))

        if user_lookup_params:
            confirm = input(self.style.NOTICE('Удалить перечисленных пользователей? [y/n]: '))
            if confirm.lower() != 'y' and confirm.lower() != 'yes':
                self.stdout.write('Отменено')
                return

        users.delete()
        self.stdout.write(self.style.SUCCESS('Пользователи удалены'))
