from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandParser

from app.hotels.models import Hotel
from utils.validators import validate_lookup_str, validate_lookup_params
from utils.parsers import parse_lookup


class Command(BaseCommand):
    help = 'Удаляет данные об отелях.'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--hotel-lookup',
            type=str,
            default='',
            help='Фильтрация отелей: параметр1=значение1,параметр2=значение2'
        )

    def handle(self, *_args: Any, **options: Any) -> Optional[str]:
        hotel_lookup: str = options['hotel_lookup']

        is_valid, error_msg = validate_lookup_str(hotel_lookup)
        if not is_valid:
            self.stderr.write(error_msg)
            return

        hotel_lookup_params = parse_lookup(hotel_lookup)
        if not hotel_lookup_params:
            confirm = input(self.style.WARNING('Удалить все отели? [y/n]: '))
            if confirm.lower() != 'y' and confirm.lower() != 'yes':
                self.stdout.write('Отменено')
                return

        is_valid, wrong, suggestions = validate_lookup_params(Hotel, hotel_lookup_params)
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

        self._delete_hotels(hotel_lookup_params)

    def _delete_hotels(self, hotel_lookup_params: dict) -> None:
        hotels = Hotel.objects.filter(**hotel_lookup_params)

        if not hotels.exists():
            self.stdout.write(self.style.WARNING('Нет отелей для удаления'))
            return

        for hotel in hotels:
            self.stdout.write(self.style.WARNING(str(hotel)))

        confirm = input(self.style.NOTICE('Удалить перечисленные отели? [y/n]: '))
        if confirm.lower() != 'y' and confirm.lower() != 'yes':
            self.stdout.write('Отменено')
            return

        hotels.delete()
        self.stdout.write(self.style.SUCCESS('Отели удалены'))
