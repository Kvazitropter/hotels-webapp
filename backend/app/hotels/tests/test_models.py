from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from app.hotels.models import (
    Hotel,
    RoomCategory,
    RoomType,
    Room,
    RoomPhoto,
)


class HotelModelTest(TestCase):
    def setUp(self):
        self.hotel_data = {
            'name': 'Тестовый Отель',
            'phone_number': '+79123456789',
            'email': 'hotel@example.com',
            'country': 'Тестия',
            'city': 'Тестов',
            'address': 'ул. Тест, д. 1, к. 3',
            'floor_count': 5,
        }
        self.other_hotel_data = {
            'name': 'Другой Отель',
            'phone_number': '+790123645678',
            'email': 'other@example.com',
            'country': 'Тестия',
            'city': 'Тестов',
            'address': 'ул. Другая, д. 11',
            'floor_count': 3,
        }

    def test_create_hotel_success(self):
        hotel = Hotel.objects.create(**self.hotel_data)
        self.assertEqual(hotel.name, self.hotel_data['name'])
        self.assertEqual(hotel.phone_number.as_e164, self.hotel_data['phone_number'])
        self.assertEqual(hotel.email, self.hotel_data['email'])
        self.assertEqual(hotel.floor_count, self.hotel_data['floor_count'])
        self.assertEqual(hotel.check_in_time, Hotel.STND_CHECK_IN_TIME)
        self.assertEqual(hotel.check_out_time, Hotel.STND_CHECK_OUT_TIME)
        self.assertFalse(hotel.is_active)

    def test_create_hotel_with_duplicate_data_fails(self):
        Hotel.objects.create(**self.hotel_data)

        for field in ['name', 'email', 'phone_number']:
            with self.subTest(duplicate=field):
                other_hotel_data = self.other_hotel_data.copy()
                other_hotel_data[field] = self.hotel_data[field]
                with transaction.atomic():
                    with self.assertRaises(IntegrityError):
                        Hotel.objects.create(**other_hotel_data)

    def test_floor_count_validation(self):
        self.hotel_data['floor_count'] = 0
        with self.assertRaises(ValidationError):
            hotel = Hotel(**self.hotel_data)
            hotel.full_clean()

        self.hotel_data['floor_count'] = Hotel.MAX_FLOOR_COUNT + 1
        with self.assertRaises(ValidationError):
            hotel = Hotel(**self.hotel_data)
            hotel.full_clean()


class RoomCategoryModelTest(TestCase):
    def setUp(self):
        self.category_data = {
            'tier': RoomCategory.Tier.LUX,
            'min_area': 40,
            'requires_kitchen': True,
            'required_bathroom_type': RoomCategory.BathroomType.FULL,
            'min_rooms': 2,
        }

    def test_create_category_success(self):
        category = RoomCategory.objects.create(**self.category_data)
        self.assertEqual(category.tier, self.category_data['tier'])
        self.assertEqual(category.min_area, self.category_data['min_area'])
        self.assertEqual(category.requires_kitchen, self.category_data['requires_kitchen'])
        self.assertEqual(
            category.required_bathroom_type, self.category_data['required_bathroom_type']
        )
        self.assertEqual(category.min_rooms, self.category_data['min_rooms'])

    def test_tier_unique_constraint(self):
        RoomCategory.objects.create(**self.category_data)
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                RoomCategory.objects.create(**self.category_data)

    def test_is_premium_property(self):
        base_data = {
            'min_area': 10,
            'requires_kitchen': False,
            'required_bathroom_type': RoomCategory.BathroomType.FULL,
            'min_rooms': 1,
        }
        premium_tiers = [
            RoomCategory.Tier.SUITE,
            RoomCategory.Tier.APARTMENT,
            RoomCategory.Tier.LUX,
            RoomCategory.Tier.JUNIOR_SUITE,
            RoomCategory.Tier.STUDIO,
        ]
        for tier in premium_tiers:
            with self.subTest(tier=tier):
                category = RoomCategory.objects.create(tier=tier, **base_data)
                self.assertTrue(category.is_premium)

        not_premium_tiers = [
            RoomCategory.Tier.FIRST,
            RoomCategory.Tier.SECOND,
            RoomCategory.Tier.THIRD,
            RoomCategory.Tier.FOURTH,
            RoomCategory.Tier.FIFTH,
        ]
        for tier in not_premium_tiers:
            with self.subTest(tier=tier):
                category = RoomCategory.objects.create(tier=tier, **base_data)
                self.assertFalse(category.is_premium)


class RoomTypeModelTest(TestCase):
    def setUp(self):
        self.lux_category = RoomCategory.objects.create(
            tier=RoomCategory.Tier.LUX,
            min_area=40,
            requires_kitchen=True,
            required_bathroom_type=RoomCategory.BathroomType.FULL,
            min_rooms=2,
        )
        self.room_lux_data = {
            'name': 'Тестовый Номер',
            'category': self.lux_category,
            'description': 'Описание тестового номера',
            'size': 80,
            'standard_capacity': 4,
            'bedroom_count': 2,
            'living_room_count': 1,
            'bathroom_count': 2,
            'bathroom_type': RoomCategory.BathroomType.FULL,
            'has_kitchen': True,
            'has_balcony': True,
        }

    def test_create_room_type_success(self):
        room_type = RoomType.objects.create(**self.room_lux_data)
        self.assertEqual(room_type.name, self.room_lux_data['name'])
        self.assertEqual(room_type.category, self.lux_category)

    def test_name_unique_constraint(self):
        RoomType.objects.create(**self.room_lux_data)
        with self.assertRaises(ValidationError):
            RoomType.objects.create(**self.room_lux_data)

    def test_clean_validates_min_area(self):
        data = self.room_lux_data.copy()
        data['size'] = self.lux_category.min_area - 1
        room_type = RoomType(**data)
        with self.assertRaises(ValidationError):
            room_type.full_clean()

    def test_clean_validates_room_count(self):
        data = self.room_lux_data.copy()
        data['bedroom_count'] = self.lux_category.min_rooms - 1
        data['living_room_count'] = 0
        room_type = RoomType(**data)
        with self.assertRaises(ValidationError):
            room_type.full_clean()

    def test_clean_validates_bathroom_count_and_type_full(self):
        invalid_pairs = [
            (RoomCategory.BathroomType.FULL, 0),
            (RoomCategory.BathroomType.PARTIAL, 1),
            (RoomCategory.BathroomType.SHARED, 1),
        ]
        type_data = self.room_lux_data.copy()

        for btype, count in invalid_pairs:
            with self.subTest(type=btype, count=count):
                type_data['bathroom_type'] = btype
                type_data['bathroom_count'] = count
                room_type = RoomType(**type_data)
                with self.assertRaises(ValidationError):
                    room_type.full_clean()

    def test_clean_validates_bathroom_count_and_type_partial(self):
        self.lux_category.required_bathroom_type = RoomCategory.BathroomType.PARTIAL
        self.lux_category.save()
        type_data = self.room_lux_data.copy()

        invalid_pairs = [
            (RoomCategory.BathroomType.FULL, 0),
            (RoomCategory.BathroomType.PARTIAL, 0),
            (RoomCategory.BathroomType.SHARED, 1),
        ]
        for btype, count in invalid_pairs:
            with self.subTest(type=btype, count=count):
                type_data['bathroom_type'] = btype
                type_data['bathroom_count'] = count
                room_type = RoomType(**type_data)
                with self.assertRaises(ValidationError):
                    room_type.full_clean()

        valid_pairs = [
            (RoomCategory.BathroomType.FULL, 1),
            (RoomCategory.BathroomType.PARTIAL, 1),
        ]
        for btype, count in valid_pairs:
            with self.subTest(type=btype, count=count):
                type_data['bathroom_type'] = btype
                type_data['bathroom_count'] = count
                room_type = RoomType(**type_data)
                try:
                    room_type.full_clean()
                except ValidationError:
                    self.fail('Валидация не прошла')

    def test_clean_validates_kitchen_requirement(self):
        data = self.room_lux_data.copy()
        data['has_kitchen'] = not self.lux_category.requires_kitchen
        room_type = RoomType(**data)
        with self.assertRaises(ValidationError):
            room_type.full_clean()


class RoomModelTests(TestCase):
    def setUp(self):
        self.hotel = Hotel.objects.create(
            name='Тестовый Отель',
            phone_number='+79123456789',
            email='hotel@example.com',
            country='Тестия',
            city='Тестов',
            address='ул. Тест, д. 1, к. 3',
            floor_count=5,
        )
        self.standard_category = RoomCategory.objects.create(
            tier=RoomCategory.Tier.FIRST,
            min_area=10,
            requires_kitchen=False,
            required_bathroom_type=RoomCategory.BathroomType.PARTIAL,
            min_rooms=1,
        )
        self.room_type = RoomType.objects.create(
            name='Стандартный Двухместный',
            category=self.standard_category,
            description='Интересное описание',
            size=20,
            standard_capacity=2,
            bedroom_count=1,
            living_room_count=0,
            bathroom_count=1,
            bathroom_type=RoomCategory.BathroomType.PARTIAL,
            has_kitchen=False,
        )
        self.room_data = {
            'hotel': self.hotel,
            'room_type': self.room_type,
            'bed_count': 2,
            'price_per_night': Decimal('100.00'),
            'extra_pay_per_person': Decimal('20.00'),
            'floor': 3,
            'number_on_floor': 5,
            'variant': 'A',
        }

    def test_create_room_success(self):
        room = Room.objects.create(**self.room_data)
        self.assertEqual(room.hotel, self.hotel)
        self.assertEqual(room.room_type, self.room_type)
        self.assertEqual(room.price_per_night, self.room_data['price_per_night'])
        self.assertEqual(room.extra_pay_per_person, self.room_data['extra_pay_per_person'])
        self.assertEqual(room.floor, self.room_data['floor'])
        self.assertEqual(room.number_on_floor, self.room_data['number_on_floor'])
        self.assertEqual(room.variant, self.room_data['variant'])
        self.assertEqual(room.room_number, '305A')

    def test_unique_room_per_hotel_constraint(self):
        Room.objects.create(**self.room_data)
        with self.assertRaises(ValidationError):
            Room.objects.create(**self.room_data)

    def test_unique_room_with_variant(self):
        Room.objects.create(**self.room_data)
        data_b = self.room_data.copy()
        data_b['variant'] = 'B'
        Room.objects.create(**data_b)

    def test_floor_validation_against_hotel_floor_count(self):
        self.room_data['floor'] = self.hotel.floor_count + 1
        room = Room(**self.room_data)
        with self.assertRaises(ValidationError):
            room.full_clean()

    def test_room_number_property(self):
        room = Room.objects.create(**self.room_data)
        self.assertEqual(room.room_number, '305A')
        room.number_on_floor = 42
        self.assertEqual(room.room_number, '342A')
        room.variant = None
        self.assertEqual(room.room_number, '342')

    def test_price_validators(self):
        self.room_data['price_per_night'] = Decimal('-10.00')
        room = Room(**self.room_data)
        with self.assertRaises(ValidationError):
            room.full_clean()


class RoomPhotoModelTests(TestCase):
    def setUp(self):
        self.hotel = Hotel.objects.create(
            name='Тестовый Отель',
            phone_number='+79123456789',
            email='hotel@example.com',
            country='Тестия',
            city='Тестов',
            address='ул. Тест, д. 1, к. 3',
            floor_count=5,
        )
        self.standard_category = RoomCategory.objects.create(
            tier=RoomCategory.Tier.FIRST,
            min_area=10,
            requires_kitchen=False,
            required_bathroom_type=RoomCategory.BathroomType.PARTIAL,
            min_rooms=1,
        )
        self.room_type = RoomType.objects.create(
            name='Стандартный Двухместный',
            category=self.standard_category,
            description='Интересное описание',
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
            room_type=self.room_type,
            bed_count=2,
            price_per_night=Decimal('100.00'),
            extra_pay_per_person=Decimal('20.00'),
            floor=2,
            number_on_floor=5,
            variant='A',
        )
        self.photo_url = 'http://test-photo'

    def test_create_room_photo_success(self):
        photo = RoomPhoto.objects.create(
            room=self.room, photo_url=self.photo_url, order_number=1
        )
        self.assertEqual(photo.room, self.room)
        self.assertEqual(photo.photo_url, self.photo_url)
        self.assertEqual(photo.order_number, 1)

    def test_ordering_on_create_shifts_existing_photos(self):
        photo1 = RoomPhoto.objects.create(
            room=self.room, photo_url=self.photo_url, order_number=1
        )
        photo2 = RoomPhoto.objects.create(
            room=self.room, photo_url=self.photo_url, order_number=2
        )

        photo_new = RoomPhoto.objects.create(
            room=self.room, photo_url=self.photo_url, order_number=1
        )
        photo1.refresh_from_db()
        photo2.refresh_from_db()
        self.assertEqual(photo_new.order_number, 1)
        self.assertEqual(photo1.order_number, 2)
        self.assertEqual(photo2.order_number, 3)

    def test_ordering_on_update_when_increasing_order(self):
        photo1 = RoomPhoto.objects.create(
            room=self.room, photo_url=self.photo_url, order_number=1
        )
        photo2 = RoomPhoto.objects.create(
            room=self.room, photo_url=self.photo_url, order_number=2
        )
        photo3 = RoomPhoto.objects.create(
            room=self.room, photo_url=self.photo_url, order_number=3
        )

        photo1.order_number = 3
        photo1.save()

        photo1.refresh_from_db()
        photo2.refresh_from_db()
        photo3.refresh_from_db()
        self.assertEqual(photo1.order_number, 3)
        self.assertEqual(photo2.order_number, 1)
        self.assertEqual(photo3.order_number, 2)

    def test_ordering_on_update_when_decreasing_order(self):
        photo1 = RoomPhoto.objects.create(
            room=self.room, photo_url=self.photo_url, order_number=1
        )
        photo2 = RoomPhoto.objects.create(
            room=self.room, photo_url=self.photo_url, order_number=2
        )
        photo3 = RoomPhoto.objects.create(
            room=self.room, photo_url=self.photo_url, order_number=3
        )

        photo3.order_number = 1
        photo3.save()

        photo1.refresh_from_db()
        photo2.refresh_from_db()
        photo3.refresh_from_db()
        self.assertEqual(photo3.order_number, 1)
        self.assertEqual(photo1.order_number, 2)
        self.assertEqual(photo2.order_number, 3)

    def test_deleting_photo_shifts_higher_order_numbers_down(self):
        photo1 = RoomPhoto.objects.create(
            room=self.room, photo_url=self.photo_url, order_number=1
        )
        photo2 = RoomPhoto.objects.create(
            room=self.room, photo_url=self.photo_url, order_number=2
        )
        photo3 = RoomPhoto.objects.create(
            room=self.room, photo_url=self.photo_url, order_number=3
        )

        photo2.delete()
        photo1.refresh_from_db()
        photo3.refresh_from_db()
        self.assertEqual(photo1.order_number, 1)
        self.assertEqual(photo3.order_number, 2)
        self.assertEqual(RoomPhoto.objects.filter(room=self.room).count(), 2)
