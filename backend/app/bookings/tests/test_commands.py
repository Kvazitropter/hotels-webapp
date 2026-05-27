from datetime import date
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from app.accounts.models import Guest, Moderator
from app.bookings.models import Booking, Review, CancelledBooking
from app.hotels.models import Hotel, Room, RoomType, RoomCategory

User = get_user_model()


class CreateTestBookingsCommandTest(TestCase):
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

        self.guest_user = User.objects.create_user(
            email='guest@example.com',
            first_name='Guest',
            last_name='Test',
            phone_number='+79111111111',
            password='GoodPassword432+'
        )
        self.guest = Guest.objects.create(user=self.guest_user)
        self.moderator_user = User.objects.create_user(
            email='moderator@example.com',
            first_name='Moderator',
            last_name='Test',
            phone_number='+79333333333',
            password='GoodPassword432+'
        )
        self.moderator = Moderator.objects.create(user=self.moderator_user)

        self.out = StringIO()

    def _call_command(self, **kwargs):
        call_command('create_test_bookings', stdout=self.out, stderr=StringIO(), **kwargs)

    def test_creates_bookings_default(self):
        self._call_command()
        self.assertEqual(Booking.objects.count(), 10)
        self.assertEqual(Review.objects.count(), 0)

    def test_creates_specified_number_of_bookings(self):
        self._call_command(bookings=3)
        self.assertEqual(Booking.objects.count(), 3)

    @patch('app.bookings.management.commands.create_test_bookings.Command._get_status_distribution')
    def test_creates_reviews_only_when_flag_present(self, mock_dist):
        mock_dist.return_value = {
            Booking.Status.ACTIVE: 0,
            Booking.Status.CLOSED: 3,
            Booking.Status.MOVED: 0,
            Booking.Status.CANCELLED: 0,
        }
        self._call_command(bookings=3, with_reviews=True)
        self.assertEqual(Review.objects.count(), 3)

    @patch('app.bookings.management.commands.create_test_bookings.Command._get_status_distribution')
    def test_skips_reviews_if_no_closed_bookings(self, mock_dist):
        mock_dist.return_value = {
            Booking.Status.ACTIVE: 3,
            Booking.Status.CLOSED: 0,
            Booking.Status.MOVED: 0,
            Booking.Status.CANCELLED: 0,
        }
        self._call_command(bookings=3, with_reviews=True)
        self.assertEqual(Review.objects.count(), 0)

    @patch('app.bookings.utils.helpers.faker_providers.BookingProvider.pets_count')
    def test_adjusts_pets_count_if_not_allowed(self, mock_pets_count):
        mock_pets_count.return_value = 1
        self.room.is_pets_allowed = False
        self.room.save()
        self._call_command(bookings=1)
        booking = Booking.objects.first()
        self.assertEqual(booking.pets_count, 0)

    @patch('app.bookings.utils.helpers.faker_providers.BookingProvider.children_count')
    @patch('app.bookings.utils.helpers.faker_providers.BookingProvider.adults_count')
    def test_adjusts_guests_count_if_exceeds_bed_count(
        self, mock_adults_count, mock_children_count
    ):
        mock_adults_count.return_value = 2
        mock_children_count.return_value = 1
        self.room.bed_count = 1
        self.room.save()
        self._call_command(bookings=1)
        booking = Booking.objects.first()
        self.assertLessEqual(booking.adults_count, 1)
        self.assertLessEqual(booking.children_count, 1)

    @patch('app.bookings.management.commands.create_test_bookings.Command._get_status_distribution')
    def test_distribution_of_statuses(self, mock_dist):
        mock_dist.return_value = {
            Booking.Status.ACTIVE: 2,
            Booking.Status.CLOSED: 2,
            Booking.Status.MOVED: 2,
            Booking.Status.CANCELLED: 2,
        }
        self._call_command(bookings=8)
        statuses = list(Booking.objects.values_list('status', flat=True))
        self.assertEqual(statuses.count(Booking.Status.ACTIVE), 2)
        self.assertEqual(statuses.count(Booking.Status.CLOSED), 2)
        self.assertEqual(statuses.count(Booking.Status.MOVED), 2)
        self.assertEqual(statuses.count(Booking.Status.CANCELLED), 2)

    @patch('app.bookings.management.commands.create_test_bookings.Command._get_status_distribution')
    def test_moved_bookings_have_moved_to(self, mock_dist):
        mock_dist.return_value = {
            Booking.Status.ACTIVE: 1,
            Booking.Status.CLOSED: 0,
            Booking.Status.MOVED: 1,
            Booking.Status.CANCELLED: 0,
        }
        self._call_command(bookings=2)
        moved = Booking.objects.filter(status=Booking.Status.MOVED)
        for booking in moved:
            self.assertIsNotNone(booking.moved_to)
            self.assertEqual(booking.moved_to.status, Booking.Status.ACTIVE)

    @patch('app.bookings.management.commands.create_test_bookings.Command._get_status_distribution')
    def test_cancelled_bookings_have_cancellation(self, mock_dist):
        mock_dist.return_value = {
            Booking.Status.ACTIVE: 0,
            Booking.Status.CLOSED: 0,
            Booking.Status.MOVED: 0,
            Booking.Status.CANCELLED: 3,
        }
        self._call_command(bookings=3)
        cancelled = Booking.objects.filter(status=Booking.Status.CANCELLED)
        for booking in cancelled:
            self.assertTrue(hasattr(booking, 'cancellation'))
            self.assertIsInstance(booking.cancellation, CancelledBooking)
            self.assertIsNotNone(booking.cancellation.cancellation_reason)
            self.assertIsNotNone(booking.cancellation.cancelled_at)

    @patch('app.bookings.management.commands.create_test_bookings.Booking.objects.bulk_create')
    @patch('app.bookings.management.commands.create_test_bookings.Command._get_status_distribution')
    def test_rollback_on_booking_creation_error(self, mock_dist, mock_bulk):
        mock_dist.return_value = {
            Booking.Status.ACTIVE: 1,
            Booking.Status.CLOSED: 1,
            Booking.Status.MOVED: 1,
            Booking.Status.CANCELLED: 1,
        }
        mock_bulk.side_effect = Exception('Database error')
        with self.assertRaises(Exception) as e:
            self._call_command(bookings=4, with_reviews=True)
            self.assertEqual(str(e), 'Database error')
        self.assertEqual(Booking.objects.count(), 0)
        self.assertEqual(CancelledBooking.objects.count(), 0)
        self.assertEqual(Review.objects.count(), 0)

    @patch('app.bookings.models.Booking.cancel')
    @patch('app.bookings.management.commands.create_test_bookings.Command._get_status_distribution')
    def test_rollback_on_booking_cancel_error(self, mock_dist, mock_cancel):
        mock_dist.return_value = {
            Booking.Status.ACTIVE: 1,
            Booking.Status.CLOSED: 1,
            Booking.Status.MOVED: 0,
            Booking.Status.CANCELLED: 1,
        }
        mock_cancel.side_effect = Exception('Database error')
        with self.assertRaises(Exception) as e:
            self._call_command(bookings=3)
            self.assertEqual(str(e), 'Database error')
        self.assertEqual(Booking.objects.count(), 0)
        self.assertEqual(CancelledBooking.objects.count(), 0)
        self.assertEqual(Review.objects.count(), 0)

    @patch('app.bookings.models.Booking.move')
    @patch('app.bookings.management.commands.create_test_bookings.Command._get_status_distribution')
    def test_rollback_on_booking_move_error(self, mock_dist, mock_move):
        mock_dist.return_value = {
            Booking.Status.ACTIVE: 1,
            Booking.Status.CLOSED: 1,
            Booking.Status.MOVED: 1,
            Booking.Status.CANCELLED: 1,
        }
        mock_move.side_effect = Exception('Database error')
        with self.assertRaises(Exception) as e:
            self._call_command(bookings=4)
            self.assertEqual(str(e), 'Database error')
        self.assertEqual(Booking.objects.count(), 0)
        self.assertEqual(CancelledBooking.objects.count(), 0)
        self.assertEqual(Review.objects.count(), 0)

    def test_no_guests_error(self):
        Guest.objects.all().delete()
        self._call_command(bookings=1)
        self.assertEqual(Booking.objects.count(), 0)

    def test_use_existing_bookings_when_no_creation(self):
        Booking.objects.create(
            room=self.room,
            guest=self.guest,
            adults_count=1,
            children_count=1,
            pets_count=1,
            check_in_date=date(2020, 1, 1),
            check_out_date=date(2020, 1, 10),
            status=Booking.Status.CLOSED
        )
        self._call_command(bookings=0, with_reviews=True)
        self.assertEqual(Review.objects.count(), 1)

    def test_no_moderators_reviews_become_draft(self):
        Moderator.objects.all().delete()
        Booking.objects.create(
            room=self.room,
            guest=self.guest,
            adults_count=1,
            children_count=1,
            pets_count=1,
            check_in_date=date(2020, 1, 1),
            check_out_date=date(2020, 1, 10),
            status=Booking.Status.CLOSED
        )
        self._call_command(bookings=0, with_reviews=True)
        review = Review.objects.first()
        self.assertEqual(review.status, Review.Status.DRAFT)
        self.assertIsNone(review.moderated_by)


class DeleteBookingsCommandTest(TestCase):
    def setUp(self):
        self.out = StringIO()
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

        self.guest_user = User.objects.create_user(
            email='guest@example.com',
            first_name='Guest',
            last_name='Test',
            phone_number='+79111111111',
            password='GoodPassword432+'
        )
        self.guest = Guest.objects.create(
            user=self.guest_user
        )
        self.moderator_user = User.objects.create_user(
            email='moderator@example.com',
            first_name='Moderator',
            last_name='Test',
            phone_number='+79333333333',
            password='GoodPassword432+'
        )
        self.moderator = Moderator.objects.create(user=self.moderator_user)

        self.active_booking = Booking.objects.create(
            room=self.room,
            guest=self.guest,
            adults_count=1,
            children_count=1,
            pets_count=1,
            check_in_date=date(2020, 1, 8),
            check_out_date=date(2020, 1, 17),
            status=Booking.Status.ACTIVE
        )
        self.moved_booking = Booking.objects.create(
            room=self.room,
            guest=self.guest,
            adults_count=1,
            children_count=1,
            pets_count=1,
            check_in_date=date(2020, 1, 1),
            check_out_date=date(2020, 1, 10),
            status=Booking.Status.MOVED,
            moved_to=self.active_booking
        )
        self.closed_booking = Booking.objects.create(
            room=self.room,
            guest=self.guest,
            adults_count=1,
            children_count=1,
            pets_count=1,
            check_in_date=date(2000, 1, 1),
            check_out_date=date(2000, 1, 7),
            status=Booking.Status.CLOSED
        )
        self.cancelled_booking = Booking.objects.create(
            room=self.room,
            guest=self.guest,
            adults_count=1,
            children_count=1,
            pets_count=1,
            check_in_date=date(2000, 2, 1),
            check_out_date=date(2000, 2, 7),
            status=Booking.Status.PENDING
        )
        CancelledBooking.objects.create(
            booking=self.cancelled_booking,
            cancellation_reason='Причина'
        )
        self.cancelled_booking.status = Booking.Status.CANCELLED
        self.cancelled_booking.save(update_fields=['status'])
        self.cancelled_booking.refresh_from_db()

        self.review = Review.objects.create(
            booking=self.closed_booking,
            rating=5,
            comment='Все отлично',
            status=Review.Status.PUBLISHED,
            moderated_by=self.moderator,
            published_at=timezone.now()
        )

    def _call_command(self, booking_lookup='', inputs=None):
        if inputs is None:
            inputs = []
        with patch('builtins.input', side_effect=inputs):
            call_command(
                'delete_bookings', booking_lookup=booking_lookup,
                stdout=self.out, stderr=StringIO()
            )

    def test_empty_lookup_prompts_confirmation(self):
        self._call_command(booking_lookup='', inputs=['y'])
        output = self.out.getvalue()
        self.assertIn('Бронирования удалены', output)
        self.assertEqual(Booking.objects.count(), 0)

    def test_empty_lookup_cancelled(self):
        self._call_command(booking_lookup='', inputs=['n'])
        output = self.out.getvalue()
        self.assertIn('Отменено', output)
        self.assertEqual(Booking.objects.count(), 4)

    def test_delete_bookings_by_status(self):
        self._call_command(booking_lookup='status=M', inputs=['y'])
        output = self.out.getvalue()
        self.assertIn('Бронирования удалены', output)
        self.assertEqual(Booking.objects.count(), 3)
        self.assertFalse(Booking.objects.filter(status=Booking.Status.MOVED).exists())

    def test_delete_bookings_by_check_in_date(self):
        self._call_command(booking_lookup='check_in_date__year=2000', inputs=['y'])
        self.assertEqual(Booking.objects.count(), 2)
        self.assertFalse(Booking.objects.filter(pk=self.closed_booking.pk).exists())
        self.assertFalse(Booking.objects.filter(pk=self.cancelled_booking.pk).exists())

    def test_delete_bookings_by_multiple_fields(self):
        self._call_command(booking_lookup='check_in_date__year=2000,status=CA', inputs=['y'])
        self.assertEqual(Booking.objects.count(), 3)
        self.assertFalse(Booking.objects.filter(pk=self.cancelled_booking.pk).exists())

    def test_deletes_associated_cancellations_reviews(self):
        self._call_command(booking_lookup='', inputs=['y'])
        self.assertFalse(CancelledBooking.objects.all().exists())
        self.assertFalse(Review.objects.all().exists())

    def test_cancel_deletion_after_preview(self):
        self._call_command(booking_lookup='status=A', inputs=['n'])
        output = self.out.getvalue()
        self.assertIn('Отменено', output)
        self.assertEqual(Booking.objects.count(), 4)

    def test_no_bookings_match_lookup(self):
        self._call_command(booking_lookup='status=INVALID')
        output = self.out.getvalue()
        self.assertIn('Нет бронирований для удаления', output)
        self.assertEqual(Booking.objects.count(), 4)

    def test_invalid_lookup_str_returns_error(self):
        self._call_command(booking_lookup='status:active')
        output = self.out.getvalue()
        self.assertIn('Неверный формат', output)
        self.assertEqual(Booking.objects.count(), 4)

    def test_non_existent_field_returns_error_with_suggestion(self):
        self._call_command(booking_lookup='statuss=active')
        output = self.out.getvalue()
        self.assertIn('statuss', output)
        self.assertIn('status', output)
        self.assertEqual(Booking.objects.count(), 4)
