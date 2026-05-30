from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from app.accounts.models import Guest
from app.bookings.models import Booking
from app.hotels.models import Hotel, RoomCategory, RoomType, Room, RoomPhoto

User = get_user_model()


class HotelsAPITestCase(APITestCase):
    def setUp(self):
        self.active_hotel = Hotel.objects.create(
            name='Тестовый Отель',
            phone_number='+79123456789',
            email='hotel@example.com',
            country='Тестия',
            city='Тестов',
            address='ул. Тест, д. 1',
            floor_count=5,
            is_active=True,
        )
        self.inactive_hotel = Hotel.objects.create(
            name='Неактивный Отель',
            phone_number='+79012345678',
            email='inactive@example.com',
            country='Тестия',
            city='Тестов',
            address='ул. Какая-то, д. 9',
            floor_count=2,
            is_active=False,
        )
        self.standard_category = RoomCategory.objects.create(
            tier=RoomCategory.Tier.FIRST,
            min_area=10,
            requires_kitchen=False,
            required_bathroom_type=RoomCategory.BathroomType.PARTIAL,
            min_rooms=1,
        )
        self.premium_category = RoomCategory.objects.create(
            tier=RoomCategory.Tier.LUX,
            min_area=35,
            requires_kitchen=False,
            required_bathroom_type=RoomCategory.BathroomType.FULL,
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
        self.premium_room_type = RoomType.objects.create(
            name='Люкс Двухместный',
            category=self.premium_category,
            description='Описание люкс номера',
            size=40,
            standard_capacity=2,
            bedroom_count=1,
            living_room_count=1,
            bathroom_count=1,
            bathroom_type=RoomCategory.BathroomType.FULL,
            has_kitchen=False,
        )
        self.standard_room = Room.objects.create(
            hotel=self.active_hotel,
            room_type=self.standard_room_type,
            bed_count=2,
            price_per_night=Decimal('100.00'),
            extra_pay_per_person=Decimal('20.00'),
            floor=2,
            number_on_floor=5,
            variant='A',
        )
        self.premium_room = Room.objects.create(
            hotel=self.active_hotel,
            room_type=self.premium_room_type,
            bed_count=2,
            price_per_night=Decimal('300.00'),
            extra_pay_per_person=Decimal('50.00'),
            floor=3,
            number_on_floor=1,
        )
        self.photo_1 = RoomPhoto.objects.create(
            room=self.standard_room,
            photo_url='http://test-photo1',
            order_number=1,
        )
        self.photo_2 = RoomPhoto.objects.create(
            room=self.standard_room,
            photo_url='http://test-photo2',
            order_number=2,
        )
        self.guest_user = User.objects.create_user(
            email='guest@example.com',
            first_name='Guest',
            last_name='Test',
            phone_number='+79444444444',
            password='GoodPassword432+',
        )
        self.guest = Guest.objects.create(user=self.guest_user)

    def _hotel_list_url(self):
        return reverse('hotel-list')

    def _hotel_detail_url(self, pk):
        return reverse('hotel-detail', kwargs={'pk': pk})

    def _room_list_url(self, hotel_pk):
        return reverse('hotel-room-list', kwargs={'hotel_pk': hotel_pk})

    def _room_detail_url(self, hotel_pk, room_pk):
        return reverse('hotel-room-detail', kwargs={'hotel_pk': hotel_pk, 'pk': room_pk})


class HotelListAPITest(HotelsAPITestCase):

    def test_returns_only_active_hotels(self):
        response = self.client.get(self._hotel_list_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(self.active_hotel.pk, response.data[0]['id'])

    def test_unauthenticated_user_can_access(self):
        response = self.client.get(self._hotel_list_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_guest_can_access(self):
        self.client.force_authenticate(self.guest_user)
        response = self.client.get(self._hotel_list_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_fields(self):
        response = self.client.get(self._hotel_list_url())
        hotel = response.data[0]
        self.assertEqual(hotel['id'], self.active_hotel.pk)
        self.assertEqual(hotel['name'], self.active_hotel.name)
        self.assertEqual(hotel['email'], self.active_hotel.email)
        self.assertEqual(hotel['phone_number'], self.active_hotel.phone_number)
        self.assertEqual(
            hotel['check_in_time'], self.active_hotel.check_in_time.strftime('%H:%M:%S')
        )
        self.assertEqual(
            hotel['check_out_time'], self.active_hotel.check_out_time.strftime('%H:%M:%S')
        )
        self.assertEqual(hotel['country'], self.active_hotel.country)
        self.assertEqual(hotel['city'], self.active_hotel.city)
        self.assertEqual(hotel['address'], self.active_hotel.address)
        self.assertEqual(hotel['floor_count'], self.active_hotel.floor_count)

    def test_search_by_city(self):
        Hotel.objects.create(
            name='Другой Отель',
            phone_number='+79500000001',
            email='other@example.com',
            country='Тестия',
            city='Другой Город',
            address='ул. Другая, 1',
            floor_count=3,
            is_active=True,
        )
        response = self.client.get(self._hotel_list_url(), {'search': 'Тестов'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [h['city'] for h in response.data]
        self.assertTrue(all(c == 'Тестов' for c in names))


class HotelDetailAPITest(HotelsAPITestCase):

    def test_returns_active_hotel(self):
        response = self.client.get(self._hotel_detail_url(self.active_hotel.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.active_hotel.pk)

    def test_inactive_hotel_returns_404(self):
        response = self.client.get(self._hotel_detail_url(self.inactive_hotel.pk))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_nonexistent_hotel_returns_404(self):
        response = self.client.get(self._hotel_detail_url(99999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class RoomListAPITest(HotelsAPITestCase):

    def test_returns_rooms_for_active_hotel(self):
        response = self.client.get(self._room_list_url(self.active_hotel.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r['id'] for r in response.data]
        self.assertIn(self.standard_room.pk, ids)
        self.assertIn(self.premium_room.pk, ids)

    def test_inactive_hotel_returns_404(self):
        response = self.client.get(self._room_list_url(self.inactive_hotel.pk))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_nonexistent_hotel_returns_404(self):
        response = self.client.get(self._room_list_url(99999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_does_not_return_rooms_of_other_hotel(self):
        other_hotel = Hotel.objects.create(
            name='Другой Отель',
            phone_number='+79500000002',
            email='other2@example.com',
            country='Тестия',
            city='Тестов',
            address='ул. Другая, 2',
            floor_count=3,
            is_active=True,
        )
        other_room = Room.objects.create(
            hotel=other_hotel,
            room_type=self.standard_room_type,
            bed_count=1,
            price_per_night=Decimal('80.00'),
            extra_pay_per_person=Decimal('10.00'),
            floor=1,
            number_on_floor=1,
        )
        response = self.client.get(self._room_list_url(self.active_hotel.pk))
        ids = [r['id'] for r in response.data]
        self.assertNotIn(other_room.pk, ids)

    def test_response_fields(self):
        response = self.client.get(self._room_list_url(self.active_hotel.pk))
        room = response.data[0]
        expected_fields = {
            'id', 'category', 'room_type_name', 'room_type_description', 'is_premium',
            'is_standard', 'standard_capacity', 'price_per_night', 'cover_photo',
        }
        self.assertLessEqual(set(room.keys()), expected_fields)

    def test_cover_photo_is_first(self):
        response = self.client.get(self._room_list_url(self.active_hotel.pk))
        room_data = next(r for r in response.data if r['id'] == self.standard_room.pk)
        self.assertIsNotNone(room_data['cover_photo'])
        self.assertEqual(room_data['cover_photo']['order_number'], 1)

    def test_cover_photo_is_null_when_no_photos(self):
        response = self.client.get(self._room_list_url(self.active_hotel.pk))
        room_data = next(r for r in response.data if r['id'] == self.premium_room.pk)
        self.assertIsNone(room_data['cover_photo'])

    def test_filter_is_premium(self):
        response = self.client.get(
            self._room_list_url(self.active_hotel.pk), {'is_premium': 'true'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r['id'] for r in response.data]
        self.assertIn(self.premium_room.pk, ids)
        self.assertNotIn(self.standard_room.pk, ids)

    def test_filter_is_standard(self):
        response = self.client.get(
            self._room_list_url(self.active_hotel.pk), {'is_standard': 'true'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r['id'] for r in response.data]
        self.assertIn(self.standard_room.pk, ids)
        self.assertNotIn(self.premium_room.pk, ids)

    def test_filter_min_capacity(self):
        response = self.client.get(
            self._room_list_url(self.active_hotel.pk), {'min_capacity': 2}
        )
        ids = [r['id'] for r in response.data]
        self.assertIn(self.standard_room.pk, ids)
        self.assertIn(self.premium_room.pk, ids)

    def test_filter_min_capacity_excludes_lower(self):
        small_type = RoomType.objects.create(
            name='Одноместный',
            category=self.standard_category,
            description='Маленький',
            size=10,
            standard_capacity=1,
            bedroom_count=1,
            living_room_count=0,
            bathroom_count=1,
            bathroom_type=RoomCategory.BathroomType.PARTIAL,
            has_kitchen=False,
        )
        small_room = Room.objects.create(
            hotel=self.active_hotel,
            room_type=small_type,
            bed_count=1,
            price_per_night=Decimal('50.00'),
            extra_pay_per_person=Decimal('0.00'),
            floor=1,
            number_on_floor=1,
        )
        response = self.client.get(
            self._room_list_url(self.active_hotel.pk), {'min_capacity': 2}
        )
        ids = [r['id'] for r in response.data]
        self.assertNotIn(small_room.pk, ids)


class RoomDetailAPITest(HotelsAPITestCase):

    def test_room_from_other_hotel_returns_404(self):
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
        response = self.client.get(
            self._room_detail_url(other_hotel.pk, self.standard_room.pk)
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_nonexistent_room_returns_404(self):
        response = self.client.get(
            self._room_detail_url(self.active_hotel.pk, 99999)
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class RoomVacantDatesAPITest(HotelsAPITestCase):
    def _get_vacant_dates_url(self, hotel_pk, room_pk):
        return reverse('hotel-room-vacant-dates', kwargs={'hotel_pk': hotel_pk, 'pk': room_pk})

    def test_returns_vacant_dates(self):
        response = self.client.get(
            self._get_vacant_dates_url(self.active_hotel.pk, self.standard_room.pk)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('vacant_dates', response.data)

    def test_vacant_dates_is_list(self):
        response = self.client.get(
            self._get_vacant_dates_url(self.active_hotel.pk, self.standard_room.pk)
        )
        self.assertIsInstance(response.data['vacant_dates'], list)

    def test_vacant_dates_excludes_booked_periods(self):
        Booking.objects.create(
            room=self.standard_room,
            guest=self.guest,
            adults_count=1,
            children_count=0,
            check_in_date=date.today() + timedelta(days=10),
            check_out_date=date.today() + timedelta(days=15),
            status=Booking.Status.ACTIVE,
        )
        response = self.client.get(
            self._get_vacant_dates_url(self.active_hotel.pk, self.standard_room.pk)
        )
        booked_range = (
            str(date.today() + timedelta(days=10)),
            str(date.today() + timedelta(days=15)),
        )
        self.assertNotIn(booked_range, response.data['vacant_dates'])

    def test_vacant_dates_with_after_param(self):
        after = date.today() + timedelta(days=30)
        response = self.client.get(
            self._get_vacant_dates_url(self.active_hotel.pk, self.standard_room.pk),
            {'after': after.isoformat()}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for start, end in response.data['vacant_dates']:
            self.assertGreaterEqual(end, after)

    def test_vacant_dates_with_before_param(self):
        before = date.today() + timedelta(days=60)
        response = self.client.get(
            self._get_vacant_dates_url(self.active_hotel.pk, self.standard_room.pk),
            {'before': before.isoformat()}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for start, end in response.data['vacant_dates']:
            self.assertLessEqual(start, before)

    def test_vacant_dates_with_after_and_before_params(self):
        after = date.today() + timedelta(days=10)
        before = date.today() + timedelta(days=40)
        response = self.client.get(
            self._get_vacant_dates_url(self.active_hotel.pk, self.standard_room.pk),
            {'after': after.isoformat(), 'before': before.isoformat()}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_vacant_dates_invalid_after_returns_400(self):
        response = self.client.get(
            self._get_vacant_dates_url(self.active_hotel.pk, self.standard_room.pk),
            {'after': 'not-a-date'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_vacant_dates_invalid_before_returns_400(self):
        response = self.client.get(
            self._get_vacant_dates_url(self.active_hotel.pk, self.standard_room.pk),
            {'before': 'not-a-date'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_vacant_dates_after_greater_than_before_returns_400(self):
        response = self.client.get(
            self._get_vacant_dates_url(self.active_hotel.pk, self.standard_room.pk),
            {
                'after': (date.today() + timedelta(days=60)).isoformat(),
                'before': (date.today() + timedelta(days=10)).isoformat(),
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
