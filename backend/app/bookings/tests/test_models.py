from decimal import Decimal
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from app.bookings.models import Booking, BookingPayment, CancelledBooking, Review
from app.hotels.models import Hotel, Room, RoomCategory, RoomType


User = get_user_model()


class BookingModelTest(TestCase):
    def setUp(self):
        self.hotel = Hotel.objects.create(
            name='Тестовый Отель',
            phone_number='+79123456789',
            email='hotel@example.com',
            country='Тестия',
            city='Тестов',
            address='ул. Тест, д. 1',
            floor_count=5,
            is_active=True,
        )
        self.standard_category = RoomCategory.objects.create(
            tier=RoomCategory.Tier.FIRST,
            min_area=10,
            requires_kitchen=False,
            required_bathroom_type=RoomCategory.BathroomType.PARTIAL,
            min_rooms=1,
        )
        self.standard_room_type = RoomType.objects.create(
            name='Стандартный Двухместный',
            category=self.standard_category,
            description='Описание стандартного номера',
            size=20,
            standard_capacity=2,
            bedroom_count=1,
            living_room_count=0,
            bathroom_count=1,
            bathroom_type=RoomCategory.BathroomType.PARTIAL,
            has_kitchen=False,
        )
        self.room = Room.objects.create(
            hotel=self.hotel,
            room_type=self.standard_room_type,
            bed_count=2,
            price_per_night=Decimal('100.00'),
            extra_pay_per_person=Decimal('20.00'),
            is_pets_allowed=True,
            is_smoking_allowed=True,
            floor=2,
            number_on_floor=5,
            variant='A',
        )
        self.user = User.objects.create_user(
            email='guest@example.com',
            first_name='Guest',
            last_name='Test',
            phone_number='+79333333333',
            password='GoodPassword432+'
        )
        self.user.assign_role(role=User.Role.GUEST)
        self.guest = self.user.guest

        self.booking_data = {
            'room': self.room,
            'guest': self.guest,
            'adults_count': 1,
            'children_count': 1,
            'pets_count': 1,
            'check_in_date': date(2000, 1, 1),
            'check_out_date': date(2000, 1, 7),
        }

    def test_create_booking_success(self):
        booking = Booking.objects.create(**self.booking_data)
        self.assertEqual(booking.guest, self.guest)
        self.assertEqual(booking.room, self.room)
        self.assertEqual(booking.adults_count, self.booking_data['adults_count'])
        self.assertEqual(booking.children_count, self.booking_data['children_count'])
        self.assertEqual(booking.pets_count, self.booking_data['pets_count'])
        self.assertEqual(booking.check_in_date, self.booking_data['check_in_date'])
        self.assertEqual(booking.check_out_date, self.booking_data['check_out_date'])
        self.assertEqual(booking.status, Booking.Status.ACTIVE)
        self.assertEqual(booking.type, Booking.Type.GUARANTEED)
        self.assertIsNotNone(booking.created_at)
        self.assertIsNotNone(booking.updated_at)
        expected_days_count = (
            self.booking_data['check_out_date'] - self.booking_data['check_in_date']
        ).days
        self.assertEqual(booking.days_count, expected_days_count)

    def test_booking_updated_at_sets_when_updated(self):
        updated_at = timezone.now() - timedelta(days=1)
        booking = Booking.objects.create(
            **self.booking_data, updated_at=updated_at
        )
        booking.type = Booking.Type.NOT_GUARANTEED
        booking.save(update_fields=['type'])
        self.assertNotEqual(booking.updated_at, updated_at)
        self.assertTrue(booking.updated_at > updated_at)

    def test_booking_clean_validates_check_out_after_check_in(self):
        booking_data = self.booking_data.copy()
        booking_data['check_in_date'] = self.booking_data['check_out_date']
        booking_data['check_out_date'] = self.booking_data['check_in_date']
        booking = Booking(**booking_data)
        with self.assertRaises(ValidationError):
            booking.full_clean()

    def test_booking_requires_active_hotel(self):
        self.hotel.is_active = False
        self.hotel.save()
        booking = Booking(**self.booking_data)
        with self.assertRaises(ValidationError):
            booking.full_clean()

    def test_booking_clean_validates_pets_allowed(self):
        self.room.is_pets_allowed = False
        self.room.save()
        booking = Booking(**self.booking_data)
        with self.assertRaises(ValidationError):
            booking.full_clean()

    def test_booking_clean_validates_guest_capacity(self):
        booking_data = self.booking_data.copy()
        booking_data['adults_count'] += 1
        booking = Booking(**booking_data)
        with self.assertRaises(ValidationError):
            booking.full_clean()

        booking_data['adults_count'] -= 1
        booking_data['children_count'] += 1
        booking = Booking(**booking_data)
        with self.assertRaises(ValidationError):
            booking.full_clean()

    def test_booking_cancel_success(self):
        booking = Booking.objects.create(**self.booking_data)
        reason = 'Teстовая отмена'
        booking.cancel(reason)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)
        cancelled = CancelledBooking.objects.filter(booking=booking).first()
        self.assertIsNotNone(cancelled)
        self.assertEqual(cancelled.cancellation_reason, reason)
        self.assertIsNotNone(cancelled.cancelled_at)

    def test_booking_cancel_already_cancelled_raises_error(self):
        booking = Booking.objects.create(**self.booking_data)
        reason = 'Teстовая отмена'
        booking.cancel(reason)
        booking.refresh_from_db()
        with self.assertRaises(ValueError):
            booking.cancel('Повторная отмена')

    def test_booking_move_creates_new_booking(self):
        booking = Booking.objects.create(**self.booking_data)
        new_check_in = booking.check_in_date + timedelta(days=5)
        new_check_out = new_check_in + timedelta(days=3)
        booking.move(new_check_in, new_check_out)

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.MOVED)
        self.assertIsNotNone(booking.moved_to)
        new_booking = booking.moved_to
        self.assertEqual(new_booking.guest, booking.guest)
        self.assertEqual(new_booking.room, booking.room)
        self.assertEqual(new_booking.adults_count, booking.adults_count)
        self.assertEqual(new_booking.pets_count, booking.pets_count)
        self.assertEqual(new_booking.check_in_date, new_check_in)
        self.assertEqual(new_booking.check_out_date, new_check_out)
        self.assertEqual(new_booking.status, Booking.Status.ACTIVE)

    def test_booking_move_closed_raises_error(self):
        booking_data = self.booking_data.copy()
        booking = Booking.objects.create(
            **booking_data, status=Booking.Status.CLOSED
        )

        new_check_in = booking.check_in_date + timedelta(days=5)
        new_check_out = new_check_in + timedelta(days=3)
        with self.assertRaises(ValueError):
            booking.move(new_check_in, new_check_out)

    def test_booking_move_cancelled_raises_error(self):
        booking = Booking.objects.create(**self.booking_data)
        booking.cancel('Причина')

        new_check_in = booking.check_in_date + timedelta(days=5)
        new_check_out = new_check_in + timedelta(days=3)
        with self.assertRaises(ValueError):
            booking.move(new_check_in, new_check_out)

    def test_booking_move_moved_raises_error(self):
        booking = Booking.objects.create(**self.booking_data)
        new_check_in = booking.check_in_date + timedelta(days=5)
        new_check_out = new_check_in + timedelta(days=3)
        booking.move(new_check_in, new_check_out)

        with self.assertRaises(ValueError):
            booking.move(
                new_check_in + timedelta(days=1),
                new_check_out + timedelta(days=1)
            )

    def test_booking_constraint_moved_to_required_when_status_moved(self):
        booking = Booking.objects.create(**self.booking_data)
        booking.status = Booking.Status.MOVED
        with self.assertRaises(ValidationError):
            booking.save(update_fields=['status'])

    def test_overlapping_check_in_inside_already_booked_period(self):
        Booking.objects.create(**self.booking_data)

        overlapping_data = self.booking_data.copy()
        overlapping_data['check_in_date'] = self.booking_data['check_in_date'] + timedelta(days=2)
        overlapping_data['check_out_date'] = self.booking_data['check_out_date'] + timedelta(days=2)
        with self.assertRaises(ValidationError):
            Booking.objects.create(**overlapping_data)

    def test_overlapping_check_out_inside_already_booked_period(self):
        Booking.objects.create(**self.booking_data)

        overlapping_data = self.booking_data.copy()
        overlapping_data['check_in_date'] = self.booking_data['check_in_date'] - timedelta(days=2)
        overlapping_data['check_out_date'] = self.booking_data['check_out_date'] - timedelta(days=2)
        with self.assertRaises(ValidationError):
            Booking.objects.create(**overlapping_data)

    def test_overlapping_booking_period_part_of_already_booked_period(self):
        Booking.objects.create(**self.booking_data)

        overlapping_data = self.booking_data.copy()
        overlapping_data['check_in_date'] = self.booking_data['check_in_date'] + timedelta(days=1)
        overlapping_data['check_out_date'] = self.booking_data['check_out_date'] - timedelta(days=1)
        with self.assertRaises(ValidationError):
            Booking.objects.create(**overlapping_data)

    def test_overlapping_booking_period_includes_already_booked_period(self):
        Booking.objects.create(**self.booking_data)

        overlapping_data = self.booking_data.copy()
        overlapping_data['check_in_date'] = self.booking_data['check_in_date'] - timedelta(days=1)
        overlapping_data['check_out_date'] = self.booking_data['check_out_date'] + timedelta(days=1)
        with self.assertRaises(ValidationError):
            Booking.objects.create(**overlapping_data)

    def test_overlapping_with_cancelled_booking_allowed(self):
        booking1 = Booking.objects.create(**self.booking_data)
        booking1.cancel('Тест')
        booking1.refresh_from_db()

        try:
            Booking.objects.create(**self.booking_data)
        except ValidationError:
            self.fail(
                'Не удалось создать активное бронирование, даты которого пересекаются с отмененным'
            )
        self.assertEqual(Booking.objects.count(), 2)

    def test_overlapping_with_moved_booking_allowed(self):
        booking1 = Booking.objects.create(**self.booking_data)
        booking1.move(
            self.booking_data['check_in_date'] + timedelta(days=31),
            self.booking_data['check_out_date'] + timedelta(days=31)
        )
        booking1.refresh_from_db()

        try:
            Booking.objects.create(**self.booking_data)
        except ValidationError:
            self.fail(
                'Не удалось создать активное бронирование, '
                'даты которого пересекаются с перенесенным'
            )
        self.assertEqual(Booking.objects.count(), 3)

    def test_update_booking_to_overlap_raises_error(self):
        Booking.objects.create(**self.booking_data)
        data = self.booking_data.copy()
        data['check_in_date'] = self.booking_data['check_in_date'] + timedelta(days=31)
        data['check_out_date'] = self.booking_data['check_out_date'] + timedelta(days=31)
        booking2 = Booking.objects.create(**data)

        booking2.check_in_date = self.booking_data['check_in_date'] - timedelta(days=2)
        booking2.check_out_date = self.booking_data['check_out_date'] - timedelta(days=2)
        with self.assertRaises(ValidationError):
            booking2.save(update_fields=['check_in_date', 'check_out_date'])


class BookingPaymentModelTest(TestCase):
    def setUp(self):
        self.hotel = Hotel.objects.create(
            name='Тестовый Отель',
            phone_number='+79123456789',
            email='hotel@example.com',
            country='Тестия',
            city='Тестов',
            address='ул. Тест, д. 1',
            floor_count=5,
            is_active=True,
        )
        self.standard_category = RoomCategory.objects.create(
            tier=RoomCategory.Tier.FIRST,
            min_area=10,
            requires_kitchen=False,
            required_bathroom_type=RoomCategory.BathroomType.PARTIAL,
            min_rooms=1,
        )
        self.standard_room_type = RoomType.objects.create(
            name='Стандартный Двухместный',
            category=self.standard_category,
            description='Описание стандартного номера',
            size=20,
            standard_capacity=2,
            bedroom_count=1,
            living_room_count=0,
            bathroom_count=1,
            bathroom_type=RoomCategory.BathroomType.PARTIAL,
            has_kitchen=False,
        )
        self.room = Room.objects.create(
            hotel=self.hotel,
            room_type=self.standard_room_type,
            bed_count=2,
            price_per_night=Decimal('100.00'),
            extra_pay_per_person=Decimal('20.00'),
            is_pets_allowed=True,
            is_smoking_allowed=True,
            floor=2,
            number_on_floor=5,
            variant='A',
        )
        self.user = User.objects.create_user(
            email='guest@example.com',
            first_name='Guest',
            last_name='Test',
            phone_number='+79333333333',
            password='GoodPassword432+'
        )
        self.user.assign_role(role=User.Role.GUEST)
        self.guest = self.user.guest
        self.booking = Booking.objects.create(
            room=self.room,
            guest=self.guest,
            adults_count=1,
            children_count=1,
            pets_count=1,
            check_in_date=date(2000, 1, 1),
            check_out_date=date(2000, 1, 7),
        )

        self.booking_payment_data = {
            'booking': self.booking,
            'purpose': BookingPayment.Purpose.FULL_PAYMENT,
            'amount': Decimal('100.00'),
            'status': BookingPayment.Status.CLOSED,
            'paid_at': timezone.datetime(2000, 1, 7, 14)
        }

    def test_create_booking_payment_success(self):
        payment = BookingPayment.objects.create(**self.booking_payment_data)
        self.assertEqual(payment.booking, self.booking)
        self.assertEqual(payment.purpose, self.booking_payment_data['purpose'])
        self.assertEqual(payment.amount, self.booking_payment_data['amount'])
        self.assertEqual(payment.status, self.booking_payment_data['status'])
        self.assertEqual(payment.paid_at, self.booking_payment_data['paid_at'])
        self.assertIsNotNone(payment.created_at)

    def test_create_booking_payment_default_status_open(self):
        payment_data = self.booking_payment_data.copy()
        del payment_data['status']
        payment = BookingPayment.objects.create(**payment_data)
        self.assertEqual(payment.status, BookingPayment.Status.OPEN)

    def test_booking_with_status_closed_requires_paid_at(self):
        payment_data = self.booking_payment_data.copy()
        payment_data['paid_at'] = None
        payment = BookingPayment(**payment_data)
        with self.assertRaises(ValidationError):
            payment.full_clean()


class ReviewModelTest(TestCase):
    def setUp(self):
        self.hotel = Hotel.objects.create(
            name='Тестовый Отель',
            phone_number='+79123456789',
            email='hotel@example.com',
            country='Тестия',
            city='Тестов',
            address='ул. Тест, д. 1',
            floor_count=5,
            is_active=True,
        )
        self.standard_category = RoomCategory.objects.create(
            tier=RoomCategory.Tier.FIRST,
            min_area=10,
            requires_kitchen=False,
            required_bathroom_type=RoomCategory.BathroomType.PARTIAL,
            min_rooms=1,
        )
        self.standard_room_type = RoomType.objects.create(
            name='Стандартный Двухместный',
            category=self.standard_category,
            description='Описание стандартного номера',
            size=20,
            standard_capacity=2,
            bedroom_count=1,
            living_room_count=0,
            bathroom_count=1,
            bathroom_type=RoomCategory.BathroomType.PARTIAL,
            has_kitchen=False,
        )
        self.room = Room.objects.create(
            hotel=self.hotel,
            room_type=self.standard_room_type,
            bed_count=2,
            price_per_night=Decimal('100.00'),
            extra_pay_per_person=Decimal('20.00'),
            is_pets_allowed=True,
            is_smoking_allowed=True,
            floor=2,
            number_on_floor=5,
            variant='A',
        )
        self.user1 = User.objects.create_user(
            email='guest@example.com',
            first_name='Guest',
            last_name='Test',
            phone_number='+79333333333',
            password='GoodPassword432+'
        )
        self.user1.assign_role(role=User.Role.GUEST)
        self.guest = self.user1.guest
        self.booking = Booking.objects.create(
            room=self.room,
            guest=self.user1.guest,
            adults_count=1,
            children_count=1,
            pets_count=1,
            check_in_date=date(2000, 1, 1),
            check_out_date=date(2000, 1, 7),
            status=Booking.Status.CLOSED,
        )
        self.user2 = User.objects.create_user(
            email='moderator@example.com',
            first_name='Moderator',
            last_name='Test',
            phone_number='+79222222222',
            password='GoodPassword432+'
        )
        self.user2.assign_role(role=User.Role.MODERATOR)
        self.moderator = self.user2.moderator

        self.review_data = {
            'booking': self.booking,
            'rating': 5,
            'comment': 'Хороший отель',
            'status': Review.Status.ON_MODERATION,
            'moderated_by': self.moderator,
        }

    def test_create_review_success(self):
        review = Review.objects.create(**self.review_data)
        self.assertEqual(review.booking, self.review_data['booking'])
        self.assertEqual(review.rating, self.review_data['rating'])
        self.assertEqual(review.comment, self.review_data['comment'])
        self.assertEqual(review.status, self.review_data['status'])
        self.assertEqual(review.moderated_by, self.review_data['moderated_by'])
        self.assertIsNotNone(review.created_at)

    def test_review_on_active_booking_not_allowed(self):
        self.booking.status = Booking.Status.ACTIVE
        self.booking.save()
        review = Review(**self.review_data)
        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_review_on_cancelled_booking_not_allowed(self):
        self.booking.status = Booking.Status.ACTIVE
        self.booking.save(update_fields=['status'])
        self.booking.cancel('Причина')
        self.booking.refresh_from_db()
        review = Review(**self.review_data)
        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_review_on_moved_booking_not_allowed(self):
        self.booking.status = Booking.Status.ACTIVE
        self.booking.save(update_fields=['status'])
        self.booking.move(
            self.booking.check_in_date + timedelta(3),
            self.booking.check_out_date + timedelta(3),
        )
        self.booking.refresh_from_db()
        review = Review(**self.review_data)
        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_review_constraint_published_at_required_for_published_status(self):
        review_data = self.review_data.copy()
        review_data['status'] = Review.Status.PUBLISHED
        review = Review(**review_data)
        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_review_constraint_moderated_by_required_for_non_draft(self):
        statuses = [
            Review.Status.ON_MODERATION, Review.Status.PUBLISHED,
            Review.Status.REJECTED, Review.Status.ARCHIVED
        ]
        review_data = self.review_data.copy()
        review_data['moderated_by'] = None

        for status in statuses:
            review_data['status'] = status
            review = Review(**review_data)
            with self.subTest(status=status):
                with self.assertRaises(ValidationError):
                    review.full_clean()

    def test_review_draft_not_require_moderated_by(self):
        review_data = self.review_data.copy()
        review_data['status'] = Review.Status.DRAFT
        review_data['moderated_by'] = None
        review_draft = Review(**review_data)
        try:
            review_draft.full_clean()
        except ValidationError:
            self.fail('Наличие модератора необязательно для черновика, но тест упал')

    def test_review_constraint_rejection_reason_required_for_rejected(self):
        review_data = self.review_data.copy()
        review_data['status'] = Review.Status.REJECTED
        review = Review(**review_data)
        with self.assertRaises(ValidationError):
            review.full_clean()
