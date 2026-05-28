from datetime import time
import random
from typing import Optional

from faker import Faker
from faker.providers import BaseProvider

from app.hotels.models import RoomCategory, Hotel


class HotelProvider(BaseProvider):
    '''Кастомный Faker-провайдер для генерации данных модели Hotel'''

    def __init__(self, generator: Faker, franchise_name: Optional[str]):
        super().__init__(generator)
        self.base_name = franchise_name or f'{self.generator.word().capitalize()}-отель'
        self._preposition_cases = {
            'с видом на': ('площадь', 'реку', 'здание', 'бульвар', 'залив'),
            'у': ('площади', 'реки', 'здания', 'бульвара', 'залива'),
            'рядом с': ('площадью', 'рекой', 'зданием', 'бульваром', 'заливом'),
            'над': ('площадью', 'рекой', 'зданием', 'бульваром', 'заливом'),
            'на': ('площади', 'реке', 'озере', 'заливе', 'проспекте'),
            'в центре': ('площади', 'квартала', 'района'),
        }
        self._prepositions = tuple(self._preposition_cases.keys())

    def email(self) -> str:
        return self.generator.company_email()

    def phone(self) -> str:
        return self.generator.phone_number()

    def name(self, street: Optional[str]=None) -> str:
        if street is None:
            pr = self.generator.random_element(self._prepositions)
            location = ' '.join([
                self.generator.random_element(self._preposition_cases[pr]),
                self.generator.street_title()
            ])
        else:
            pr = 'на'
            location = street
        return f'{self.base_name} {pr} {location}'

    def country(self) -> str:
        return 'Россия'

    def city(self) -> str:
        return f'{self.generator.city_name()}{self.generator.city_suffix()}'

    def address(self, street: Optional[str]=None, city: Optional[str]=None) -> str:
        if not all([street, city]):
            return self.generator.address()
        b_num = self.generator.building_number()
        corps_num = None
        if self.generator.boolean(chance_of_getting_true=25):
            corps_num = self.generator.building_number()
        region = self.generator.administrative_unit()
        return (
            f'{street}, д. {b_num}, {f" стр. {corps_num}, " if corps_num else ""}'
            f'{city}, {region}'
        )

    def floor_count(self) -> int:
        return self.generator.random_int(min=1, max=10)

    def check_in_time(self) -> time:
        standard_time = Hotel.STND_CHECK_IN_TIME
        if self.generator.boolean(chance_of_getting_true=5):
            return standard_time.replace(hour=standard_time.hour + 1)
        if self.generator.boolean(chance_of_getting_true=5):
            return standard_time.replace(hour=standard_time.hour - 1)
        return standard_time

    def check_out_time(self) -> time:
        standard_time = Hotel.STND_CHECK_OUT_TIME
        if self.generator.boolean(chance_of_getting_true=5):
            return standard_time.replace(hour=standard_time.hour + 1)
        if self.generator.boolean(chance_of_getting_true=5):
            return standard_time.replace(hour=standard_time.hour - 1)
        return standard_time

    def is_active(self) -> bool:
        return self.generator.boolean(chance_of_getting_true=90)

    def hotel(self) -> dict:
        street = self.generator.street_name()
        city = self.city()

        return {
            'name': self.name(street),
            'phone_number': self.phone(),
            'email': self.email(),
            'country': self.country(),
            'city': city,
            'address': self.address(street, city),
            'floor_count': self.floor_count(),
            'check_in_time': self.check_in_time(),
            'check_out_time': self.check_out_time(),
            'is_active': self.is_active(),
        }


class RoomTypeProvider(BaseProvider):
    '''Кастомный Faker-провайдер для генерации данных модели RoomType'''

    def __init__(self, generator: Faker):
        super().__init__(generator)
        self._categories = RoomCategory.Tier.values
        self._bathroom_types = RoomCategory.BathroomType.values
        self._preposition_cases = {
            'с видом на': ('площадь', 'реку', 'здание', 'бульвар', 'залив'),
            'у': ('площади', 'реки', 'здания', 'бульвара', 'залива'),
            'рядом с': ('площадью', 'рекой', 'зданием', 'бульваром', 'заливом'),
            'над': ('площадью', 'рекой', 'зданием', 'бульваром', 'заливом'),
            'на': ('площади', 'реке', 'озере', 'заливе', 'проспекте'),
            'в центре': ('площади', 'квартала', 'района'),
        }
        self._prepositions = tuple(self._preposition_cases.keys())

    def name(self, category: Optional[str]=None) -> str:
        room_type_name = category if category else self.generator.random_element(self._categories)
        pr = self.generator.random_element(self._prepositions)
        location = ' '.join([
            self.generator.random_element(self._preposition_cases[pr]),
            self.generator.street_title()
        ])
        return f'{room_type_name} {pr} {location}'

    def description(self) -> str:
        return self.generator.text(max_nb_chars=300)

    def size(self) -> int:
        return self.generator.random_int(min=6, max=200)

    def standard_capacity(self) -> int:
        return self.generator.random_int(min=1, max=8)

    def bedroom_count(self) -> int:
        return self.generator.random_int(min=1, max=5)

    def living_room_count(self, max_count: Optional[int]=None) -> int:
        max_count = max_count if max_count else 3
        return self.generator.random_int(min=0, max=max_count)

    def bathroom_count(self, max_count: Optional[int]=None) -> int:
        max_count = max_count if max_count else 3
        return self.generator.random_int(min=0, max=max_count)

    def bathroom_type(self) -> str:
        return self.generator.random_element(self._categories)

    def has_kitchen(self) -> bool:
        return self.generator.boolean(chance_of_getting_true=25)

    def has_balcony(self) -> bool:
        return self.generator.boolean(chance_of_getting_true=25)

    def room_type(self) -> dict:
        bedroom_count = self.bedroom_count()
        bathroom_count = self.bathroom_count(bedroom_count)
        bathroom_type = RoomCategory.BathroomType.SHARED
        if bathroom_count != 0:
            bathroom_type = self.generator.random_element(
                elements=(RoomCategory.BathroomType.FULL, RoomCategory.BathroomType.PARTIAL)
            )
        return {
            'name': self.name(),
            'description': self.description(),
            'size': self.size(),
            'standard_capacity': self.standard_capacity(),
            'bedroom_count': bedroom_count,
            'living_room_count': self.living_room_count(bedroom_count),
            'bathroom_count': self.bathroom_count(bedroom_count),
            'bathroom_type': bathroom_type,
            'has_kitchen': self.has_kitchen(),
            'has_balcony': self.has_balcony(),
        }


class RoomProvider(BaseProvider):
    '''Кастомный Faker-провайдер для генерации данных модели Room'''

    def bed_count(self) -> int:
        return self.generator.random_int(min=1, max=10)

    def is_pets_allowed(self) -> bool:
        return self.generator.boolean(chance_of_getting_true=25)

    def is_smoking_allowed(self) -> bool:
        return self.generator.boolean(chance_of_getting_true=25)

    def price_per_night(self) -> float:
        return round(random.uniform(800.0, 20000.0), 2)

    def extra_pay_per_person(self, price: Optional[float]=None) -> float:
        if price is None:
            return round(random.uniform(400.0, 5000.0), 2)
        return round(price * random.uniform(0.25, 0.50), 2)

    def floor(self, max_floor: Optional[int]=None) -> int:
        max_floor = max_floor if max_floor else 10
        return self.generator.random_int(min=1, max=max_floor)

    def number_on_floor(self, last_num: Optional[int]=None) -> int:
        if last_num is not None:
            return last_num + 1
        return self.generator.random_int(min=1, max=99)

    def variant(self, last_var: Optional[str]=None) -> str:
        if last_var is not None:
            return chr(ord(last_var) + 1)
        return self.generator.random_uppercase_letter()

    def room(self) -> dict:
        price = self.price_per_night()
        return {
            'bed_count': self.bed_count(),
            'is_pets_allowed': self.is_pets_allowed(),
            'is_smoking_allowed': self.is_smoking_allowed(),
            'price_per_night': price,
            'extra_pay_per_person': self.extra_pay_per_person(price),
            'floor': self.floor(),
            'number_on_floor': self.number_on_floor(),
            'variant': self.variant(),
        }


class RoomPhotoProvider(BaseProvider):
    '''Кастомный Faker-провайдер для генерации данных модели RoomPhoto'''

    def photo_url(self) -> str:
        return self.generator.url()

    def order_number(self) -> int:
        return self.generator.random_int(min=1, max=10)

    def room_photo(self) -> dict:
        return {
            'photo_url': self.photo_url(),
            'order_number': self.order_number(),
        }
