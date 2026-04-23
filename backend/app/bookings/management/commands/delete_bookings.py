from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandParser

from app.bookings.models import Booking
from utils.validators import validate_lookup_str, validate_lookup_params
from utils.parsers import parse_lookup


class Command(BaseCommand):
    help = 'Удаляет данные о бронированиях.'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--booking-lookup',
            type=str,
            default='',
            help='Фильтрация бронирований: параметр1=значение1,параметр2=значение2'
        )

    def handle(self, *_args: Any, **options: Any) -> Optional[str]:
        booking_lookup: str = options['booking_lookup']

        is_valid, error_msg = validate_lookup_str(booking_lookup)
        if not is_valid:
            self.stderr.write(error_msg)
            return

        booking_lookup_params = parse_lookup(booking_lookup)
        if not booking_lookup_params:
            confirm = input(self.style.WARNING('Удалить все бронирования? [y/n]: '))
            if confirm.lower() != 'y' and confirm.lower() != 'yes':
                self.stdout.write('Отменено')
                return

        is_valid, wrong, suggestions = validate_lookup_params(Booking, booking_lookup_params)
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

        self._delete_bookings(booking_lookup_params)

    def _delete_bookings(self, booking_lookup_params: dict) -> None:
        bookings = Booking.objects.filter(**booking_lookup_params)

        if not bookings.exists():
            self.stdout.write(self.style.WARNING('Нет бронирований для удаления'))
            return

        for booking in bookings:
            self.stdout.write(self.style.WARNING(str(booking)))

        confirm = input(self.style.NOTICE('Удалить перечисленные бронирования? [y/n]: '))
        if confirm.lower() != 'y' and confirm.lower() != 'yes':
            self.stdout.write('Отменено')
            return

        bookings.delete()
        self.stdout.write(self.style.SUCCESS('Бронирования удалены'))
