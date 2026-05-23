from datetime import date

from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone

from app.accounts.models import Guest, Moderator


User = get_user_model()


class _BookingStatus(models.TextChoices):
    ACTIVE = 'A', 'Активно'
    MOVED = 'M', 'Перенесено'
    CANCELLED = 'CA', 'Отменено'
    CLOSED = 'CL', 'Завершено'
    PENDING = 'P', 'В обработке'

class Booking(models.Model):
    class Type(models.TextChoices):
        GUARANTEED = 'G', 'Гарантированное'
        NOT_GUARANTEED = 'N', 'Негарантированное'
    Status = _BookingStatus

    guest = models.ForeignKey(
        Guest,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='Гость'
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
        default=0,
        validators=[MinValueValidator(0, 'Количество детей не может быть меньше нуля')],
        verbose_name='Количество детей',
    )
    pets_count = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0, 'Количество питомцев не может быть меньше нуля')],
        verbose_name='Количество питомцев',
    )
    check_in_date = models.DateField(verbose_name='Дата въезда')
    check_out_date = models.DateField(verbose_name='Дата выселения')
    status = models.CharField(
        max_length=2,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name='Статус бронирования',
    )
    type = models.CharField(
        max_length=2,
        choices=Type.choices,
        default=Type.GUARANTEED,
        verbose_name='Тип бронирования',
        help_text='С предоплатой или без (гарантированное/негарантированное)'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления',
    )
    moved_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moved_from',
        verbose_name='Новое бронирование (при переносе)'
    )

    class Meta:
        db_table = 'booking'
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        ordering = [
            '-created_at', 'room__hotel__name',
            'room__floor', 'room__number_on_floor', 'guest__user__last_name'
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(check_out_date__gt=models.F('check_in_date')),
                name='booking_check_out_after_check_in',
                violation_error_message='Дата выселения должна быть позже даты заселения'
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status=_BookingStatus.MOVED, moved_to__isnull=False) |
                    models.Q(~models.Q(status=_BookingStatus.MOVED))
                ),
                name='booking_moved_to_required',
                violation_error_message=('При переносе бронирования'
                    'необходимо указать ссылку на новое')
            ),
        ]

    def clean(self):
        if not self.room.hotel.is_active:
            raise ValidationError('Нельзя забронировать номер в неактивном отеле')

        overlapping = Booking.objects.filter(
            room=self.room,
            status=Booking.Status.ACTIVE,
            check_in_date__lt=self.check_out_date,
            check_out_date__gt=self.check_in_date,
        ).exclude(pk=self.pk)
        if overlapping.exists():
            raise ValidationError('Номер уже забронирован на выбранные даты.')

        if self.pets_count > 0 and not self.room.is_pets_allowed:
            raise ValidationError('В данном номере нельзя проживать с животными')

        total_guests = self.adults_count + self.children_count
        if total_guests > self.room.bed_count:
            raise ValidationError(
                f'Номер рассчитан на {self.room.bed_count} гостей, '
                f'указано {total_guests}'
            )

        if self.status == Booking.Status.CANCELLED and not hasattr(self, 'cancellation'):
            raise ValidationError(
                f'У бронирования со статусом "{self.get_status_display()}"'
                'должна быть соответствующая запись в таблице CancelledBooking'
            )

        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @transaction.atomic
    def cancel(self, reason: str) -> None:
        if self.status != Booking.Status.ACTIVE:
            raise ValueError('Нельзя отменить неактивное бронирование')
        self.status = Booking.Status.CANCELLED
        super(Booking, self).save(update_fields=['status'])
        CancelledBooking.objects.create(booking=self, cancellation_reason=reason)

    @transaction.atomic
    def move(self, new_check_in: date, new_check_out: date, **kwargs):
        if self.status != Booking.Status.ACTIVE:
            raise ValueError('Нельзя перенести неактивное бронирование')

        self.status = Booking.Status.PENDING
        super(Booking, self).save(update_fields=['status'])

        new_booking = Booking.objects.create(
            guest=self.guest,
            room=self.room,
            adults_count=self.adults_count,
            children_count=self.children_count,
            pets_count=self.pets_count,
            check_in_date=new_check_in,
            check_out_date=new_check_out,
            status=Booking.Status.ACTIVE,
            type=self.type,
            **kwargs,
        )
        self.status = Booking.Status.MOVED
        self.moved_to = new_booking
        super(Booking, self).save(update_fields=['status', 'moved_to'])

    @property
    def days_count(self) -> int:
        return (self.check_out_date - self.check_in_date).days

    def __str__(self) -> str:
        return f'Бронирование ({self.check_in_date:%d.%m.%Y}, {self.check_out_date:%d.%m.%Y})'


class _PaymentStatus(models.TextChoices):
    OPEN = 'O', 'Ждет оплаты'
    IRRELEVANT = 'I', 'Не актуально'
    EXPIRED = 'E', 'Просрочен'
    CLOSED = 'C', 'Оплачено'

class BookingPayment(models.Model):
    class Purpose(models.TextChoices):
        PREPAY = 'PP', 'Предоплата'
        FULL_PAYMENT = 'FP', 'Полная оплата бронирования'
        EXTRA_PAY = 'EP', 'Доплата'
        REFUND = 'RF', 'Возврат'
        PENALTY = 'PN', 'Штраф'

    Status = _PaymentStatus

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='Бронирование'
    )
    status = models.CharField(
        max_length=1,
        choices=Status.choices,
        default=Status.OPEN,
        verbose_name='Статус платежа'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='К оплате',
    )
    purpose = models.CharField(
        max_length=3,
        choices=Purpose.choices,
        default=Purpose.PREPAY,
        verbose_name='Назначение платежа'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата оплаты'
    )

    class Meta:
        db_table = 'booking_payment'
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        ordering = ['-created_at', '-paid_at']
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(status=_PaymentStatus.CLOSED, paid_at__isnull=False) |
                    models.Q(~models.Q(status=_PaymentStatus.CLOSED))
                ),
                name='booking_payment_paid_at_required',
                violation_error_message=('При закрытии платежа'
                    'необходимо указать дату оплаты')
            ),
        ]

    def __str__(self):
        return f'Оплата по {self.booking}, статус: {self.status}, сумма: {self.amount}'


class CancelledBooking(models.Model):
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name='cancellation',
        verbose_name='Бронирование'
    )
    cancelled_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата отмены',
    )
    cancellation_reason = models.CharField(
        max_length=255,
        verbose_name='Причина отмены',
    )

    class Meta:
        db_table = 'cancelled_booking'
        verbose_name = 'Отменненное бронирование'
        verbose_name_plural = 'Отмененные бронирования'
        ordering = ['-cancelled_at']

    def __str__(self) -> str:
        return f'Отмена {self.booking}'


class _ReviewStatus(models.TextChoices):
    PUBLISHED = 'P', 'Опубликован'
    DRAFT = 'D', 'Черновик'
    ON_MODERATION = 'M', 'Ожидает проверки'
    REJECTED = 'R', 'Не прошел модерацию'
    ARCHIVED = 'A', 'Убран из публичного доступа'


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
        max_length=1,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    moderated_by = models.ForeignKey(
        Moderator,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_reviews',
        verbose_name='Модератор'
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
                    models.Q(
                        status__in=[_ReviewStatus.PUBLISHED, _ReviewStatus.ARCHIVED],
                        published_at__isnull=False
                    ) |
                    models.Q(
                        ~models.Q(status__in=[_ReviewStatus.PUBLISHED, _ReviewStatus.ARCHIVED])
                    )
                ),
                name='review_published_at_required',
                violation_error_message='Необходимо указать дату публикации'
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        ~models.Q(status=_ReviewStatus.DRAFT),
                        moderated_by__isnull=False
                    ) | models.Q(status=_ReviewStatus.DRAFT)
                ),
                name='review_moderated_by_required',
                violation_error_message='Необходимо указать модератора'
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status=_ReviewStatus.REJECTED, rejection_reason__isnull=False) |
                    models.Q(models.Q(~models.Q(status=_ReviewStatus.REJECTED)))
                ),
                name='review_rejection_reason_required',
                violation_error_message='Необходимо указать причину отказа'
            ),
        ]

    def clean(self):
        if self.booking and self.booking.status != Booking.Status.CLOSED:
            raise ValidationError('Отзыв можно оставить только на завершенное бронирование')

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.status == Review.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return (
            f'Оценка {self.rating} от {self.created_at:%d.%m.%Y}, {self.get_status_display()}'
        )
