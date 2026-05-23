from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def create_confirm_link(url_name: str, user) -> str:
    '''Генерирует ссылку подтверждения действия'''
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    relative_url = reverse(url_name)
    full_url = f'{settings.FRONTEND_URL}{relative_url}?uid={uid}&token={token}'
    return full_url
