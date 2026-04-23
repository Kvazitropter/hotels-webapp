import random
from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandParser
from faker import Faker

from app.hotels.models import Hotel, RoomType, Room, RoomPhoto
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
            '--without-photos',
            action='store_false',
            help='Не создавать тестовые фото для комнат'
        )

    def handle(self, *_args: Any, **options: Any) -> Optional[str]:
        base_name: Optional[str] = options.get('name')
        hotel_count: int = options.get('hotel_count')
        room_type_count: int = options.get('room_type_count')
        room_per_hotel: int = options.get('room_per_hotel')
        with_photos: bool = options.get('without_photos')

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
            hotels = Hotel.objects.filter(name__startswith=base_name)
            if not hotels.exists():
                self.stderr.write(
                    'Нет доступных отелей.'
                )
                return

        if not room_types:
            self.stdout.write(self.style.WARNING(
                'Типы номеров не были сгенерированы, переданное количество '
                f'типов номеров: "{room_type_count}". Будут взяты существующие.'
            ))
            room_types = RoomType.objects.all()
            if not room_types.exists():
                self.stderr.write(
                    'Нет доступных типов номеров.'
                )
                return

        rooms = self._create_rooms(
            RoomProvider(faker), hotels, room_types, room_per_hotel
        )

        if not rooms:
            msg = (
                'Номера не были сгенерированы, переданное количество '
                f'номеров на отель: "{room_per_hotel}".'
            )
            if not with_photos:
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

        if with_photos:
            self._create_photos(RoomPhotoProvider(faker), rooms)

    def _create_hotels(self, generator: HotelProvider, count: int) -> list[Hotel]:
        existing_emails = set(Hotel.objects.values_list('email', flat=True))
        existing_phones = set(Hotel.objects.values_list('phone_number', flat=True))
        new_hotels = []

        for _ in range(count):
            email = normalize_email(generator.email())
            while email in existing_emails or not validate_email(email):
                email = normalize_email(generator.email())
            existing_emails.add(email)

            phone = normalize_phone(generator.phone())
            while phone in existing_phones or not validate_phone(phone):
                phone = normalize_phone(generator.phone())
            existing_phones.add(phone)

            hotel_data = generator.hotel()
            hotel_data['email'] = email
            hotel_data['phone_number'] = phone
            hotel = Hotel(**hotel_data)
            new_hotels.append(hotel)

        created_hotels = Hotel.objects.bulk_create(new_hotels)

        for hotel in created_hotels:
            self.stdout.write(self.style.SUCCESS(
               f'Создан отель {hotel}'
            ))

        return created_hotels

    def _create_room_types(self, generator: RoomTypeProvider, count: int) -> list[RoomType]:
        existing_names = set(RoomType.objects.values_list('name', flat=True))
        room_types = []

        for _ in range(count):
            name = generator.name()
            while name in existing_names:
                name = generator.name()
            existing_names.add(name)

            room_type_data = generator.room_type()
            room_type_data['name'] = name
            room_types.append(RoomType(**room_type_data))

        created_room_types = RoomType.objects.bulk_create(room_types)

        for room_type in created_room_types:
            self.stdout.write(self.style.SUCCESS(
               f'Создан тип номера {room_type}'
            ))

        return created_room_types

    def _create_rooms(
        self, generator: RoomProvider, hotels: list[Hotel],
        room_types: list[RoomType], rooms_per_hotel: int,
    ) -> list[Room]:
        new_rooms = []

        for hotel in hotels:
            floor_tracker = {}
            for room in hotel.rooms.only('floor', 'number_on_floor', 'variant'):
                floor = room.floor
                if floor not in floor_tracker:
                    floor_tracker[floor] = 0
                if room.number_on_floor > floor_tracker[floor]:
                    floor_tracker[floor] = room.number_on_floor

            max_floor = hotel.floor_count
            base_per_floor = rooms_per_hotel // max_floor
            extra_rooms = rooms_per_hotel % max_floor
            rooms_per_floors = [
                base_per_floor + (1 if i < extra_rooms else 0)
                for i in range(max_floor)
            ]
            floor = 1
            last_number = floor_tracker.get(floor, 0)
            last_variant = None
            room_type = None
            for room_counter in range(1, rooms_per_hotel + 1):
                if room_counter == sum(rooms_per_floors[:floor]):
                    floor += 1
                    last_number = floor_tracker.get(floor, 0)
                    last_variant = None
                    room_type = None
                room_data = generator.room()
                room_data['floor'] = floor

                if faker.boolean(chance_of_getting_true=25):
                    if last_variant:
                        last_variant = generator.variant(last_var=last_variant)
                    else:
                        last_variant = 'A'
                        last_number += 1
                    room_data['variant'] = last_variant
                    if not room_type:
                        room_type = random.choice(room_types)
                else:
                    room_type = random.choice(room_types)
                    last_number += 1
                    room_data['variant'] = None
                    last_variant = None

                room_data['number_on_floor'] = last_number
                room = Room(hotel=hotel, room_type=room_type, **room_data)
                new_rooms.append(room)

        created_rooms = Room.objects.bulk_create(new_rooms)

        for room in created_rooms:
            self.stdout.write(self.style.SUCCESS(
               f'Создан номер {room}'
            ))

        return created_rooms

    def _create_photos(
        self, generator: RoomPhotoProvider, rooms: list[Room]
    ):
        tracker = set(RoomPhoto.objects.values_list('room_id', flat=True))
        new_photos = []

        for room in rooms:
            if room.pk not in tracker:
                photos_count = faker.random_int(min=0, max=3)
                for i in range(photos_count):
                    room_photo_data = generator.room_photo()
                    room_photo_data['sort_order_number'] = i + 1
                    new_photos.append(RoomPhoto(**room_photo_data, room=room))

        created_photos = RoomPhoto.objects.bulk_create(new_photos)

        for photo in created_photos:
            self.stdout.write(self.style.SUCCESS(
               f'Создано {photo}'
            ))

        return created_photos
