from django.contrib import admin
from app.hotels.models import Hotel, RoomType, Room, RoomPhoto


class RoomInline(admin.TabularInline):
    model = Room
    extra = 1
    fields = ('hotel', 'floor', 'number_on_floor', 'variant')
    readonly_fields = ('room_number',)
    show_change_link = True


class RoomPhotoInline(admin.TabularInline):
    model = RoomPhoto
    extra = 1
    fields = ('photo', 'sort_order_number')


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'country', 'phone_number', 'email', 'is_active')
    list_per_page = 30
    list_editable = ('is_active',)
    list_filter = ('is_active', 'city', 'country')
    search_fields = ('name', 'city', 'address')
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'country', 'city', 'address'),
        }),
        ('Контакты', {
            'fields': ('phone_number', 'email'),
        }),
        ('Настройки', {
            'fields': ('is_active',),
        }),
    )


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    inlines = (RoomInline,)
    list_display = ('name', 'size', 'capacity', 'bedroom_count', 'bathroom_count')
    list_per_page = 30
    list_filter = ('has_balcony',)
    search_fields = ('name', 'description')
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description'),
        }),
        ('Параметры', {
            'fields': ('size', 'capacity', 'bedroom_count', 'bathroom_count'),
        }),
        ('Особенности', {
            'fields': ('has_balcony',),
        }),
    )


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_select_related = ('hotel', 'room_type')
    inlines = (RoomPhotoInline,)
    list_display = ('room_number', 'room_type__name', 'hotel__name')
    list_per_page = 30
    list_filter = ('hotel', 'room_type')
    readonly_fields = ('room_number',)
    search_fields = ('room_type__name', 'hotel__name', 'floor', 'number_on_floor')
    fieldsets = (
        ('Основная информация', {
            'fields': ('room_type', 'floor', 'number_on_floor', 'variant'),
        }),
        ('Особенности', {
            'fields': ('is_pets_allowed', 'is_smoking_allowed'),
        }),
        ('Ценообразование', {
            'fields': ('price_per_night', 'extra_pay_per_person'),
        }),
    )

    @admin.display(
        description='Номер',
        ordering=('hotel__name', 'floor', 'number_on_floor', 'variant')
    )
    def room_number(self, obj):
        return obj.room_number


@admin.register(RoomPhoto)
class RoomPhotoAdmin(admin.ModelAdmin):
    list_select_related = ('room',)
    list_display = ('room_number', 'photo', 'sort_order_number')
    list_per_page = 30
    search_fields = (
        'room__floor', 'room__number_on_floor',
        'room__room_type__name', 'room__hotel__name'
    )
    fieldsets = (
        ('Загрузка фото', {
            'fields': ('room', 'photo', 'sort_order_number'),
        }),
    )

    @admin.display(
        description='Номер комнаты',
        ordering=('room__hotel__name', 'floor', 'number_on_floor', 'variant')
    )
    def room_number(self, obj):
        return obj.room.room_number
