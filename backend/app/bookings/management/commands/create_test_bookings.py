import random
from typing import Any, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandParser
from faker import Faker

from app.accounts.models import Group, User
from app.bookings.models import Booking, Review
from app.bookings.utils.helpers.faker_providers import BookingProvider, ReviewProvider
from app.bookings.utils.helpers.calculate_total_price import calculate_total_price
from app.hotels.models import Room


class Command(BaseCommand):
    help = 'Генерирует тестовые записи о бронировании'
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--bookings',
            '-b',
            type=int,
            default=5,
            help='Количество бронирований (по умолчанию 5)',
        )
        parser.add_argument(
            '--reviews',
            '-r',
            type=int,
            default=5,
            help='Количество отзывов (по умолчанию 5)',
        )

    def handle(self, *_args: Any, **options: Any) -> Optional[str]:
        bookings_count: int = options.get('bookings')
        reviews_count: int = options.get('reviews')

        faker = Faker('ru_RU')
        rooms = Room.objects.all()
        users = Group.objects.get(name=settings.USER_GROUP_NAME).user_set.all()
        bookings = self._create_bookings(
            BookingProvider(faker), rooms,
            users, bookings_count
        )

        if not bookings:
            msg = (
                'Бронирования не были сгенерированы, переданное количество: '
                f'"{bookings_count}".'
            )
            if reviews_count > 0:
                msg += ' Будут взяты существующие.'
            self.stdout.write(self.style.WARNING(msg))
            bookings = Booking.objects.all()
            if not bookings.exists():
                self.stderr.write(
                    'Нет доступных бронирований.'
                )
                return

        moderators = User.objects.filter(is_staff=True)
        closed_bookings = [
            b for b in bookings
            if b.status == Booking.Status.CLOSED and not hasattr(b, 'review')
        ]
        reviews = self._create_reviews(
            ReviewProvider(faker), closed_bookings,
            moderators, reviews_count
        )

        if not reviews:
            msg = (
                'Отзывы не были сгенерированы, переданное количество: '
                f'"{reviews_count}".'
            )
            self.stdout.write(self.style.WARNING(msg))

    def _create_bookings(
        self, generator: BookingProvider, rooms: list[Room],
        users: list[User], count: int
    ) -> list[Booking]:
        new_bookings = []

        for _ in range(count):
            room = random.choice(rooms)
            user = random.choice(users)
            booking_data = generator.booking()
            booking_data['total_price'] = calculate_total_price(
                days=(booking_data['check_out_date'] - booking_data['check_in_date']).days,
                adults_count=booking_data['adults_count'],
                children_count=booking_data['children_count'],
                room_capacity=room.room_type.capacity,
                base_price=room.price_per_night,
                extra_person_price=room.extra_pay_per_person,
            )
            new_bookings.append(Booking(user=user, room=room, **booking_data))

        created_bookings = Booking.objects.bulk_create(new_bookings)

        for booking in created_bookings:
            self.stdout.write(self.style.SUCCESS(
               f'Создано {booking}'
            ))

        return created_bookings

    def _create_reviews(
        self, generator: ReviewProvider, bookings: list[Booking],
        moderators: list[User], count: int
    ) -> list[Review]:
        new_reviews = []

        if count > len(bookings):
            self.stdout.write(self.style.WARNING(
                f'Переданное количество отзывов "{count}" больше, чем '
                f'количество доступных бронирований: {len(bookings)}.'
                'Каждому бронированию будет добавлено по одному отзыву.'
            ))
            count = len(bookings)

        for i in range(count):
            review_data = generator.review()
            print(review_data)
            if (review_data['status'] == Review.Status.PUBLISHED
                    or review_data['status'] == Review.Status.REJECTED):
                review_data['moderated_by'] = random.choice(moderators)
                print(review_data)
            new_reviews.append(Review(booking=bookings[i], **review_data))

        created_reviews = Review.objects.bulk_create(new_reviews)

        for review in created_reviews:
            self.stdout.write(self.style.SUCCESS(
               f'Создан {review}'
            ))

        return created_reviews
