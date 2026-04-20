import random
from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandParser
from faker import Faker

from app.hotels.models import Hotel, RoomType, Room, RoomPhoto
from app.hotels.utils.helpers.HotelProvider import HotelProvider


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

        faker = HotelProvider(Faker('ru_RU'), base_name)
        hotels = self._create_hotels(faker, hotel_count)
        room_types = self._create_room_types(faker, room_type_count)

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

        rooms, _ = self._create_rooms_for_hotels(
            faker, hotels, room_types, room_per_hotel, with_photos
        )

        if not rooms:
            self.stdout.write(self.style.WARNING(
                'Номера не были сгенерированы, переданное количество '
                f'номеров: "{room_type_count}".'
            ))

    def _create_hotels(self, generator: HotelProvider, count: int) -> list[Hotel]:
        new_hotels = []

        for _ in range(count):
            hotel_data = generator.generate_hotel()
            hotel = Hotel(**hotel_data)
            new_hotels.append(hotel)

        created_hotels = Hotel.objects.bulk_create(new_hotels)

        for hotel in created_hotels:
            self.stdout.write(self.style.SUCCESS(
               f'Создан отель {hotel}'
            ))

        return created_hotels

    def _create_room_types(self, generator: HotelProvider, count: int) -> list[RoomType]:
        room_types = []

        for _ in range(count):
            rt_data = generator.generate_room_type()
            room_types.append(RoomType(**rt_data))

        created_room_types = RoomType.objects.bulk_create(room_types)

        for room_type in created_room_types:
            self.stdout.write(self.style.SUCCESS(
               f'Создан тип номера {room_type}'
            ))

        return created_room_types

    def _create_rooms_for_hotels(
        self, generator: HotelProvider, hotels: list[Hotel],
        room_types: list[RoomType], rooms_per_hotel: int,
        with_photos: bool
    ) -> tuple[list[Room], list[RoomPhoto]]:
        rooms = []
        room_photos = []

        for hotel in hotels:
            generator.load_existing_data(hotel)
            for _ in range(rooms_per_hotel):
                room_type = random.choice(room_types)
                room_data = generator.generate_room(hotel, room_type)
                room = Room(**room_data)
                rooms.append(room)

        created_rooms = Room.objects.bulk_create(rooms)

        if with_photos:
            for room in created_rooms:
                photos_count = generator.random_int(min=0, max=3)
                for _ in range(photos_count):
                    room_photo_data = generator.generate_room_photo(room)
                    room_photos.append(RoomPhoto(**room_photo_data))

        created_photos = RoomPhoto.objects.bulk_create(room_photos)

        for room in created_rooms:
            self.stdout.write(self.style.SUCCESS(
               f'Создан номер {room}'
            ))

        return created_rooms, created_photos
