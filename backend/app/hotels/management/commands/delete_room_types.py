from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandParser

from app.hotels.models import RoomType
from utils.validators import validate_lookup_str, validate_lookup_params
from utils.parsers import parse_lookup


class Command(BaseCommand):
    help = 'Удаляет данные об типах номеров.'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--room-type-lookup',
            type=str,
            default='',
            help='Фильтрация типов: параметр1=значение1,параметр2=значение2'
        )

    def handle(self, *_args: Any, **options: Any) -> Optional[str]:
        room_type_lookup: str = options['room_type_lookup']

        is_valid, error_msg = validate_lookup_str(room_type_lookup)
        if not is_valid:
            self.stderr.write(error_msg)
            return

        room_type_lookup_params = parse_lookup(room_type_lookup)
        if not room_type_lookup_params:
            confirm = input(self.style.WARNING('Удалить все типы? [y/n]: '))
            if confirm.lower() != 'y' and confirm.lower() != 'yes':
                self.stdout.write('Отменено')
                return

        is_valid, wrong, suggestions = validate_lookup_params(RoomType, room_type_lookup_params)
        if not is_valid:
            for field in wrong:
                simular = suggestions.get(field, [])
                if simular:
                    self.stderr.write(
                        f'Поле "{field}" не существует. '
                        f'Возможно, вы имели в виду: {", ".join(simular)}?'
                    )
                else:
                    self.stderr.write(f'Поле "{field}" не существует.')
            return

        self._delete_room_types(room_type_lookup_params)

    def _delete_room_types(self, room_type_lookup_params: dict) -> None:
        room_types = RoomType.objects.filter(**room_type_lookup_params)

        if not room_types.exists():
            self.stdout.write(self.style.WARNING('Нет типов для удаления'))
            return

        for room_type in room_types:
            self.stdout.write(self.style.WARNING(str(room_type)))

        confirm = input(self.style.NOTICE('Удалить перечисленные типы? [y/n]: '))
        if confirm.lower() != 'y' and confirm.lower() != 'yes':
            self.stdout.write('Отменено')
            return

        room_types.delete()
        self.stdout.write(self.style.SUCCESS('Типы удалены'))
