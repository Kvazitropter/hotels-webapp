import difflib
import re
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Model
import phonenumbers
from phonenumbers import NumberParseException
from rest_framework import serializers


def validate_lookup_str(lookup_str: str) -> tuple[bool, Optional[str]]:
    """Проверяет, что строка соответствует формату "ключ=значение, ключ2=значение2".

    Аргументы:
        lookup_str (str): Строка для проверки.

    Возвращает:
        Кортеж, состоящий из:
        - bool: Валидна ли строка
        - Optional[str]: Строка с сообщением ошибки, если строка невалидна
    """
    if not lookup_str.strip():
        return True, None

    parts = [part.strip() for part in lookup_str.strip().split(',')]
    pattern = re.compile(r'^(\w*)\s*=\s*(.*)$')

    for part in parts:
        if not re.match(pattern, part):
            return (
                False,
                f'Неверный формат пары: "{part}". Правильный формат "имя_поля=значение"'
            )

    return True, None


def validate_lookup_params(
    model: Model, lookup_params: dict
) -> tuple[bool, list[str], dict[str, list[str]]]:
    """Проверяет, существуют ли указанные поля в модели Django.

    Аргументы:
        model (Model): Модель Django
        lookup_params (dict): Словарь с параметрами поиска

    Возвращает:
        Кортеж из трёх элементов:
            - bool: True, если все поля существуют, иначе False.
            - list[str]: Список невалидных (отсутствующих) полей.
            - dict[str, list[str]]: Словарь, где ключ — невалидное поле,
              значение — список из похожих допустимых полей
    """
    field_names = {f.name for f in model._meta.concrete_fields}
    wrong_fields = []
    suggestions = {}

    for key in lookup_params.keys():
        base_key = key.split('__')[0]
        if base_key not in field_names:
            wrong_fields.append(base_key)
            similar = difflib.get_close_matches(base_key, field_names, cutoff=0.6)
            suggestions[base_key] = similar

    return len(wrong_fields) == 0, wrong_fields, suggestions


def validate_email(email: str) -> bool:
    return re.match(r'.+@.+', email)


def validate_phone(phone_str: str) -> bool:
    try:
        num = phonenumbers.parse(phone_str, settings.PHONENUMBER_DEFAULT_REGION)
    except NumberParseException:
        return False
    return phonenumbers.is_valid_number(num)


def validate_instance_for_serializer(instance: Model) -> Model:
    try:
        instance.full_clean()
    except DjangoValidationError as e:
        raise serializers.ValidationError(e.message_dict)
    return instance
