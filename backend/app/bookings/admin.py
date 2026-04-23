from django.contrib import admin
from app.bookings.models import Booking, Review


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 1
    fields = ('rating', 'comment')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    inlines = (ReviewInline,)
    list_display = ('user', 'room', 'check_in_date', 'check_out_date')
    list_per_page = 30
    list_filter = ('status', 'room__hotel__name', 'room__room_type__name')
    readonly_fields = ('total_price', 'created_at')
    search_fields = ('room__room_number',)
    fieldsets = (
        ('Основная информация', {
            'fields': ('room', 'check_in_date', 'check_out_date', 'status'),
        }),
        ('Гость', {
            'fields': ('user', 'adults_count', 'children_count', 'pets_count'),
        }),
        ('Оплата', {
            'fields': ('payment_status',),
        }),
        ('Отмена', {
            'fields': ('cancelled_at', 'cancellation_reason'),
        }),
    )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('booking', 'rating', 'created_at', 'status')
    list_per_page = 30
    list_filter = ('rating', 'status')
    readonly_fields = ('created_at',)
    search_fields = (
        'comment', 'booking__user__email',
        'booking__user__phone', 'room__room_type__name'
    )
    fieldsets = (
        ('Бронь', {
            'fields': ('booking',),
        }),
        ('Отзыв', {
            'fields': ('rating', 'comment'),
        }),
        ('Модерация и публикация', {
            'fields': ('status', 'moderated_by', 'rejection_reason', 'published_at'),
        }),
    )
