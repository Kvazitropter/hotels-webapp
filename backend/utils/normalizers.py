import phonenumbers
from django.conf import settings


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_phone(phone_str: str) -> str:
    num = phonenumbers.parse(phone_str, settings.PHONENUMBER_DEFAULT_REGION)
    format_constant = getattr(phonenumbers.PhoneNumberFormat, settings.PHONENUMBER_DB_FORMAT)
    return phonenumbers.format_number(num, format_constant)
