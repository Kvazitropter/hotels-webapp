from django.db import models
from django.contrib.auth.models import AbstractUser, Group as BaseGroup
from phonenumber_field.modelfields import PhoneNumberField

from app.accounts.managers import UserManager


class Group(BaseGroup):
    '''
    Прокси-модель Group, добавляющая verbose_name.
    '''
    class Meta:
        proxy = True
        verbose_name = 'Группа пользователей'
        verbose_name_plural = 'Группы пользователей'
        ordering = ['name']


class User(AbstractUser):
    '''
    Кастомная модель пользователя, наследующая AbstractUser.
    В качестве идентификатора используется email, поле username отключено.
    '''
    class Role(models.TextChoices):
        GUEST = 'guest', 'Гость'
        MODERATOR = 'moderator', 'Модератор'
        ADMIN = 'admin', 'Администратор'
        NO_ROLE = 'no role', 'Нет роли'

    username = None
    email = models.EmailField(
        max_length=100,
        unique=True,
        error_messages={'invalid': 'Введен некорректный email.'},
        verbose_name='Электронная почта',
        help_text='Обязательное поле, должно быть уникальным.'
    )
    phone_number = PhoneNumberField(
        null=False,
        blank=False,
        unique=True,
        error_messages={'invalid': 'Введите номер в формате +7XXXXXXXXXX или 8XXXXXXXXXX.'},
        verbose_name='Номер телефона',
    )
    first_name = models.CharField(
        max_length=100,
        verbose_name='Имя',
    )
    middle_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Отчество',
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name='Фамилия',
    )
    date_of_birth = models.DateField(
        null=True,
        verbose_name='Дата рождения',
    )

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ('first_name', 'last_name', 'phone_number')
    objects = UserManager()

    class Meta:
        db_table = 'user'
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['-date_joined']),
        ]
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    @property
    def full_name(self) -> str:
        '''
        Возвращает полное имя пользователя в формате:
        Имя Отчество Фамилия (если отчество указано) или Имя Фамилия.
        '''
        names = [self.last_name, self.first_name, self.middle_name]
        return ' '.join(filter(None, names))

    @property
    def short_name(self) -> str:
        '''
        Возвращает краткое имя: Фамилия И.О. или Фамилия И., если отчества нет.
        '''
        first_initial = f'{self.first_name[0]}.'
        middle_initial = f'{self.middle_name[0]}.' if self.middle_name else ''
        return f"{self.last_name} {first_initial}{middle_initial}"

    @property
    def is_admin(self) -> bool:
        return hasattr(self, 'admin')

    @is_admin.setter
    def is_admin(self, _):
        raise ValueError('Назначьте соответствующую роль через user.assign_role(role)')

    @property
    def is_moderator(self) -> bool:
        return hasattr(self, 'moderator')

    @is_moderator.setter
    def is_moderator(self, _):
        raise ValueError('Назначьте соответствующую роль через user.assign_role(role)')

    @property
    def is_guest(self) -> bool:
        return hasattr(self, 'guest')

    @is_guest.setter
    def is_guest(self, _):
        raise ValueError('Назначьте соответствующую роль через user.assign_role(role)')

    @property
    def is_superuser(self) -> bool:
        return self.is_admin

    @is_superuser.setter
    def is_superuser(self, _):
        raise ValueError('Назначьте роль администратора')

    @property
    def is_staff(self) -> bool:
        return self.is_moderator or self.is_admin

    @is_staff.setter
    def is_staff(self, _):
        raise ValueError('Назначьте роль администратора или модератора')

    @property
    def role(self) -> str:
        '''
        Возвращает основную роль пользователя.
        '''
        if self.is_admin:
            return User.Role.ADMIN
        if self.is_moderator:
            return User.Role.MODERATOR
        if self.is_guest:
            return User.Role.GUEST
        return User.Role.NO_ROLE

    def get_full_name(self) -> str:
        '''
        Возвращает ФИО пользователя.
        '''
        return self.full_name

    def get_short_name(self) -> str:
        '''
        Возвращает Фамилия И.(О). пользователя.
        '''
        return self.short_name

    def assign_role(self, role: str) -> None:
        if role == User.Role.GUEST:
            if self.is_guest:
                raise ValueError('Пользователь уже является гостем')
            Guest.objects.create(user=self)
        elif role == User.Role.MODERATOR:
            if self.is_moderator:
                raise ValueError('Пользователь уже является модератором')
            Moderator.objects.create(user=self)
        elif role == User.Role.ADMIN:
            if self.is_admin:
                raise ValueError('Пользователь уже является администратором')
            Administrator.objects.create(user=self)
        else:
            raise ValueError(f'Неизвестная роль пользователя: {role}')

    def remove_role(self, role: str) -> None:
        if role == User.Role.GUEST:
            if not self.is_guest:
                raise ValueError('Пользователь уже не является гостем')
            self.guest.delete()
            self.save()
        elif role == User.Role.MODERATOR:
            if not self.is_moderator:
                raise ValueError('Пользователь уже не является модератором')
            self.moderator.delete()
            self.save()
        elif role == User.Role.ADMIN:
            if not self.is_admin:
                raise ValueError('Пользователь уже не является администратором')
            self.admin.delete()
            self.save()
        else:
            raise ValueError(f'Неизвестная роль пользователя: {role}')

    def __str__(self) -> str:
        return f'{self.role} {self.full_name}, {self.email}, {self.phone_number}'


class Guest(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='guest',
        verbose_name='Пользователь'
    )

    class Meta:
        db_table = 'guest'
        verbose_name = 'Гость'
        verbose_name_plural = 'Гости'

    def __str__(self):
        return str(self.user)


class Moderator(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='moderator',
        verbose_name='Пользователь'
    )

    class Meta:
        db_table = 'moderator'
        verbose_name = 'Модератор'
        verbose_name_plural = 'Модераторы'

    def __str__(self):
        return str(self.user)


class Administrator(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='admin',
        verbose_name='Пользователь'
    )

    class Meta:
        db_table = 'admin'
        verbose_name = 'Администратор'
        verbose_name_plural = 'Администраторы'

    def __str__(self):
        return str(self.user)
