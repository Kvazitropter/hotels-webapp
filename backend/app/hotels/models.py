from datetime import time

from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from phonenumber_field.modelfields import PhoneNumberField

from app.hotels.managers import RoomManager


class Hotel(models.Model):
    MAX_FLOOR_COUNT = 10
    STND_CHECK_IN_TIME = time(hour=14, minute=0, second=0, microsecond=0)
    STND_CHECK_OUT_TIME = time(hour=12, minute=0, second=0, microsecond=0)

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Название отеля',
    )
    phone_number = PhoneNumberField(
        null=False,
        blank=False,
        unique=True,
        error_messages={'invalid': 'Введен некорректный номер телефона'},
        verbose_name='Номер телефона',
    )
    email = models.EmailField(
        max_length=100,
        unique=True,
        error_messages={'invalid': 'Введен некорректный email'},
        verbose_name='Email-адрес',
    )
    country = models.CharField(
        max_length=100,
        verbose_name='Страна',
    )
    city = models.CharField(
        max_length=100,
        verbose_name='Город',
    )
    address = models.CharField(
        max_length=255,
        verbose_name='Адрес',
    )
    floor_count = models.PositiveSmallIntegerField(
        verbose_name='Количество этажей',
        validators=[
            MinValueValidator(1, message='Количество этажей не может быть меньше 1'),
            MaxValueValidator(MAX_FLOOR_COUNT, message='Количество этажей не может быть больше 10'),
        ],
    )
    check_in_time = models.TimeField(
        default=STND_CHECK_IN_TIME,
        verbose_name='Время заезда'
    )
    check_out_time = models.TimeField(
        default=STND_CHECK_OUT_TIME,
        verbose_name='Время выезда (расчётный час)'
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name='Активен',
    )

    class Meta:
        db_table = 'hotel'
        verbose_name = 'Отель'
        verbose_name_plural = 'Отели'
        ordering = ['country', 'city', 'name', '-is_active']

    def __str__(self) -> str:
        return self.name


class RoomCategory(models.Model):
    class BathroomType(models.TextChoices):
        SHARED = 'S', 'Общий'
        PARTIAL = 'P', 'Частичный (без ванны/душа)'
        FULL = 'F', 'Полный санузел'

    class Tier(models.TextChoices):
        SUITE = 'SU', 'Сюит'
        APARTMENT = 'A', 'Апартамент'
        LUX = 'L', 'Люкс'
        JUNIOR_SUITE = 'JSU', 'Джуниор сюит'
        STUDIO = 'ST', 'Студия'
        FIRST = '1', 'Первая категория (стандарт)'
        SECOND = '2', 'Вторая категория'
        THIRD = '3', 'Третья категория'
        FOURTH = '4', 'Четвёртая категория'
        FIFTH = '5', 'Пятая категория'

    PREMIUM_TIERS = (
        Tier.SUITE,
        Tier.APARTMENT,
        Tier.LUX,
        Tier.JUNIOR_SUITE,
        Tier.STUDIO,
    )

    STANDARD_TIERS = (
        Tier.FIRST,
        Tier.SECOND,
        Tier.THIRD,
        Tier.FOURTH,
        Tier.FIFTH,
    )

    tier = models.CharField(
        max_length=3,
        choices=Tier.choices,
        unique=True,
        verbose_name='Категория',
    )
    min_area = models.PositiveSmallIntegerField(verbose_name='Минимальная площадь (кв.м.)')
    requires_kitchen = models.BooleanField(
        default=False,
        verbose_name='Требуется кухонное оборудование',
    )
    required_bathroom_type = models.CharField(
        max_length=1,
        choices=BathroomType.choices,
        default=BathroomType.FULL,
        verbose_name='Необходимый тип санузла'
    )
    min_rooms = models.PositiveSmallIntegerField(
        default=1,
        verbose_name='Минимальное количество комнат',
    )

    class Meta:
        db_table = 'room_category'
        verbose_name = 'Категория номера'
        verbose_name_plural = 'Категории номеров'
        ordering = ['tier']

    @property
    def is_premium(self):
        return self.tier in self.PREMIUM_TIERS

    @property
    def is_standard(self):
        return self.tier in self.STANDARD_TIERS

    def __str__(self):
        return self.get_tier_display()


class RoomType(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Название типа',
    )
    category = models.ForeignKey(
        'hotels.RoomCategory',
        on_delete=models.PROTECT,
        related_name='room_types',
        verbose_name='Категория по классификации',
    )
    description = models.TextField(
        verbose_name='Описание',
    )
    size = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(2, message='Номер должен быть размером хотя бы 2 кв.м.')],
        verbose_name='Площадь (кв.м.)',
        help_text='в квадратных метрах',
    )
    standard_capacity = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1, message='Номер должен вмещать хотя бы одного человека')],
        verbose_name='Вместимость',
    )
    bedroom_count = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1, message='Номер должен иметь хотя бы одну спальню')],
        verbose_name='Количество спален',
    )
    living_room_count = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0, message='Количество гостинных не может быть меньше нуля')],
        verbose_name='Количество гостинных',
    )
    bathroom_count = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0, message='Количество ванных не может быть меньше нуля')],
        verbose_name='Количество ванных комнат',
    )
    bathroom_type = models.CharField(
        max_length=1,
        choices=RoomCategory.BathroomType.choices,
        default=RoomCategory.BathroomType.FULL,
        verbose_name='Тип санузла',
    )
    has_kitchen = models.BooleanField(
        default=False,
        verbose_name='Есть кухня',
    )
    has_balcony = models.BooleanField(
        default=False,
        verbose_name='Есть балкон',
    )

    class Meta:
        db_table = 'room_type'
        verbose_name = 'Тип номера'
        verbose_name_plural = 'Типы номеров'
        ordering = ['name', '-standard_capacity', '-size']

    def clean(self):
        if self.category:
            if self.size:
                min_area = self.category.min_area
                if self.size < min_area:
                    raise ValidationError(
                        f'Площадь номера категории "{self.category}" '
                        f'не может быть меньше {min_area} кв.м. '
                    )
            if (self.bedroom_count + self.living_room_count) < self.category.min_rooms:
                raise ValidationError(
                    f'Категория "{self.category}" требует минимум '
                    f'{self.category.min_rooms} комнат(ы)'
                )
            if self.category.requires_kitchen and not self.has_kitchen:
                raise ValidationError(
                    f'Категория "{self.category}" требует наличия кухни'
                )
            if self.bathroom_type:
                if self.category.required_bathroom_type == RoomCategory.BathroomType.FULL:
                    if (self.bathroom_type != RoomCategory.BathroomType.FULL
                        or self.bathroom_count < 1):
                        raise ValidationError(
                            f'Категория "{self.category}" требует наличия полного санузла'
                        )
                if self.category.required_bathroom_type == RoomCategory.BathroomType.PARTIAL:
                    if self.bathroom_type not in (
                        RoomCategory.BathroomType.FULL, RoomCategory.BathroomType.PARTIAL
                    ) or self.bathroom_count < 1:
                        raise ValidationError(
                            f'Категория "{self.category}" требует'
                            'наличия хотя бы частичного санузла'
                        )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Room(models.Model):
    hotel = models.ForeignKey(
        'hotels.Hotel',
        on_delete=models.CASCADE,
        related_name='rooms',
    )
    room_type = models.ForeignKey(
        'hotels.RoomType',
        on_delete=models.CASCADE,
        related_name='rooms',
    )
    bed_count = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1, message='Номер должен иметь хотя бы одно спальное место')],
        verbose_name='Количество спальных мест',
    )
    is_pets_allowed = models.BooleanField(
        default=False,
        verbose_name='Можно с животными',
    )
    is_smoking_allowed = models.BooleanField(
        default=False,
        verbose_name='Можно курить',
    )
    price_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0, message='Цена не может быть меньше нуля')],
        verbose_name='Цена за ночь',
    )
    extra_pay_per_person = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0, message='Цена не может быть меньше нуля')],
        verbose_name='Доплата за дополнительного человека',
    )
    floor = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1, message='Этаж не может быть меньше 1'),
            MaxValueValidator(Hotel.MAX_FLOOR_COUNT, message='Этаж не может быть больше 10'),
        ],
        verbose_name='Номер этажа',
    )
    number_on_floor = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1, message='Минимальный порядковый номер комнаты равен 1'),
            MaxValueValidator(99, message='Максимальный порядковый номер комнаты равен 99'),
        ],
        verbose_name='Порядковый номер на этаже',
    )
    variant = models.CharField(
        max_length=1,
        null=True,
        blank=True,
        validators=[RegexValidator(
            regex=r'^[A-Z]$',
            message='Вариация может быть только латинской буквой в высшем регистре',
        )],
        verbose_name='Вариация номера',
        help_text='Например, 1A и 1B (указать только букву)',
    )

    objects = RoomManager()

    class Meta:
        db_table = 'room'
        verbose_name = 'Номер'
        verbose_name_plural = 'Номера'
        ordering = ['floor', 'number_on_floor', 'variant']
        constraints = [
            models.UniqueConstraint(
                fields=('hotel', 'floor', 'number_on_floor', 'variant'),
                name='unique_room_per_hotel',
                violation_error_message='В отеле может быть только одна комната '
                'с таким номером и вариантом на этаже'
            )
        ]

    def clean(self, *args, **kwargs):
        hotel = self.hotel
        if hotel and self.floor > hotel.floor_count:
            raise ValidationError(
                f'Максимальное количество этажей в отеле {hotel}: {hotel.floor_count}'
            )
        super().clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def room_number(self) -> str:
        number_on_floor = str(self.number_on_floor).rjust(2, '0')
        return f'{self.floor}{number_on_floor}{self.variant if self.variant else ""}'

    def __str__(self) -> str:
        return self.room_number


def _photo_path(instance, filename) -> str:
    return f'hotels/{instance.room.hotel_id}/rooms/{instance.room_id}/{filename}'

class RoomPhoto(models.Model):
    room = models.ForeignKey(
        'hotels.Room',
        on_delete=models.CASCADE,
        related_name='photos',
    )
    photo_url = models.URLField(
        verbose_name='Фото URL',
    )
    order_number = models.PositiveSmallIntegerField(
        verbose_name='Порядковый номер',
    )

    class Meta:
        db_table = 'room_photo'
        verbose_name = 'Фото номера'
        verbose_name_plural = 'Фото номеров'
        ordering = [
            'room__hotel__name', 'room__floor',
            'room__number_on_floor', 'room__variant', 'order_number'
        ]

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if not self.pk:
                RoomPhoto.objects.filter(
                    room=self.room,
                    order_number__gte=self.order_number
                ).update(order_number=models.F('order_number') + 1)
            else:
                old = RoomPhoto.objects.get(pk=self.pk)
                if old.order_number != self.order_number:
                    if self.order_number > old.order_number:
                        RoomPhoto.objects.filter(
                            room=self.room,
                            order_number__gt=old.order_number,
                            order_number__lte=self.order_number
                        ).update(order_number=models.F('order_number') - 1)
                    else:
                        RoomPhoto.objects.filter(
                            room=self.room,
                            order_number__gte=self.order_number,
                            order_number__lt=old.order_number
                        ).update(order_number=models.F('order_number') + 1)
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        order_number = self.order_number
        room = self.room
        super().delete(*args, **kwargs)
        RoomPhoto.objects.filter(room=room, order_number__gt=order_number) \
            .update(order_number=models.F('order_number') - 1)

    def __str__(self) -> str:
        return f'Фото №{self.order_number} комнаты {self.room}'
