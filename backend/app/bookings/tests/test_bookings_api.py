from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from app.bookings.models import Booking
from app.hotels.models import Hotel, Room, RoomCategory, RoomType


User = get_user_model()


class MyBookingViewSetTest(APITestCase):
    def setUp(self):
        self.list_url = reverse('my-booking-list')
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
        self.no_role_user = User.objects.create_user(
            email='user@example.com',
            first_name='User',
            last_name='NoRole',
            phone_number='+79222222222',
            password='GoodPassword432+'
        )

        self.guest_user.assign_role(role=User.Role.GUEST)
        self.moved_booking = Booking.objects.create(
            room=self.room,
            guest=self.guest_user.guest,
            adults_count=1,
            children_count=1,
            pets_count=1,
            check_in_date=date(2020, 1, 1),
            check_out_date=date(2020, 1, 10),
            status=Booking.Status.ACTIVE
        )
        self.moved_booking.move(
            self.moved_booking.check_in_date + timedelta(days=7),
            self.moved_booking.check_out_date + timedelta(days=7)
        )
        self.active_booking = self.moved_booking.moved_to
        self.closed_booking = Booking.objects.create(
            room=self.room,
            guest=self.guest_user.guest,
            adults_count=1,
            children_count=1,
            pets_count=1,
            check_in_date=date(2000, 1, 1),
            check_out_date=date(2000, 1, 7),
            status=Booking.Status.CLOSED
        )
        self.cancelled_booking = Booking.objects.create(
            room=self.room,
            guest=self.guest_user.guest,
            adults_count=1,
            children_count=1,
            pets_count=1,
            check_in_date=date(2000, 2, 1),
            check_out_date=date(2000, 2, 7),
        )
        self.cancelled_booking.cancel('Причина')

    def _get_detail_url(self, booking_id):
        return reverse('my-booking-detail', kwargs={'pk': booking_id})

    def _get_cancel_url(self, booking_id):
        return reverse('my-booking-cancel', kwargs={'pk': booking_id})

    def _get_move_url(self, booking_id):
        return reverse('my-booking-move', kwargs={'pk': booking_id})

    def test_unathenticated_cannot_list_bookings(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_guest_cannot_list_bookings(self):
        self.client.force_authenticate(self.no_role_user)
        roles = [None, User.Role.MODERATOR, User.Role.ADMIN]

        for role in roles:
            with self.subTest(role=role):
                if role:
                    self.no_role_user.assign_role(role)
                response = self.client.get(self.list_url)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_guest_can_list_bookings(self):
        self.client.force_authenticate(self.guest_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)
        ids = [b['id'] for b in response.data]
        self.assertIn(self.active_booking.pk, ids)
        self.assertIn(self.cancelled_booking.pk, ids)
        self.assertIn(self.closed_booking.pk, ids)
        self.assertIn(self.moved_booking.pk, ids)

    def test_guest_cannot_list_other_guest_bookings(self):
        self.no_role_user.assign_role(User.Role.GUEST)
        self.client.force_authenticate(self.no_role_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_filter_by_status(self):
        self.client.force_authenticate(self.guest_user)
        statuses = [
            (Booking.Status.ACTIVE, self.active_booking.pk),
            (Booking.Status.CANCELLED, self.cancelled_booking.pk),
            (Booking.Status.CLOSED, self.closed_booking.pk),
            (Booking.Status.MOVED, self.moved_booking.pk)
        ]

        for b_status, b_id in statuses:
            with self.subTest(status=status):
                response = self.client.get(self.list_url, {'status': b_status})
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 1)
                self.assertEqual(response.data[0]['id'], b_id)

    def test_filter_by_several_statuses(self):
        self.client.force_authenticate(self.guest_user)
        statuses = [Booking.Status.CANCELLED, Booking.Status.MOVED]
        response = self.client.get(self.list_url, {'status': statuses})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [b['id'] for b in response.data]
        self.assertEqual(len(ids), 2)
        self.assertNotIn(self.active_booking.pk, ids)
        self.assertIn(self.cancelled_booking.pk, ids)
        self.assertNotIn(self.closed_booking.pk, ids)
        self.assertIn(self.moved_booking.pk, ids)

    def test_filter_by_hotel_id(self):
        other_hotel = Hotel.objects.create(
            name='Чужой Отель',
            phone_number='+79500000003',
            email='foreign@example.com',
            country='Тестия',
            city='Тестов',
            address='ул. Чужая, 1',
            floor_count=3,
            is_active=True,
        )
        other_room = Room.objects.create(
            hotel=other_hotel,
            room_type=self.standard_room_type,
            bed_count=2,
            price_per_night=Decimal('100.00'),
            extra_pay_per_person=Decimal('20.00'),
            is_pets_allowed=True,
            is_smoking_allowed=True,
            floor=1,
            number_on_floor=10,
        )
        other_hotel_booking = Booking.objects.create(
            room=other_room,
            guest=self.guest_user.guest,
            adults_count=1,
            children_count=1,
            pets_count=1,
            check_in_date=date(2010, 1, 1),
            check_out_date=date(2010, 1, 7),
            status=Booking.Status.CLOSED
        )
        self.client.force_authenticate(self.guest_user)
        response = self.client.get(self.list_url, {'hotel_id': other_hotel.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [b['id'] for b in response.data]
        self.assertEqual(len(ids), 1)
        self.assertIn(other_hotel_booking.pk, ids)
        self.assertNotIn(self.active_booking.pk, ids)
        self.assertNotIn(self.cancelled_booking.pk, ids)
        self.assertNotIn(self.closed_booking.pk, ids)
        self.assertNotIn(self.moved_booking.pk, ids)

    def test_filter_by_check_in(self):
        self.client.force_authenticate(self.guest_user)

        check_in_from = date(2010, 1, 1)
        response1 = self.client.get(self.list_url, {'check_in_from': check_in_from})
        ids1 = [b['id'] for b in response1.data]
        self.assertEqual(len(ids1), 2)
        self.assertIn(self.active_booking.pk, ids1)
        self.assertNotIn(self.cancelled_booking.pk, ids1)
        self.assertNotIn(self.closed_booking.pk, ids1)
        self.assertIn(self.moved_booking.pk, ids1)

        check_in_to = self.moved_booking.check_in_date
        response2 = self.client.get(
            self.list_url,
            {'check_in_from': check_in_from, 'check_in_to': check_in_to}
        )
        ids2 = [b['id'] for b in response2.data]
        self.assertEqual(len(ids2), 1)
        self.assertNotIn(self.active_booking.pk, ids2)
        self.assertNotIn(self.cancelled_booking.pk, ids2)
        self.assertNotIn(self.closed_booking.pk, ids2)
        self.assertIn(self.moved_booking.pk, ids2)

    def test_default_ordering_created_at(self):
        self.client.force_authenticate(self.guest_user)
        response = self.client.get(self.list_url)
        created_at_data = [datetime.fromisoformat(b['created_at']) for b in response.data]
        self.assertEqual(created_at_data, sorted(created_at_data, reverse=True))

    def test_order_by_created_at(self):
        self.client.force_authenticate(self.guest_user)
        response = self.client.get(self.list_url, {'ordering': 'created_at'})
        data = [datetime.fromisoformat(b['created_at']) for b in response.data]
        self.assertEqual(data, sorted(data))

    def test_order_by_check_in_date(self):
        self.client.force_authenticate(self.guest_user)
        response = self.client.get(self.list_url, {'ordering': 'check_in_date'})
        data = [date.fromisoformat(b['check_in_date']) for b in response.data]
        self.assertEqual(data, sorted(data))

    def test_unathenticated_cannot_retrieve_booking(self):
        response = self.client.get(self._get_detail_url(self.active_booking.pk))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_guest_cannot_retrieve_booking(self):
        self.client.force_authenticate(self.no_role_user)
        roles = [None, User.Role.MODERATOR, User.Role.ADMIN]

        for role in roles:
            with self.subTest(role=role):
                if role:
                    self.no_role_user.assign_role(role)
                response = self.client.get(self._get_detail_url(self.active_booking.pk))
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_guest_can_retrieve_booking(self):
        self.client.force_authenticate(self.guest_user)
        response = self.client.get(self._get_detail_url(self.active_booking.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.active_booking.pk)
        self.assertEqual(response.data['hotel_name'], self.hotel.name)
        self.assertEqual(response.data['room_number'], self.room.room_number)
        self.assertEqual(response.data['room_type_name'], self.standard_room_type.name)
        self.assertEqual(
            date.fromisoformat(response.data['check_in_date']),
            self.active_booking.check_in_date
        )
        self.assertEqual(
            date.fromisoformat(response.data['check_out_date']),
            self.active_booking.check_out_date
        )
        self.assertEqual(response.data['days_count'], self.active_booking.days_count)
        self.assertEqual(response.data['adults_count'], self.active_booking.adults_count)
        self.assertEqual(response.data['children_count'], self.active_booking.children_count)
        self.assertEqual(response.data['pets_count'], self.active_booking.pets_count)
        self.assertEqual(response.data['status'], self.active_booking.status)
        self.assertEqual(response.data['status_display'], self.active_booking.get_status_display())
        self.assertEqual(response.data['type'], self.active_booking.type)
        self.assertEqual(
            datetime.fromisoformat(response.data['created_at']),
            self.active_booking.created_at
        )

    def test_guest_cannot_retrieve_other_guest_booking(self):
        self.no_role_user.assign_role(User.Role.GUEST)
        self.client.force_authenticate(self.no_role_user)
        response = self.client.get(self._get_detail_url(self.active_booking.pk))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_cancelled_booking_returns_cancellation(self):
        self.client.force_authenticate(self.guest_user)
        response = self.client.get(self._get_detail_url(self.cancelled_booking.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cancellation = self.cancelled_booking.cancellation
        self.assertIn('cancellation', response.data)
        self.assertEqual(response.data['cancellation']['id'], cancellation.pk)
        self.assertEqual(
            response.data['cancellation']['cancellation_reason'],
            cancellation.cancellation_reason
        )
        self.assertEqual(
            datetime.fromisoformat(response.data['cancellation']['cancelled_at']),
            cancellation.cancelled_at
        )

    def test_retrieve_moved_booking_returns_moved_to_id(self):
        self.client.force_authenticate(self.guest_user)
        response = self.client.get(self._get_detail_url(self.moved_booking.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['moved_to_id'], self.active_booking.pk)

    def test_unathenticated_cannot_cancel_booking(self):
        cancel_data = {'reason': 'Причина'}
        response = self.client.post(
            self._get_cancel_url(self.active_booking.pk),
            cancel_data
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_guest_cannot_cancel_booking(self):
        self.client.force_authenticate(self.no_role_user)
        roles = [None, User.Role.MODERATOR, User.Role.ADMIN]
        cancel_data = {'reason': 'Причина'}

        for role in roles:
            with self.subTest(role=role):
                if role:
                    self.no_role_user.assign_role(role)
                response = self.client.post(
                    self._get_cancel_url(self.active_booking.pk), cancel_data
                )
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_guest_can_cancel_booking(self):
        self.client.force_authenticate(self.guest_user)
        cancel_data = {'reason': 'Причина'}
        response = self.client.post(self._get_cancel_url(self.active_booking.pk), cancel_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.active_booking.refresh_from_db()
        self.assertEqual(self.active_booking.status, Booking.Status.CANCELLED)
        self.assertTrue(hasattr(self.active_booking, 'cancellation'))
        self.assertEqual(
            self.active_booking.cancellation.cancellation_reason,
            cancel_data['reason']
        )
        self.assertIsNotNone(self.active_booking.cancellation.cancelled_at)

    def test_guest_cannot_cancel_other_guest_booking(self):
        self.no_role_user.assign_role(User.Role.GUEST)
        self.client.force_authenticate(self.no_role_user)
        cancel_data = {'reason': 'Причина'}
        response = self.client.post(self._get_cancel_url(self.active_booking.pk), cancel_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.active_booking.refresh_from_db()
        self.assertNotEqual(self.active_booking.status, Booking.Status.CANCELLED)
        self.assertFalse(hasattr(self.active_booking, 'cancellation'))

    def test_guest_cannot_cancel_not_active_booking(self):
        self.client.force_authenticate(self.guest_user)
        bookings = [self.cancelled_booking, self.closed_booking, self.moved_booking]
        cancel_data = {'reason': 'Причина'}

        for booking in bookings:
            with self.subTest(status=booking.get_status_display()):
                response = self.client.post(
                    self._get_cancel_url(booking.pk), cancel_data
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                expected_status = booking.status
                booking.refresh_from_db()
                self.assertEqual(booking.status, expected_status)

    def test_cancel_booking_requires_reason(self):
        self.client.force_authenticate(self.guest_user)
        response = self.client.post(self._get_cancel_url(self.active_booking.pk), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.active_booking.refresh_from_db()
        self.assertNotEqual(self.active_booking.status, Booking.Status.CANCELLED)
        self.assertFalse(hasattr(self.active_booking, 'cancellation'))

    def test_unathenticated_cannot_move_booking(self):
        move_data = {
            'check_in_date': date(2020, 2, 1),
            'check_out_date': date(2020, 2, 7)
        }
        response = self.client.post(
            self._get_move_url(self.active_booking.pk), move_data
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_guest_cannot_move_booking(self):
        self.client.force_authenticate(self.no_role_user)
        roles = [None, User.Role.MODERATOR, User.Role.ADMIN]
        move_data = {
            'check_in_date': date(2020, 2, 1),
            'check_out_date': date(2020, 2, 7)
        }

        for role in roles:
            with self.subTest(role=role):
                if role:
                    self.no_role_user.assign_role(role)
                response = self.client.post(
                    self._get_move_url(self.active_booking.pk), move_data
                )
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_guest_can_move_booking(self):
        self.client.force_authenticate(self.guest_user)
        move_data = {
            'check_in_date': date(2020, 2, 1),
            'check_out_date': date(2020, 2, 7)
        }
        response = self.client.post(self._get_move_url(self.active_booking.pk), move_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.active_booking.refresh_from_db()
        self.assertEqual(self.active_booking.status, Booking.Status.MOVED)
        moved_to = self.active_booking.moved_to
        self.assertIsNotNone(moved_to)
        self.assertEqual(response.data['id'], moved_to.pk)
        self.assertEqual(response.data['hotel_name'], self.hotel.name)
        self.assertEqual(response.data['room_number'], self.room.room_number)
        self.assertEqual(response.data['room_type_name'], self.standard_room_type.name)
        self.assertEqual(
            date.fromisoformat(response.data['check_in_date']), move_data['check_in_date']
        )
        self.assertEqual(
            date.fromisoformat(response.data['check_out_date']), move_data['check_out_date']
        )
        self.assertEqual(response.data['days_count'], moved_to.days_count)
        self.assertEqual(response.data['adults_count'], self.active_booking.adults_count)
        self.assertEqual(response.data['children_count'], self.active_booking.children_count)
        self.assertEqual(response.data['pets_count'], self.active_booking.pets_count)
        self.assertEqual(response.data['status'], Booking.Status.ACTIVE)
        self.assertEqual(response.data['type'], self.active_booking.type)
        self.assertTrue(
            datetime.fromisoformat(response.data['created_at']) > self.active_booking.created_at
        )

    def test_guest_cannot_move_other_guest_booking(self):
        self.no_role_user.assign_role(User.Role.GUEST)
        self.client.force_authenticate(self.no_role_user)
        move_data = {
            'check_in_date': date(2020, 2, 1),
            'check_out_date': date(2020, 2, 7)
        }
        response = self.client.post(self._get_move_url(self.active_booking.pk), move_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.active_booking.refresh_from_db()
        self.assertNotEqual(self.active_booking.status, Booking.Status.MOVED)
        self.assertIsNone(self.active_booking.moved_to)

    def test_guest_cannot_move_not_active_booking(self):
        self.client.force_authenticate(self.guest_user)
        bookings = [self.cancelled_booking, self.closed_booking, self.moved_booking]
        move_data = {
            'check_in_date': date(2020, 2, 1),
            'check_out_date': date(2020, 2, 7)
        }

        for booking in bookings:
            with self.subTest(status=booking.get_status_display()):
                response = self.client.post(
                    self._get_move_url(booking.pk), move_data
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                expected_status = booking.status
                booking.refresh_from_db()
                self.assertEqual(booking.status, expected_status)

    def test_move_booking_validates_check_in_and_check_out(self):
        self.client.force_authenticate(self.guest_user)
        move_data = {
            'check_in_date': date(2020, 2, 7),
            'check_out_date': date(2020, 2, 1)
        }
        response = self.client.post(self._get_move_url(self.active_booking.pk), move_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.active_booking.refresh_from_db()
        self.assertNotEqual(self.active_booking.status, Booking.Status.MOVED)
        self.assertIsNone(self.active_booking.moved_to)


class BookingCreateViewTest(APITestCase):
    def setUp(self):
        self.base_url = reverse('create-booking')
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
        self.guest_user.assign_role(role=User.Role.GUEST)
        self.no_role_user = User.objects.create_user(
            email='user@example.com',
            first_name='User',
            last_name='NoRole',
            phone_number='+79222222222',
            password='GoodPassword432+'
        )

        self.booking_data = {
            'room_id': self.room.pk,
            'adults_count': 1,
            'children_count': 1,
            'pets_count': 1,
            'check_in_date': date(2000, 1, 1),
            'check_out_date': date(2000, 1, 7),
            'type': Booking.Type.NOT_GUARANTEED,
        }

    def test_unathenticated_cannot_create_booking(self):
        response = self.client.post(self.base_url, self.booking_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_guest_can_create_booking(self):
        self.client.force_authenticate(self.guest_user)
        response = self.client.post(self.base_url, self.booking_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['room_id'], self.room.pk)
        self.assertEqual(response.data['adults_count'], self.booking_data['adults_count'])
        self.assertEqual(response.data['children_count'], self.booking_data['children_count'])
        self.assertEqual(response.data['pets_count'], self.booking_data['pets_count'])
        self.assertEqual(
            date.fromisoformat(response.data['check_in_date']), self.booking_data['check_in_date']
        )
        self.assertEqual(
            date.fromisoformat(response.data['check_out_date']), self.booking_data['check_out_date']
        )
        self.assertEqual(response.data['type'], self.booking_data['type'])

    def test_non_guest_cannot_create_booking(self):
        self.client.force_authenticate(self.no_role_user)
        roles = [None, User.Role.MODERATOR, User.Role.ADMIN]

        for role in roles:
            with self.subTest(role=role):
                if role:
                    self.no_role_user.assign_role(role)
                response = self.client.post(self.base_url, self.booking_data)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_booking_validates_room_id(self):
        self.client.force_authenticate(self.guest_user)
        booking_data = self.booking_data.copy()
        booking_data['room_id'] = 9999

        response = self.client.post(self.base_url, booking_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_booking_validates_check_in_later_than_check_out(self):
        self.client.force_authenticate(self.guest_user)
        booking_data = self.booking_data.copy()
        booking_data['check_in_date'] = self.booking_data['check_out_date']
        booking_data['check_out_date'] = self.booking_data['check_in_date']

        response = self.client.post(self.base_url, booking_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_booking_validates_check_in_equals_check_out(self):
        self.client.force_authenticate(self.guest_user)
        booking_data = self.booking_data.copy()
        booking_data['check_out_date'] = self.booking_data['check_in_date']

        response = self.client.post(self.base_url, booking_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_booking_in_inactive_hotel_fails(self):
        inactive_hotel = Hotel.objects.create(
            name='Неактивный Отель',
            phone_number='+79012345678',
            email='inactive@example.com',
            country='Тестия',
            city='Тестов',
            address='ул. Какая-то, д. 9',
            floor_count=2,
            is_active=False,
        )
        self.room.hotel = inactive_hotel
        self.room.save(update_fields=['hotel'])
        self.room.refresh_from_db()
        self.client.force_authenticate(self.guest_user)
        response = self.client.post(self.base_url, self.booking_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_bookings_validates_pets_count(self):
        self.room.is_pets_allowed = False
        self.room.save(update_fields=['is_pets_allowed'])
        self.room.refresh_from_db()
        self.client.force_authenticate(self.guest_user)
        response = self.client.post(self.base_url, self.booking_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_bookings_validates_people_count(self):
        booking_data = self.booking_data.copy()
        booking_data['adults_count'] = 10
        with self.subTest(check='extra_adults'):
            self.client.force_authenticate(self.guest_user)
            response = self.client.post(self.base_url, booking_data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        booking_data['adults_count'] = self.booking_data['adults_count']
        booking_data['children_count'] = 10
        with self.subTest(check='extra_children'):
            self.client.force_authenticate(self.guest_user)
            response = self.client.post(self.base_url, booking_data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        booking_data['adults_count'] = 0
        booking_data['children_count'] = 1
        with self.subTest(check='no_adults'):
            self.client.force_authenticate(self.guest_user)
            response = self.client.post(self.base_url, booking_data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_overlapping_booking_fails(self):
        self.client.force_authenticate(self.guest_user)
        response1 = self.client.post(self.base_url, self.booking_data)
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        overlapping_data = self.booking_data.copy()
        overlapping_data['check_in_date'] = self.booking_data['check_in_date'] + timedelta(days=2)
        overlapping_data['check_out_date'] = self.booking_data['check_out_date'] + timedelta(days=2)
        response2 = self.client.post(self.base_url, overlapping_data)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
