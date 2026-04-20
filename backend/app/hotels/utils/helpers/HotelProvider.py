from io import BytesIO
import random
from typing import Any, Optional

from django.core.files.images import ImageFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Max
from faker import Faker
from faker.providers import BaseProvider
from PIL import Image

from app.hotels.models import Hotel, RoomType, Room, RoomPhoto
from utils.normalizers import normalize_email, normalize_phone
from utils.validators import validate_email, validate_phone


class HotelProvider(BaseProvider):
    '''Кастомный Faker-провайдер для генерации данных моделей hotels.'''

    def __init__(self, generator: Faker, franchise_name: Optional[str]):
        super().__init__(generator)
        self.base_name = franchise_name or self.generator.word().capitalize()
        self._preposition_cases = {
            'с видом на': ('площадь', 'реку', 'улицу', 'здание', 'бульвар', 'залив'),
            'у': ('площади', 'реки', 'улицы', 'здания', 'бульвара', 'залива'),
            'рядом с': ('площадью', 'рекой', 'улицей', 'зданием', 'бульваром', 'заливом'),
            'над': ('площадью', 'рекой', 'улицей', 'зданием', 'бульваром', 'заливом'),
            'на': ('площади', 'реке', 'озере', 'заливе'),
            'в центре': ('площади', 'квартала', 'района'),
        }
        self._prepositions = tuple(self._preposition_cases.keys())

        self._used_hotel_emails = set()
        self._used_hotel_phones = set()
        self._used_hotel_names = set()
        self._used_room_type_names = set()

        self._hotel_room_tracker = {}
        self._room_photo_tracker = {}

    def _gen_unique_value(
        self, storage: set, generator_func: Any,
        validator=lambda _: True, max_attempts=100
    ) -> Any:
        for _ in range(max_attempts):
            value = generator_func()
            if value not in storage and validator(value):
                storage.add(value)
                return value
        raise RuntimeError('Не удалось сгенерировать уникальное валидное значение')

    def _generate_valid_email(self) -> str:
        return normalize_email(self.generator.company_email())

    def _generate_valid_phone(self) -> str:
        return normalize_phone(self.generator.phone_number())

    def _generate_valid_name(self, street: str) -> str:
        pr = self.generator.random_element(self._prepositions)
        return f'{self.base_name} {pr} {street}'

    def generate_hotel(self) -> dict:
        '''Генерирует данные для отеля.'''
        street = self.generator.street_name()
        address = f'{street} {self.generator.building_number()}'
        name = self._gen_unique_value(
            self._used_hotel_names,
            lambda: self._generate_valid_name(street)
        )
        phone = self._gen_unique_value(
            self._used_hotel_phones,
            self._generate_valid_phone,
            validate_phone
        )
        email = self._gen_unique_value(
            self._used_hotel_emails,
            self._generate_valid_email,
            validate_email
        )
        floor = self.generator.random_int(min=1, max=10)

        return {
            'name': name,
            'phone_number': phone,
            'email': email,
            'country': self.generator.current_country(),
            'city': self.generator.city(),
            'address': address,
            'floor_count': floor,
            'is_active': self.generator.boolean(chance_of_getting_true=85),
        }

    def _generate_valid_room_type_name(self) -> str:
        noun = self.generator.random_element(('Номер', 'Комната', 'Апартаменты', 'Студия'))
        pr = self.generator.random_element(self._prepositions)
        geo = self.generator.random_element(self._preposition_cases[pr])
        geo_name = self.generator.last_name()
        return f'{noun} {pr} {geo} {geo_name}'

    def generate_room_type(self) -> dict:
        '''Генерирует данные для типа номера.'''
        name = self._gen_unique_value(
            self._used_room_type_names,
            self._generate_valid_room_type_name
        )
        bedroom_count = self.generator.random_int(min=1, max=5)
        bathroom_count = self.generator.random_int(min=0, max=bedroom_count)
        return {
            'name': name,
            'description': self.generator.text(max_nb_chars=300),
            'size': self.generator.random_int(min=2, max=200),
            'capacity': self.generator.random_int(min=1, max=8),
            'bedroom_count': bedroom_count,
            'bathroom_count': bathroom_count,
            'has_balcony': self.generator.boolean(chance_of_getting_true=25),
        }

    def generate_room(self, hotel: Hotel, room_type: RoomType) -> dict:
        '''Генерирует данные для комнаты.'''
        floor_tracker = self._hotel_room_tracker.setdefault(hotel.name, {})
        floor = max(floor_tracker.keys(), default=1)
        room_tracker = floor_tracker.setdefault(floor, {})
        max_number_on_floor = max(room_tracker.keys(), default=0)

        change_floor_chance = 0 + max_number_on_floor
        max_number_on_first_floor = max(floor_tracker[1].keys(), default=0)
        if floor != 1 and max_number_on_floor == max_number_on_first_floor:
            change_floor_chance = 100

        if self.generator.boolean(chance_of_getting_true=change_floor_chance):
            floor += 1
            max_number_on_floor = 0
            room_tracker = {}
            floor_tracker[floor] = room_tracker

        number_on_floor = max_number_on_floor + 1

        max_variant = room_tracker.get(max_number_on_floor)
        # Чтобы избежать одиночного варианта последней комнаты на этаже
        # На первом вообще не будет комнат с вариантами
        get_variant_chance = (max_number_on_first_floor - (max_number_on_floor + 1)) * 3
        if max_variant == 'A':
            get_variant_chance = 100
        elif max_variant is not None:
            get_variant_chance = 100 / ord(max_variant)
        variant = None
        if self.generator.boolean(chance_of_getting_true=get_variant_chance):
            variant = chr(ord(max_variant) + 1) if max_variant else 'A'
            if variant != 'A':
                number_on_floor = max_number_on_floor

        floor_tracker[floor][number_on_floor] = variant

        price = round(random.uniform(800.0, 20000.0), 2)
        extra_pay_per_person = round(price * random.uniform(0.25, 0.50), 2)

        return {
            'hotel': hotel,
            'room_type': room_type,
            'is_pets_allowed': self.generator.boolean(chance_of_getting_true=25),
            'is_smoking_allowed': self.generator.boolean(chance_of_getting_true=25),
            'price_per_night': price,
            'extra_pay_per_person': extra_pay_per_person,
            'floor': floor,
            'number_on_floor': number_on_floor,
            'variant': variant,
        }

    def _generate_test_image(self, filename: str) -> ImageFile:
        '''Создаёт тестовое изображение в памяти и возвращает ImageFile.'''
        img = Image.new('RGB', (800, 600), color=self.generator.color_rgb())
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        return SimpleUploadedFile(
            name=f'test_{filename}.jpg',
            content=buffer.getvalue(),
            content_type='image/jpeg',
        )

    def generate_room_photo(self, room: Room) -> dict:
        '''Генерирует данные для фото комнаты.'''
        room_key = room.id
        sort_number = self._room_photo_tracker.get(room_key, 0) + 1
        self._room_photo_tracker[room_key] = sort_number
        filename = f'photo_{sort_number}'
        img = self._generate_test_image(filename)
        return {
            'room': room,
            'photo': img,
            'sort_order_number': sort_number,
        }

    def load_existing_rooms(self, hotel: Hotel):
        '''Загружает существующие номера отеля в трекер.'''
        floor_tracker = self._hotel_room_tracker.setdefault(hotel.name, {})
        for room in hotel.rooms.select_related().only('floor', 'number_on_floor', 'variant'):
            floor = room.floor
            room_tracker = floor_tracker.setdefault(floor, {})
            max_variant = room_tracker.get(room.number_on_floor)
            if room.variant:
                if max_variant and room.variant > max_variant:
                    room_tracker[room.number_on_floor] = room.variant

    def load_existing_photos(self, hotel: Hotel):
        '''Загружает существующие фото отеля в трекер.'''
        photos_data = RoomPhoto.objects.filter(room__hotel=hotel) \
            .values('room_id').annotate(max_sort=Max('sort_order_number'))

        for entry in photos_data:
            self._room_photo_tracker[entry['room_id']] = entry['max_sort']

    def load_existing_data(self, hotel: Hotel) -> None:
        '''Загружает данные о порядке номеров, фото'''
        self.load_existing_rooms(hotel)
        self.load_existing_photos(hotel)
