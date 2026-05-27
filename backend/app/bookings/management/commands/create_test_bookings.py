from datetime import date
import random
from typing import Any, Optional

from django.db import transaction
from django.db.models import QuerySet
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandParser
from django.utils.timezone import timedelta
from faker import Faker

from app.accounts.models import Guest, Moderator
from app.bookings.models import Booking, Review
from app.bookings.utils.helpers.faker_providers import BookingProvider, ReviewProvider
from app.hotels.models import Room


User = get_user_model()


class Command(BaseCommand):
    help = 'Генерирует тестовые записи о бронировании'
    _DEFAULT_PAST_DAYS = 365 * 3
    _DEFAULT_FUTURE_DAYS = 365 * 2

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--bookings',
            '-b',
            type=int,
            default=10,
            help='Количество бронирований (по умолчанию 10)',
        )
        parser.add_argument(
            '--with-reviews',
            '-r',
            action='store_true',
            help='Всем сгенерированным закрытым бронированиям добавить отзывы',
        )

    def handle(self, *_args: Any, **options: Any) -> Optional[str]:
        bookings_count: int = options.get('bookings')
        with_reviews: bool = options.get('with_reviews')

        faker = Faker('ru_RU')
        rooms = Room.objects.filter(hotel__is_active=True)
        guests = Guest.objects.all()
        if not guests:
            self.stdout.write(self.style.ERROR('Нет пользователей с ролью Гость'))
            return
        bookings = self._create_bookings(
            BookingProvider(faker), rooms,
            guests, bookings_count
        ) if bookings_count > 0 else []

        if not bookings:
            self.stdout.write(self.style.WARNING(
                'Бронирования не были сгенерированы, переданное количество: '
                f'"{bookings_count}".'
            ))

        if not with_reviews:
            return

        if not bookings:
            self.stdout.write(self.style.WARNING('Будут взяты существующие для отзывов'))
            closed_bookings = Booking.objects.filter(
                status=Booking.Status.CLOSED, review__isnull=True
            )
            if not closed_bookings.exists():
                self.stdout.write(self.style.ERROR(
                    'Нет доступных бронирований для создания отзывов'
                ))
                return
        else:
            closed_bookings = [b for b in bookings if b.status == Booking.Status.CLOSED]

        moderators = Moderator.objects.all()
        reviews = self._create_reviews(ReviewProvider(faker), closed_bookings, moderators)

        if not reviews:
            self.stdout.write(self.style.WARNING('Отзывы не были сгенерированы'))

    def _get_status_distribution(self, count: int) -> dict:
        active = max(round(count * 0.5), 1)
        remaining = count - active
        closed = min(round(count * 0.3), remaining)
        remaining -= closed
        cancelled = min(round(count * 0.1), remaining)
        remaining -= cancelled
        moved = min(round(count * 0.1), remaining)
        return {
            Booking.Status.ACTIVE: active,
            Booking.Status.CLOSED: closed,
            Booking.Status.CANCELLED: cancelled,
            Booking.Status.MOVED: moved,
        }

    def _adjust_booking_to_room(self, data: dict, room: Room) -> dict:
        if not room.is_pets_allowed and data['pets_count'] != 0:
            data['pets_count'] = 0
        if room.bed_count < (data['adults_count'] + data['children_count']):
            data['children_count'] = 0
            if data['adults_count'] > room.bed_count:
                data['adults_count'] = room.bed_count
        return data

    def _get_valid_dates(
        self, generator: BookingProvider, booked: list[tuple[date, date]],
        later: date | None = None, before: date | None = None
    ) -> tuple[date, date]:
        today = date.today()
        later = later or (today - timedelta(days=self._DEFAULT_PAST_DAYS))
        before = before or (today + timedelta(days=self._DEFAULT_FUTURE_DAYS))
        relevant = sorted(
            (c_in, c_out) for c_in, c_out in booked
            if c_in < before or c_out > later
        )
        gaps = []

        if not relevant:
            gaps.append((later, before))
        else:
            gaps.append((later, relevant[0][0]))
            for (_, prev_out), (next_in, _) in zip(relevant, relevant[1:]):
                if (next_in - prev_out).days >= 1:
                    gaps.append((prev_out, next_in))
            gaps.append((relevant[-1][1], before))

        for gap_start, gap_end in gaps:
            try:
                period = generator.period(gap_start, gap_end)
                booked.append(period)
                return period
            except ValueError:
                continue

        raise RuntimeError(
            f'Не удалось найти свободные даты (период: {later}, {before})'
        )

    def _get_booked_periods(self, rooms_qs: QuerySet[Room]) -> dict[int, list[tuple[date, date]]]:
        statuses = [Booking.Status.ACTIVE, Booking.Status.CLOSED]
        bookings = Booking.objects.filter(room__in=rooms_qs, status__in=statuses) \
            .values_list('room_id', 'check_in_date', 'check_out_date')
        periods = {}
        for room in rooms_qs:
            periods[room.pk] = []
        for room_id, check_in, check_out in bookings:
            periods[room_id].append((check_in, check_out))
        return periods

    def _create_booking(
        self, generator: BookingProvider, room: Room,
        guest: Guest, status: str,
        booked: list[tuple[date, date]],
        later: date | None = None, before: date | None = None
    ) -> Booking:
        data = generator.booking()
        data = self._adjust_booking_to_room(data, room)
        dates = self._get_valid_dates(generator, booked, later, before)
        data['check_in_date'], data['check_out_date'] = dates
        data['status'] = status
        return Booking(guest=guest, room=room, **data)

    def _create_bookings(
        self, generator: BookingProvider, rooms_qs: QuerySet[Room],
        guests: list[Guest], count: int
    ) -> list[Booking]:
        status_distribution = self._get_status_distribution(count)
        active_count = status_distribution[Booking.Status.ACTIVE]
        closed_count = status_distribution[Booking.Status.CLOSED]
        cancelled_count = status_distribution[Booking.Status.CANCELLED]
        moved_count = status_distribution[Booking.Status.MOVED]

        rooms = list(rooms_qs)
        booked_periods = self._get_booked_periods(rooms_qs)
        new_bookings = []

        active_count += cancelled_count
        for _ in range(active_count):
            room = random.choice(rooms)
            guest = random.choice(guests)
            booked = booked_periods[room.pk]
            new_bookings.append(self._create_booking(
                generator, room, guest, Booking.Status.ACTIVE, booked, later=date.today()
            ))

        for _ in range(closed_count):
            room = random.choice(rooms)
            guest = random.choice(guests)
            booked = booked_periods[room.pk]
            new_bookings.append(self._create_booking(
                generator, room, guest, Booking.Status.CLOSED, booked, before=date.today()
            ))

        for booking in new_bookings:
            booking.full_clean()

        with transaction.atomic():
            created_bookings = Booking.objects.bulk_create(new_bookings)
            active_bookings = [b for b in created_bookings if b.status == Booking.Status.ACTIVE]

            for booking in active_bookings:
                if cancelled_count > 0:
                    booking.cancel(generator.cancellation_reason())
                    cancelled_count -= 1
                elif moved_count > 0:
                    booked = booked_periods[booking.room.pk]
                    original_period = (booking.check_in_date, booking.check_out_date)
                    if original_period in booked:
                        booked.remove(original_period)
                    check_in, check_out = self._get_valid_dates(
                        generator, booked, later=booking.check_out_date
                    )
                    booking.move(check_in, check_out)
                    moved_count -= 1
                if cancelled_count < 0 and moved_count < 0:
                    break

        for booking in created_bookings:
            self.stdout.write(self.style.SUCCESS(f'Создано {booking}'))

        return created_bookings

    def _create_reviews(
        self, generator: ReviewProvider, bookings: list[Booking],
        moderators: list[Moderator]
    ) -> list[Review]:
        new_reviews = []

        for booking in bookings:
            review_data = generator.review()
            if not moderators:
                review_data['status'] = Review.Status.DRAFT
                review_data.pop('published_at', None)
                review_data.pop('rejection_reason', None)
            elif review_data['status'] != Review.Status.DRAFT:
                review_data['moderated_by'] = random.choice(moderators)
            new_reviews.append(Review(booking=booking, **review_data))

        created_reviews = Review.objects.bulk_create(new_reviews)

        for review in created_reviews:
            self.stdout.write(self.style.SUCCESS(f'Создан {review}'))

        return created_reviews
