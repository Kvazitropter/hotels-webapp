from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin
from django.contrib.auth.models import Group as BaseGroup

from app.accounts.models import Group, Guest, Moderator, Administrator


User = get_user_model()


class GuestInline(admin.StackedInline):
    model = Guest
    can_delete = True
    verbose_name = 'Гость'
    extra = 0


class ModeratorInline(admin.StackedInline):
    model = Moderator
    can_delete = True
    verbose_name = 'Модератор'
    extra = 0


class AdministratorInline(admin.StackedInline):
    model = Administrator
    can_delete = True
    verbose_name = 'Администратор'
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'email', 'full_name', 'phone_number',
        'role', 'is_active', 'date_joined',
    ]
    list_per_page = 30
    list_filter = ['is_active', 'date_joined']
    ordering = ['-date_joined', '-last_login', 'last_name', 'first_name']
    search_fields = ['email', 'first_name', 'last_name', 'phone_number']
    readonly_fields = ['date_joined', 'last_login', 'role']
    fieldsets = (
        (None, {
            'fields': ('email', 'password'),
        }),
        ('Личные данные', {
            'fields': (
                'first_name', 'middle_name', 'last_name',
                'phone_number', 'date_of_birth',
            ),
        }),
        ('Права и роль', {
            'fields': ('is_active', 'role', 'groups', 'user_permissions'),
        }),
        ('Даты', {
            'fields': ('last_login', 'date_joined'),
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'first_name', 'last_name',
                'phone_number', 'password1', 'password2',
            ),
        }),
    )

    @admin.display(description='ФИО', ordering=('last_name', 'middle_name', 'first_name'))
    def full_name(self, obj):
        '''
        Возвращает полное имя пользователя
        '''
        return obj.full_name

    @admin.display(description='Основная роль')
    def role(self, obj):
        return obj.role.label

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('groups') \
            .select_related('guest', 'moderator', 'admin')


@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ['user']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    autocomplete_fields = ['user']


@admin.register(Moderator)
class ModeratorAdmin(admin.ModelAdmin):
    list_display = ['user']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    autocomplete_fields = ['user']


@admin.register(Administrator)
class AdministratorAdmin(admin.ModelAdmin):
    list_display = ['user']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    autocomplete_fields = ['user']


admin.site.unregister(BaseGroup)
admin.site.register(Group, GroupAdmin)
