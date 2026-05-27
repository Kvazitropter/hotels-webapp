from django.contrib import admin
from django.utils.html import format_html
from app.bookings.models import Booking, CancelledBooking, Review


class ReviewInline(admin.StackedInline):
    model = Review
    extra = 0
    readonly_fields = ['created_at', 'published_at']
    fields = [
        'rating', 'comment', 'status', 'moderated_by',
        'rejection_reason', 'published_at', 'created_at'
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('moderated_by')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    inlines = [ReviewInline]
    list_select_related = ['guest', 'guest__user', 'room', 'room__hotel', 'room__room_type']
    list_display = [
        'id', 'get_user', 'get_hotel', 'get_room', 'check_in_date', 'check_out_date',
        'days_count', 'status'
    ]
    list_per_page = 30
    list_filter = ['status', 'room__hotel', 'room__room_type']
    search_fields = [
        'guest__user__last_name', 'guest__user__first_name',
        'guest__user__last_name', 'guest__user__phone_number',
    ]
    readonly_fields = ['created_at', 'days_count']
    fieldsets = (
        ('Основная информация', {
            'fields': ('room', 'check_in_date', 'check_out_date', 'days_count', 'created_at'),
        }),
        ('Гость', {
            'fields': ('guest', 'adults_count', 'children_count', 'pets_count'),
        }),
        ('Статус и тип', {
            'fields': ('status', 'moved_to'),
        }),
    )

    @admin.display(description='Гость', ordering='guest__user__last_name')
    def get_user(self, obj):
        return obj.guest.user.short_name

    @admin.display(description='Отель', ordering='room__hotel__name')
    def get_hotel(self, obj):
        return obj.room.hotel.name

    @admin.display(description='Номер', ordering=('room__floor', 'room__number_on_floor'))
    def get_room(self, obj):
        return obj.room.room_number

    @admin.display(description='Количество суток')
    def days_count(self, obj):
        return obj.days_count

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'guest', 'guest__user', 'room', 'room__hotel', 'room__room_type'
        )


@admin.register(CancelledBooking)
class CancelledBookingAdmin(admin.ModelAdmin):
    list_select_related = ['booking', 'booking__guest__user', 'booking__room']
    list_display = [
        'id', 'booking', 'get_user', 'get_hotel', 'cancelled_at'
    ]
    list_per_page = 30
    search_fields = [
        'booking__guest__user__email', 'booking__guest__user__phone_number',
        'booking__guest__user__last_name', 'cancellation_reason', 'booking__id'
    ]
    readonly_fields = ['cancelled_at', 'booking']
    fieldsets = (
        ('Бронирование', {
            'fields': ('booking',),
        }),
        ('Отмена', {
            'fields': ('cancellation_reason', 'cancelled_at'),
        }),
    )

    @admin.display(description='Гость', ordering='booking__guest__user__last_name')
    def get_user(self, obj):
        return obj.booking.guest.user.short_name

    @admin.display(description='Отель', ordering='booking__room__hotel__name')
    def get_hotel(self, obj):
        return obj.booking.room.hotel.name

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'booking__guest__user', 'booking__room__hotel'
        )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_select_related = [
        'booking', 'booking__guest__user',
        'moderated_by', 'moderated_by__user'
    ]
    list_display = ['get_user', 'rating', 'get_stars', 'created_at', 'status', 'get_moderated_by']
    list_per_page = 30
    list_filter = ['rating', 'status']
    readonly_fields = ['created_at', 'published_at']
    search_fields = [
        'booking__guest__user__email', 'booking__guest__user__phone_number',
        'booking__guest__user__last_name', 'comment',
    ]
    fieldsets = (
        ('Бронь', {
            'fields': ('booking',),
        }),
        ('Отзыв', {
            'fields': ('rating', 'comment', 'created_at'),
        }),
        ('Модерация', {
            'fields': ('status', 'moderated_by', 'rejection_reason'),
        }),
        ('Публикация', {
            'fields': ('published_at',),
        }),
    )

    @admin.display(description='Гость', ordering='booking__guest__user__last_name')
    def get_user(self, obj):
        return obj.booking.guest.user.short_name

    @admin.display(description='Оценка')
    def get_stars(self, obj):
        filled = chr(0x2605) * obj.rating
        empty = chr(0x2606) * (5 - obj.rating)
        return format_html(
            '<span style="font-size:14px">{}{}</span>',
            filled, empty,
        )

    @admin.display(description='Модератор', ordering='moderated_by__user__last_name')
    def get_moderated_by(self, obj):
        if obj.moderated_by:
            return obj.moderated_by.user.short_name
        return '-'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'booking__guest__user', 'moderated_by__user'
        )
