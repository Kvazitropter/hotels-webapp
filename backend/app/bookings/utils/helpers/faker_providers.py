from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Optional

from faker import Faker
from faker.providers import BaseProvider

from app.bookings.models import Booking, Review


class BookingProvider(BaseProvider):
    '''Кастомный Faker-провайдер для генерации данных модели Booking'''

    def __init__(self, generator: Faker):
        super().__init__(generator)
        self._status_choices = Booking.Status.values
        self._pay_status_choices = Booking.PaymentStatus.values

    def adults_count(self) -> int:
        return self.generator.random_int(min=1, max=10)

    def children_count(self) -> int:
        return self.generator.random_int(min=0, max=5)

    def pets_count(self) -> int:
        return self.generator.random_int(min=0, max=3)

    def check_in_date(self, created_at: Optional[datetime]=None) -> datetime:
        if created_at is None:
            return self.generator.date_time_this_year()
        days = self.generator.random_int(min=1, max=30)
        return created_at + timedelta(days=days)

    def check_out_date(self, check_in_date: Optional[datetime]=None) -> datetime:
        if check_in_date is None:
            return self.generator.date_time_this_year()
        days = self.generator.random_int(min=1, max=30)
        return check_in_date + timedelta(days=days)

    def status(self) -> str:
        return self.generator.random_element(self._status_choices)

    def payment_status(self) -> str:
        return self.generator.random_element(self._pay_status_choices)

    def created_at(self, check_in_date: Optional[datetime]=None) -> datetime:
        if check_in_date is None:
            return self.generator.date_time_this_year()
        days = self.generator.random_int(min=1, max=7)
        return check_in_date - timedelta(days=days)

    def cancelled_at(
        self, created_at: Optional[datetime]=None,
        check_in_date: Optional[datetime]=None,
    ) -> Optional[datetime]:
        return self.generator.date_time_between_dates(
            datetime_start=created_at, datetime_end=check_in_date
        )

    def cancellation_reason(self) -> str:
        return self.generator.text(max_nb_chars=255)

    def booking(self) -> dict:
        created_at = self.created_at()
        check_in_date = self.check_in_date(created_at)
        check_out_date = self.check_out_date(check_in_date)
        status = self.status()
        cancelled_at = None
        cancellation_reason = None
        if status == Booking.Status.CANCELLED:
            cancelled_at = self.cancelled_at(created_at, check_in_date)
            cancellation_reason = self.cancellation_reason()
        return {
            'adults_count': self.adults_count(),
            'children_count': self.children_count(),
            'pets_count': self.pets_count(),
            'check_in_date': check_in_date,
            'check_out_date': check_out_date,
            'status': status,
            'payment_status': self.payment_status(),
            'created_at': created_at,
            'cancelled_at': cancelled_at,
            'cancellation_reason': cancellation_reason,
        }


class ReviewProvider(BaseProvider):
    '''Кастомный Faker-провайдер для генерации данных модели Review'''

    def __init__(self, generator: Faker):
        super().__init__(generator)
        self._status_choices = Review.Status.values
        self._rating_choices = OrderedDict([
            (5, 0.5),
            (4, 0.25),
            (3, 0.1),
            (2, 0.15)
        ])

    def rating(self) -> int:
        return self.generator.random_element(elements=self._rating_choices)

    def comment(self) -> str:
        return self.generator.text(max_nb_chars=3072)

    def created_at(self) -> datetime:
        return self.generator.date_time_this_year()

    def status(self) -> str:
        return self.generator.random_element(self._status_choices)

    def rejection_reason(self) -> str:
        return self.generator.text(max_nb_chars=255)

    def published_at(self, later_than: Optional[datetime]=None) -> datetime:
        if later_than is not None:
            return later_than + timedelta(days=self.generator.random_int(min=1, max=7))
        return self.generator.date_time_this_year()

    def review(self) -> dict:
        created_at = self.created_at()
        status = self.status()
        published_at = None
        rejection_reason = None
        if status == Review.Status.PUBLISHED:
            published_at = self.published_at(created_at)
        if status == Review.Status.REJECTED:
            rejection_reason = self.rejection_reason()
        return {
            'rating': self.rating(),
            'comment': self.comment(),
            'created_at': created_at,
            'status': status,
            'rejection_reason': rejection_reason,
            'published_at': published_at,
        }
