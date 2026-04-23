from decimal import Decimal

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone

from app.bookings.utils.helpers.calculate_total_price import calculate_total_price


class _BookingStatus(models.TextChoices):
    ACTIVE = 'A', 'Активно'
    MOVED = 'M', 'Перенесено'
    CANCELLED = 'CA', 'Отменено'
    CLOSED = 'CL', 'Завершено'

class _BookingPaymentStatus(models.TextChoices):
    OPEN = 'O', 'Не оплачено'
    CLOSED = 'C', 'Оплачено'

class Booking(models.Model):
    Status = _BookingStatus
    PaymentStatus = _BookingPaymentStatus

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='Зарегистрированный пользователь'
    )
    room = models.ForeignKey(
        'hotels.Room',
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='Номер',
    )
    adults_count = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1, message='В брони должен быть хотя бы один взрослый')],
        verbose_name='Количество взрослых',
    )
    children_count = models.PositiveSmallIntegerField(
        verbose_name='Количество детей',
    )
    pets_count = models.PositiveSmallIntegerField(
        verbose_name='Количество животных',
    )
    check_in_date = models.DateTimeField(
        verbose_name='Дата въезда',
    )
    check_out_date = models.DateTimeField(
        verbose_name='Дата выселения',
    )
    status = models.CharField(
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name='Статус брони',
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='К оплате',
        help_text='Будет расчитана после добавления записи о брони',
    )
    payment_status = models.CharField(
        choices=PaymentStatus.choices,
        default=PaymentStatus.OPEN,
        verbose_name='Статус платежа',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания',
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата отмены',
    )
    cancellation_reason = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Причина отмены',
    )

    class Meta:
        db_table = 'booking'
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        ordering = [
            '-created_at', 'room__hotel__name',
            'room__floor', 'room__number_on_floor', 'user__last_name'
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(check_out_date__gt=models.F('check_in_date')),
                name='booking_checkout_after_checkin',
                violation_error_message='Дата выезда должна быть позже даты заезда'
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status=_BookingStatus.CANCELLED, cancelled_at__isnull=False,
                        cancellation_reason__isnull=False
                    ) |
                    models.Q(~models.Q(status=_BookingStatus.CANCELLED))
                ),
                name='booking_cancelled_at_required',
                violation_error_message='При отмене брони необходимо указать дату отмены и причину'
            ),
        ]

    def save(self, *args, **kwargs):
        if ((self.pk and self.total_price is None)
            or (self.status == self.Status.ACTIVE and
            self.payment_status == self.PaymentStatus.OPEN)):
            self.total_price = self._recalculate_total_price()
        if self.status == Booking.Status.CANCELLED and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        super().save(*args, **kwargs)

    def _recalculate_total_price(self) -> Decimal:
        room = self.room.only('room_type', 'price_per_night', 'extra_pay_per_person')
        room_type = self.room.select_related('room_type').room_type.only('capacity')
        return calculate_total_price(
            days=self.days_count,
            adults_count=self.adults_count,
            children_count=self.children_count,
            room_capacity=room_type.capacity,
            base_price=room.price_per_night,
            extra_person_price=room.extra_pay_per_person,
        )

    @property
    def days_count(self) -> int:
        return (self.check_out_date - self.check_in_date).days

    def __str__(self) -> str:
        return f'Бронь от {self.created_at}, {self.status}'


class _ReviewStatus(models.TextChoices):
    PUBLISHED = 'P', 'Опубликован'
    ON_MODERATION = 'M', 'Ожидает проверки'
    REJECTED = 'R', 'Не прошел модерацию'
    DELETED = 'D', 'Удален'


class Review(models.Model):
    Status = _ReviewStatus

    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name='review',
        verbose_name='Запись о бронировании',
    )
    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1, message='Минимальная оценка 1 звезда'),
            MaxValueValidator(5, message='Максимальная оценка 5 звезд'),
        ],
        verbose_name='Оценка',
    )
    comment = models.TextField(
        max_length=3072,
        null=True,
        blank=True,
        verbose_name='Комментарий',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания',
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ON_MODERATION,
    )
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_reviews',
    )
    rejection_reason = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Причина отказа',
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата публикации',
    )

    class Meta:
        db_table = 'review'
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at', 'status']
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(status=_ReviewStatus.PUBLISHED, published_at__isnull=False) |
                    models.Q(~models.Q(status=_ReviewStatus.PUBLISHED))
                ),
                name='review_published_at_required',
                violation_error_message='При публикации необходимо указать дату публикации'
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status__in=[_ReviewStatus.PUBLISHED, _ReviewStatus.REJECTED],
                        moderated_by__isnull=False
                    ) |
                    models.Q(status__in=[_ReviewStatus.ON_MODERATION, _ReviewStatus.DELETED])
                ),
                name='review_moderated_by_required',
                violation_error_message='После прохождения модерации должен быть сохранен модератор'
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status=_ReviewStatus.REJECTED, rejection_reason__isnull=False) |
                    models.Q(models.Q(~models.Q(status=_ReviewStatus.REJECTED)))
                ),
                name='review_rejection_reason_required',
                violation_error_message='После отказа в публикации должна быть указана причина'
            ),
        ]

    def clean(self):
        if self.booking.status != Booking.Status.CLOSED:
            raise ValidationError('Отзыв можно оставить только на завершённую бронь')

    def save(self, *args, **kwargs):
        if self.status == Review.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return (
            f'Оценка {self.rating} от {self.created_at}, {self.status}'
        )
