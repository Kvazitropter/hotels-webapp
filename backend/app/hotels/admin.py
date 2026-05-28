from django.contrib import admin
from django.utils.html import format_html
from app.hotels.models import Hotel, RoomCategory, RoomType, Room, RoomPhoto


class RoomPhotoInline(admin.TabularInline):
    model = RoomPhoto
    extra = 0
    fields = ['photo_url', 'photo_preview', 'order_number']
    readonly_fields = ['photo_preview']

    @admin.display(description='Превью')
    def photo_preview(self, obj):
        if obj.photo_url:
            return format_html(
                '<img src="{}" style="height:60px;border-radius:4px">',
                obj.photo_url
            )
        return '-'


class RoomInline(admin.TabularInline):
    model = Room
    extra = 0
    fields = ['room_number', 'floor', 'number_on_floor', 'variant', 'price_per_night']
    readonly_fields = ['room_number']
    show_change_link = True

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('hotel', 'room_type')

    @admin.display(description='Номер')
    def room_number(self, obj):
        return obj.room_number


class RoomTypeInline(admin.TabularInline):
    """Показывает типы номеров прямо в карточке категории."""
    model = RoomType
    extra = 0
    fields = ['name', 'size', 'bedroom_count', 'bathroom_count', 'has_balcony']
    show_change_link = True


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'city', 'country', 'phone_number', 'email',
        'floor_count', 'check_in_time', 'check_out_time', 'is_active'
    ]
    list_per_page = 30
    list_editable = ['is_active']
    list_filter = ['is_active', 'country', 'city']
    search_fields = ['name', 'city', 'address', 'email', 'phone_number']
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'country', 'city', 'address', 'floor_count'),
        }),
        ('Контакты', {
            'fields': ('phone_number', 'email'),
        }),
        ('Время заезда/выезда', {
            'fields': ('check_in_time', 'check_out_time'),
        }),
        ('Настройки', {
            'fields': ('is_active',),
        }),
    )


@admin.register(RoomCategory)
class RoomCategoryAdmin(admin.ModelAdmin):
    search_fields = ['tier']
    inlines = [RoomTypeInline]
    list_display = [
        'get_tier_display_name', 'get_is_premium', 'min_area',
        'min_rooms', 'requires_kitchen', 'required_bathroom_type',
    ]
    list_filter = ['requires_kitchen', 'required_bathroom_type']
    ordering = ['-min_area', '-min_rooms', 'tier']
    fieldsets = (
        ('Категория', {
            'fields': ('tier',),
        }),
        ('Требования по классификации', {
            'fields': ('min_area', 'min_rooms', 'requires_kitchen', 'required_bathroom_type'),
        }),
    )

    @admin.display(description='Категория')
    def get_tier_display_name(self, obj):
        return obj.get_tier_display()

    @admin.display(description='Высшая категория', boolean=True)
    def get_is_premium(self, obj):
        return obj.is_premium


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'size', 'standard_capacity',
        'bedroom_count', 'bathroom_count', 'bathroom_type',
        'has_kitchen', 'has_balcony',
    ]
    list_per_page = 30
    list_filter = ['category', 'has_balcony', 'has_kitchen', 'bathroom_type']
    search_fields = ['name', 'description']
    ordering = ['-category__min_area', '-category__min_rooms', 'category__tier', '-size', 'name']
    autocomplete_fields = ['category']
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'category', 'description'),
        }),
        ('Параметры номера', {
            'fields': ('size', 'standard_capacity'),
        }),
        ('Состав номера', {
            'fields': (
                'bedroom_count', 'bathroom_count',
                'bathroom_type', 'has_kitchen', 'has_balcony',
            ),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_select_related = ['hotel', 'room_type', 'room_type__category']
    inlines = [RoomPhotoInline]
    list_display = [
        'room_number', 'get_room_type', 'get_category',
        'get_hotel', 'floor', 'bed_count',
        'price_per_night', 'is_pets_allowed',
    ]
    list_per_page = 30
    list_filter = [
        'hotel', 'room_type', 'room_type__category',
        'is_pets_allowed', 'is_smoking_allowed',
    ]
    ordering = ['hotel__name', 'floor', 'number_on_floor', 'variant']
    readonly_fields = ['room_number']
    search_fields = ['room_type__name', 'hotel__name']
    autocomplete_fields = ['hotel', 'room_type']
    fieldsets = (
        ('Основная информация', {
            'fields': ('hotel', 'room_type', 'room_number', 'floor', 'number_on_floor', 'variant'),
        }),
        ('Спальные места', {
            'fields': ('bed_count',),
        }),
        ('Особенности', {
            'fields': ('is_pets_allowed', 'is_smoking_allowed'),
        }),
        ('Ценообразование', {
            'fields': ('price_per_night', 'extra_pay_per_person'),
        }),
    )

    @admin.display(description='Номер', ordering=('floor', 'number_on_floor', 'variant'))
    def room_number(self, obj):
        return obj.room_number

    @admin.display(description='Тип номера', ordering='room_type__name')
    def get_room_type(self, obj):
        return obj.room_type.name

    @admin.display(description='Категория', ordering='room_type__category__tier')
    def get_category(self, obj):
        return obj.room_type.category

    @admin.display(description='Отель', ordering='hotel__name')
    def get_hotel(self, obj):
        return obj.hotel.name

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'hotel', 'room_type', 'room_type__category'
        )


@admin.register(RoomPhoto)
class RoomPhotoAdmin(admin.ModelAdmin):
    list_select_related = ['room', 'room__hotel']
    list_display = ['get_room_number', 'photo_preview', 'order_number']
    list_per_page = 30
    search_fields = ['room__room_type__name', 'room__hotel__name']
    ordering = ['room__hotel__name', 'room__floor', 'room__number_on_floor', 'room__variant']
    fieldsets = (
        ('Загрузка фото', {
            'fields': ('room', 'photo_url', 'order_number'),
        }),
    )

    @admin.display(description='Превью')
    def photo_preview(self, obj):
        if obj.photo_url:
            return format_html(
                '<img src="{}" style="height:60px;border-radius:4px">',
                obj.photo_url
            )
        return '-'

    @admin.display(
        description='Номер комнаты',
        ordering=['room__hotel__name', 'room__floor', 'room__number_on_floor', 'room__variant'],
    )
    def get_room_number(self, obj):
        return obj.room.room_number

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'room', 'room__hotel'
        )
