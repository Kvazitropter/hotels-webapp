import random
from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandParser
from faker import Faker

from app.hotels.models import Hotel, RoomCategory, RoomType, Room, RoomPhoto
from app.hotels.utils.helpers.faker_providers import (
    HotelProvider,
    RoomTypeProvider,
    RoomProvider,
    RoomPhotoProvider,
)

from utils.normalizers import normalize_email, normalize_phone
from utils.validators import validate_email, validate_phone


faker = Faker('ru_RU')


class Command(BaseCommand):
    help = 'Генерирует тестовые отели'
    CHANCE_TO_USE_VARIANT = 25
    MAX_PHOTOS_PER_ROOM = 3

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--name',
            type=str,
            help='Название сети отелей (по умолчанию сгенерируется)'
        )
        parser.add_argument(
            '--hotel-count',
            type=int,
            default=5,
            help='Количество отелей (по умолчанию 5)'
        )
        parser.add_argument(
            '--room-type-count',
            type=int,
            default=10,
            help='Количество типов номеров (по умолчанию 10)'
        )
        parser.add_argument(
            '--room-per-hotel',
            type=int,
            default=20,
            help='Количество номеров на отель (по умолчанию 20)'
        )
        parser.add_argument(
            '--photo-per-room',
            type=int,
            default=0,
            help='Количество номеров на отель (по умолчанию 0)'
        )

    def handle(self, *_args: Any, **options: Any) -> Optional[str]:
        base_name: Optional[str] = options.get('name')
        hotel_count: int = options.get('hotel_count')
        room_type_count: int = options.get('room_type_count')
        room_per_hotel: int = options.get('room_per_hotel')
        photo_per_room: int = options.get('photo_per_room')

        hotels = self._create_hotels(
            HotelProvider(faker, base_name), hotel_count
        )
        room_types = self._create_room_types(
            RoomTypeProvider(faker), room_type_count
        )

        if not hotels:
            self.stdout.write(self.style.WARNING(
                'Отели не были сгенерированы, переданное количество отелей: '
                f'"{hotel_count}". Будут взяты существующие.'
            ))
            hotels = Hotel.objects.all()
            if base_name is not None:
                hotels = hotels.filter(name__startswith=base_name)
            if not hotels.exists():
                self.stdout.write(self.style.ERROR('Нет доступных отелей.'))
                return

        if not room_types:
            self.stdout.write(self.style.WARNING(
                'Типы номеров не были сгенерированы, переданное количество '
                f'типов номеров: "{room_type_count}". Будут взяты существующие.'
            ))
            room_types = RoomType.objects.all()
            if not room_types.exists():
                self.stdout.write(self.style.ERROR('Нет доступных типов номеров.'))
                return

        rooms = self._create_rooms(
            RoomProvider(faker), hotels, room_types, room_per_hotel
        )

        if not rooms:
            msg = (
                'Номера не были сгенерированы, переданное количество '
                f'номеров на отель: "{room_per_hotel}".'
            )
            if photo_per_room == 0:
                self.stdout.write(self.style.WARNING(msg))
                return
            self.stdout.write(self.style.WARNING(
                msg + ' Будут взяты существующие.'
            ))
            rooms = Room.objects.filter(hotel__in=hotels)
            if not rooms.exists():
                self.stdout.write(self.style.WARNING(
                    'Нет доступных номеров.'
                ))
                return

        if photo_per_room > 0:
            self._create_photos(photo_per_room, RoomPhotoProvider(faker), rooms)

    def _get_unique_email(self, generator: HotelProvider, existing_emails: dict) -> str:
        email = normalize_email(generator.email())
        while email in existing_emails or not validate_email(email):
            email = normalize_email(generator.email())
        existing_emails.add(email)
        return email

    def _get_unique_phone(self, generator: HotelProvider, existing_phones: dict) -> str:
        phone = normalize_phone(generator.phone())
        while phone in existing_phones or not validate_phone(phone):
            phone = normalize_phone(generator.phone())
        existing_phones.add(phone)
        return phone

    def _create_hotels(self, generator: HotelProvider, count: int) -> list[Hotel]:
        existing_emails = set(Hotel.objects.values_list('email', flat=True))
        existing_phones = set(Hotel.objects.values_list('phone_number', flat=True))
        new_hotels = []

        for _ in range(count):
            hotel_data = generator.hotel()
            hotel_data['email'] = self._get_unique_email(generator, existing_emails)
            hotel_data['phone_number'] = self._get_unique_phone(generator, existing_phones)
            hotel = Hotel(**hotel_data)
            new_hotels.append(hotel)

        created_hotels = Hotel.objects.bulk_create(new_hotels)

        for hotel in created_hotels:
            self.stdout.write(self.style.SUCCESS(f'Создан отель {hotel}'))

        return created_hotels

    def _adjust_room_type_to_category(
        self, room_type_data: dict, category: RoomCategory
    ) -> dict:
        if room_type_data['size'] < category.min_area:
            room_type_data['size'] = category.min_area
        if room_type_data['has_kitchen'] != category.requires_kitchen:
            room_type_data['has_kitchen'] = category.requires_kitchen
        if room_type_data['bathroom_type'] != category.required_bathroom_type:
            room_type_data['bathroom_type'] = category.required_bathroom_type
        if (room_type_data['bathroom_type'] != RoomCategory.BathroomType.SHARED
            and room_type_data['bathroom_count'] < 1):
            room_type_data['bathroom_count'] = 1
        return room_type_data

    def _get_unique_room_type_name(
        self, generator: RoomTypeProvider, category: RoomCategory, existing_names: dict
    ) -> str:
        name = generator.name(category.get_tier_display())
        while name in existing_names:
            name = generator.name(category.get_tier_display())
        existing_names.add(name)
        return name

    def _create_room_types(self, generator: RoomTypeProvider, count: int) -> list[RoomType]:
        room_categories = RoomCategory.objects.all()
        existing_names = set(RoomType.objects.values_list('name', flat=True))
        room_types = []

        for _ in range(count):
            category = random.choice(room_categories)
            room_type_data = self._adjust_room_type_to_category(
                generator.room_type(), category
            )
            room_type_data['name'] = self._get_unique_room_type_name(
                generator, category, existing_names
            )
            room_types.append(RoomType(category=category, **room_type_data))

        created_room_types = RoomType.objects.bulk_create(room_types)

        for room_type in created_room_types:
            self.stdout.write(self.style.SUCCESS(f'Создан тип номера {room_type}'))

        return created_room_types

    def _get_rooms_distribution(self, total_rooms: int, max_floor: int) -> list[int]:
        base = total_rooms // max_floor
        extra = total_rooms % max_floor
        return [base + (1 if i < extra else 0) for i in range(max_floor)]

    def _create_room(
        self, generator: RoomProvider, hotel: Hotel, room_types: list[RoomType],
        floor: int, last_number: int, last_variant: str, room_type: RoomType | None = None
    ):
        if room_type is None:
            room_type = random.choice(room_types)

        use_variant = faker.boolean(chance_of_getting_true=self.CHANCE_TO_USE_VARIANT)
        if use_variant:
            if last_variant:
                variant = generator.variant(last_var=last_variant)
            else:
                variant = 'A'
                last_number += 1
        else:
            variant = None
            last_number += 1

        room_data = generator.room()
        room_data.update({
            'floor': floor,
            'number_on_floor': last_number,
            'variant': variant,
        })
        room = Room(hotel=hotel, room_type=room_type, **room_data)
        return room, last_number, variant, room_type

    def _create_rooms(
        self, generator: RoomProvider, hotels: list[Hotel],
        room_types: list[RoomType], rooms_per_hotel: int,
    ) -> list[Room]:
        new_rooms = []

        for hotel in hotels:
            floor_tracker = {}
            for r in hotel.rooms.only('floor', 'number_on_floor', 'variant'):
                floor_tracker.setdefault(r.floor, []).append(r.number_on_floor)
            max_floor = hotel.floor_count
            rooms_per_floor = self._get_rooms_distribution(rooms_per_hotel, max_floor)

            floor = 1
            last_number = max(floor_tracker.get(floor, [0]))
            last_variant = None
            last_room_type = None
            for room_counter in range(1, rooms_per_hotel + 1):
                if room_counter > sum(rooms_per_floor[:floor]):
                    floor += 1
                    last_number = max(floor_tracker.get(floor, [0]))
                    last_variant = None
                    last_room_type = None
                room, last_number, last_variant, last_room_type = self._create_room(
                    generator, hotel, room_types, floor, last_number, last_variant, last_room_type
                )
                if last_variant is None:
                    last_room_type = None
                new_rooms.append(room)

        created_rooms = Room.objects.bulk_create(new_rooms)

        for room in created_rooms:
            self.stdout.write(self.style.SUCCESS(f'Создан номер {room}'))

        return created_rooms

    def _create_photos(
        self, photo_per_room: int, generator: RoomPhotoProvider, rooms: list[Room]
    ):
        tracker = set(RoomPhoto.objects.values_list('room_id', flat=True))
        new_photos = []

        for room in rooms:
            if room.pk not in tracker:
                for i in range(photo_per_room):
                    room_photo_data = generator.room_photo()
                    room_photo_data['order_number'] = i + 1
                    new_photos.append(RoomPhoto(**room_photo_data, room=room))

        created_photos = RoomPhoto.objects.bulk_create(new_photos)

        for photo in created_photos:
            self.stdout.write(self.style.SUCCESS(f'Создано {photo}'))

        return created_photos
