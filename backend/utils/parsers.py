import json
import re
from datetime import datetime, date

import phonenumbers


def parse_lookup(lookup_str: str) -> dict:
    """ Преобразует строку параметров фильтрации в словарь с типизированными значениями.

    Аргументы:
        lookup_str (str): Входная строка.

    Возвращает:
        dict: Словарь, где ключи — имена полей (строки), значения — преобразованные
        (bool, int, Decimal или исходная строка). Если входная строка пуста,
        возвращается пустой словарь.
    """
    params = {}
    if not lookup_str:
        return params
    for item in lookup_str.split(','):
        param, value = item.split('=', 1)
        params[param.strip()] = parse_value(value)
    return params


def parse_value(value: str) -> bool | int | float | str | list | dict | None | date | datetime:
    """
    Преобразует строковое представление значения в соответствующий тип.

    Поддерживаемые форматы:
    - `true` / `false` (регистронезависимо) -> bool
    - `null`, `none`, `None` -> None
    - Номера телефонов оставляются как есть -> исходная строка
    - Целые числа (только цифры) -> int
    - Числа с плавающей точкой (например, "3.14", "-2.5") -> float
    - JSON: если строка начинается с `{` или `[` -> попытка распарсить через json.loads
    - Даты в формате ISO: "2025-01-15" -> date, "2025-01-15T10:30:00" -> datetime
    - Иначе -> исходная строка (с удаленными пробелами)

    Аргументы:
        value (str): Строка для преобразования.

    Возвращает:
        (bool, int, float, str, list, dict, None, date, datetime): Значение соответствующего типа.
    """
    value = value.strip()
    if not value:
        return value

    low = value.lower()
    if low == 'true':
        return True
    if low == 'false':
        return False
    if low in ('null', 'none'):
        return None

    try:
        phonenumbers.parse(value, "RU")
        return value
    except phonenumbers.phonenumberutil.NumberParseException:
        pass

    if value.isdigit():
        return int(value)

    try:
        return float(value)
    except ValueError:
        pass

    if ((value.startswith('{') and value.endswith('}'))
        or (value.startswith('[') and value.endswith(']'))):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass

    if re.match(r'^\d{4}-\d{2}-\d{2}$', value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass

    if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$', value):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass

    return value
