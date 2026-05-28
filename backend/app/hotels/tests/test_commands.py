from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from app.hotels.models import Hotel, RoomCategory, RoomType, Room, RoomPhoto


class CreateTestHotelsCommandTest(TestCase):
    def setUp(self):
        self.out = StringIO()
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

    def _call_command(self, **kwargs):
        call_command('create_test_hotels', stdout=self.out, stderr=StringIO(), **kwargs)

    def test_creates_hotels_room_types_rooms_by_default(self):
        self._call_command()
        self.assertEqual(Hotel.objects.count(), 5)
        self.assertEqual(RoomType.objects.count(), 10)
        self.assertEqual(Room.objects.count(), 100)
        self.assertEqual(RoomPhoto.objects.count(), 0)

    def test_creates_hotels_room_types_rooms_with_params(self):
        self._call_command(
            name='Что-то', hotel_count=2, room_type_count=5, room_per_hotel=10, photo_per_room=2
        )
        self.assertEqual(Hotel.objects.filter(name__icontains='Что-то').count(), 2)
        self.assertEqual(Hotel.objects.count(), 2)
        self.assertEqual(RoomType.objects.count(), 5)
        self.assertEqual(Room.objects.count(), 20)
        self.assertEqual(RoomPhoto.objects.count(), 40)

    @patch('app.hotels.utils.helpers.faker_providers.RoomTypeProvider.size')
    def test_room_type_size_adjusted_to_category_min_area(self, mock_size):
        mock_size.return_value = 5
        self._call_command(
            hotel_count=0, room_type_count=3, room_per_hotel=0, photo_per_room=0
        )
        sizes = RoomType.objects.all().values_list('size', flat=True)
        for size in sizes:
            self.assertGreaterEqual(size, self.standard_category.min_area)

    @patch('app.hotels.utils.helpers.faker_providers.RoomTypeProvider.has_kitchen')
    def test_room_type_kitchen_matches_category(self, mock_has_kitchen):
        mock_has_kitchen.return_value = False
        self.standard_category.requires_kitchen = True
        self.standard_category.save(update_fields=['requires_kitchen'])
        self.premium_category.requires_kitchen = True
        self.premium_category.save(update_fields=['requires_kitchen'])
        self._call_command(
            hotel_count=0, room_type_count=3, room_per_hotel=0, photo_per_room=0
        )
        kitchen_exists = RoomType.objects.all().values_list('has_kitchen', flat=True)
        self.assertTrue(all(kitchen_exists))

    @patch('app.hotels.utils.helpers.faker_providers.RoomTypeProvider.bathroom_type')
    def test_room_type_bathroom_type_matches_category(self, mock_bathroom_type):
        mock_bathroom_type.return_value = RoomCategory.BathroomType.SHARED
        self.standard_category.required_bathroom_type = RoomCategory.BathroomType.FULL
        self.standard_category.save(update_fields=['required_bathroom_type'])
        self._call_command(
            hotel_count=0, room_type_count=3, room_per_hotel=0, photo_per_room=0
        )
        bathroom_types = RoomType.objects.all().values_list('bathroom_type', flat=True)
        self.assertTrue(all([bt == RoomCategory.BathroomType.FULL for bt in bathroom_types]))

    def test_room_type_bathroom_type_satisfies_or_exceeds_required(self):
        self.standard_category.required_bathroom_type = RoomCategory.BathroomType.PARTIAL
        self.standard_category.save(update_fields=['required_bathroom_type'])
        self.premium_category.required_bathroom_type = RoomCategory.BathroomType.PARTIAL
        self.premium_category.save(update_fields=['required_bathroom_type'])
        self._call_command(
            hotel_count=0, room_type_count=3, room_per_hotel=0, photo_per_room=0
        )
        bathroom_types = RoomType.objects.all().values_list('bathroom_type', flat=True)
        for bt in bathroom_types:
            self.assertIn(bt, (RoomCategory.BathroomType.FULL, RoomCategory.BathroomType.PARTIAL))

    def test_hotel_email_phone_unique(self):
        self._call_command(hotel_count=10)
        emails = list(Hotel.objects.values_list('email', flat=True))
        phones = list(Hotel.objects.values_list('phone_number', flat=True))
        self.assertEqual(len(set(emails)), len(emails))
        self.assertEqual(len(set(phones)), len(phones))

    def test_rooms_distributed_across_floors(self):
        self._call_command(hotel_count=1, room_type_count=1, room_per_hotel=20)
        hotel = Hotel.objects.first()
        floors = set(Room.objects.filter(hotel=hotel).values_list('floor', flat=True))
        self.assertEqual(max(floors), hotel.floor_count)
        self.assertEqual(min(floors), 1)

    @patch(
        'app.hotels.management.commands.create_test_hotels.Command.CHANCE_TO_USE_VARIANT',
        new=0
    )
    def test_room_numbers_on_floor_incremental(self):
        self._call_command(hotel_count=1, room_per_hotel=10)
        hotel = Hotel.objects.first()
        for floor in range(1, hotel.floor_count + 1):
            numbers = list(
                Room.objects.filter(hotel=hotel, floor=floor)
                .order_by('number_on_floor')
                .values_list('number_on_floor', flat=True)
            )
            if numbers:
                self.assertEqual(numbers, list(range(1, len(numbers) + 1)))

    @patch(
        'app.hotels.management.commands.create_test_hotels.Command.CHANCE_TO_USE_VARIANT',
        new=100
    )
    @patch('app.hotels.utils.helpers.faker_providers.HotelProvider.floor_count')
    def test_variant_logic(self, mock_floor):
        mock_floor.return_value = 1
        self._call_command(hotel_count=1, room_per_hotel=10)
        rooms_with_variant = Room.objects.filter(variant__isnull=False)
        self.assertEqual(rooms_with_variant.count(), 10)

        variants_on_floor = list(
            rooms_with_variant
            .order_by('number_on_floor')
            .values_list('variant', flat=True)
        )
        expected = [chr(ord('A') + i) for i in range(10)]
        self.assertEqual(variants_on_floor, expected)

    def test_uses_existing_hotels_and_room_types_when_no_creation(self):
        hotel = Hotel.objects.create(
            name='Тестовый Отель',
            phone_number='+79123456789',
            email='hotel@example.com',
            country='Тестия',
            city='Тестов',
            address='ул. Тест, д. 1',
            floor_count=5,
            is_active=True,
        )
        room_type = RoomType.objects.create(
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
        self._call_command(room_type_count=0, hotel_count=0, room_per_hotel=5)
        rooms = Room.objects.filter(hotel=hotel, room_type=room_type)
        self.assertEqual(rooms.count(), 5)


class DeleteHotelsCommandTest(TestCase):
    def setUp(self):
        self.out = StringIO()
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
        self.room1 = Room.objects.create(
            hotel=self.active_hotel,
            room_type=self.standard_room_type,
            bed_count=2,
            price_per_night=Decimal('100.00'),
            extra_pay_per_person=Decimal('20.00'),
            floor=2,
            number_on_floor=5,
            variant='A',
        )
        self.photo = RoomPhoto.objects.create(
            room=self.room1,
            photo_url='http://test-photo',
            order_number=1,
        )
        self.room2 = Room.objects.create(
            hotel=self.inactive_hotel,
            room_type=self.standard_room_type,
            bed_count=1,
            price_per_night=Decimal('100.00'),
            extra_pay_per_person=Decimal('20.00'),
            floor=1,
            number_on_floor=3,
        )

    def _call_command(self, hotel_lookup='', inputs=None):
        if inputs is None:
            inputs = []
        with patch('builtins.input', side_effect=inputs):
            call_command(
                'delete_hotels', hotel_lookup=hotel_lookup,
                stdout=self.out, stderr=StringIO()
            )

    def test_empty_lookup_prompts_confirmation(self):
        self._call_command(hotel_lookup='', inputs=['y'])
        output = self.out.getvalue()
        self.assertIn('Отели удалены', output)
        self.assertEqual(Hotel.objects.count(), 0)

    def test_empty_lookup_cancelled(self):
        self._call_command(hotel_lookup='', inputs=['n'])
        output = self.out.getvalue()
        self.assertIn('Отменено', output)
        self.assertEqual(Hotel.objects.count(), 2)

    def test_delete_hotels_by_name(self):
        self._call_command(hotel_lookup='name=Тестовый Отель', inputs=['y'])
        output = self.out.getvalue()
        self.assertIn('Тестовый Отель', output)
        self.assertIn('Отели удалены', output)
        self.assertEqual(Hotel.objects.count(), 1)
        self.assertFalse(Hotel.objects.filter(name='Тестовый Отель').exists())

    def test_delete_hotels_by_city(self):
        self._call_command(hotel_lookup='city=Тестов', inputs=['y'])
        self.assertEqual(Hotel.objects.count(), 0)
        self.assertFalse(Hotel.objects.filter(city='Тестов').exists())

    def test_delete_hotels_by_multiple_fields(self):
        self._call_command(hotel_lookup='name__icontains=Отель,is_active=False', inputs=['y'])
        self.assertEqual(Hotel.objects.count(), 1)
        self.assertFalse(Hotel.objects.filter(is_active=False).exists())

    def test_deletes_associated_rooms_and_photos(self):
        self._call_command(hotel_lookup='', inputs=['y'])
        self.assertTrue(RoomType.objects.all().exists())
        self.assertTrue(RoomCategory.objects.all().exists())
        self.assertFalse(Room.objects.all().exists())
        self.assertFalse(RoomPhoto.objects.all().exists())

    def test_cancel_deletion_after_preview(self):
        self._call_command(hotel_lookup='city=Тестов', inputs=['n'])
        output = self.out.getvalue()
        self.assertIn('Отменено', output)
        self.assertEqual(Hotel.objects.count(), 2)

    def test_no_hotels_match_lookup(self):
        self._call_command(hotel_lookup='name=Nonexistent')
        output = self.out.getvalue()
        self.assertIn('Нет отелей для удаления', output)
        self.assertEqual(Hotel.objects.count(), 2)

    def test_invalid_lookup_str_returns_error(self):
        self._call_command(hotel_lookup='name:invalid')
        output = self.out.getvalue()
        self.assertIn('name:invalid', output)
        self.assertEqual(Hotel.objects.count(), 2)

    def test_non_existent_field_returns_error_with_suggestion(self):
        self._call_command(hotel_lookup='adress=Какая')
        output = self.out.getvalue()
        self.assertIn('adress', output)
        self.assertIn('address', output)
        self.assertEqual(Hotel.objects.count(), 2)


class DeleteRoomTypesCommandTest(TestCase):
    def setUp(self):
        self.out = StringIO()
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
            bedroom_count=2,
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

    def _call_command(self, room_type_lookup='', inputs=None):
        if inputs is None:
            inputs = []
        with patch('builtins.input', side_effect=inputs):
            call_command(
                'delete_room_types', room_type_lookup=room_type_lookup,
                stdout=self.out, stderr=StringIO()
            )

    def test_empty_lookup_prompts_confirmation(self):
        self._call_command(room_type_lookup='', inputs=['y'])
        output = self.out.getvalue()
        self.assertIn('Типы удалены', output)
        self.assertEqual(RoomType.objects.count(), 0)

    def test_empty_lookup_cancelled(self):
        self._call_command(room_type_lookup='', inputs=['n'])
        output = self.out.getvalue()
        self.assertIn('Отменено', output)
        self.assertEqual(RoomType.objects.count(), 2)

    def test_deletes_associated_rooms_and_photos(self):
        self._call_command(room_type_lookup='', inputs=['y'])
        self.assertEqual(Room.objects.count(), 0)
        self.assertEqual(RoomPhoto.objects.count(), 0)

    def test_delete_room_types_by_name(self):
        self._call_command(room_type_lookup='name=Стандартный Двухместный', inputs=['y'])
        output = self.out.getvalue()
        self.assertIn('Стандартный Двухместный', output)
        self.assertIn('Типы удалены', output)
        self.assertEqual(RoomType.objects.count(), 1)
        self.assertFalse(RoomType.objects.filter(name='Стандартный Двухместный').exists())

    def test_delete_room_types_by_bedroom_count(self):
        self._call_command(room_type_lookup='bedroom_count__gte=2', inputs=['y'])
        self.assertEqual(RoomType.objects.count(), 1)
        self.assertFalse(RoomType.objects.filter(bedroom_count=2).exists())

    def test_cancel_deletion(self):
        self._call_command(room_type_lookup='name=Стандартный Двухместный', inputs=['n'])
        output = self.out.getvalue()
        self.assertIn('Отменено', output)
        self.assertEqual(RoomType.objects.count(), 2)

    def test_non_existent_field_returns_error(self):
        self._call_command(room_type_lookup='wrong_field=value')
        output = self.out.getvalue()
        self.assertIn('wrong_field', output)
        self.assertEqual(RoomType.objects.count(), 2)

    def test_no_types_match_lookup(self):
        self._call_command(room_type_lookup='name=Nonexistent')
        output = self.out.getvalue()
        self.assertIn('Нет типов для удаления', output)
        self.assertEqual(RoomType.objects.count(), 2)

    def test_invalid_lookup_str_returns_error(self):
        self._call_command(room_type_lookup='name:invalid')
        output = self.out.getvalue()
        self.assertIn('name:invalid', output)
        self.assertEqual(RoomType.objects.count(), 2)
