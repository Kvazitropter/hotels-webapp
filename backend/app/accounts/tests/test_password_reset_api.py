from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

from app.accounts.models import Guest


User = get_user_model()


class PasswordResetRequestViewTest(APITestCase):
    def setUp(self):
        self.url = reverse('password-reset-request')
        self.user = User.objects.create_user(
            email='guest@example.com',
            first_name='Guest',
            last_name='Test',
            phone_number='+79111111111',
            password='GoodPassword432+'
        )
        Guest.objects.create(user=self.user)

    def test_valid_email_returns_200(self):
        response = self.client.post(self.url, {'email': self.user.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_nonexistent_email_still_returns_200(self):
        response = self.client.post(self.url, {'email': 'nobody@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_valid_email_sends_mail(self):
        self.client.post(self.url, {'email': self.user.email})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user.email, mail.outbox[0].recipients())

    def test_nonexistent_email_does_not_send_mail(self):
        self.client.post(self.url, {'email': 'nobody@example.com'})
        self.assertEqual(len(mail.outbox), 0)

    def test_inactive_user_does_not_receive_mail(self):
        self.user.is_active = False
        self.user.save()
        self.client.post(self.url, {'email': self.user.email})
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_link_contains_uid_and_token(self):
        self.client.post(self.url, {'email': self.user.email})
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn('uid=', body)
        self.assertIn('token=', body)

    def test_invalid_email_format_returns_400(self):
        response = self.client.post(self.url, {'email': 'not-an-email'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_email_returns_400(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmViewTests(APITestCase):
    def setUp(self):
        self.url = reverse('password-reset-confirm')
        self.user = User.objects.create_user(
            email='guest@example.com',
            first_name='Guest',
            last_name='Test',
            phone_number='+79111111111',
            password='OldPassword432+'
        )
        Guest.objects.create(user=self.user)
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = default_token_generator.make_token(self.user)
        self.new_password = 'NewPassword432+'
        self.valid_payload = {
            'uid': self.uid,
            'token': self.token,
            'new_password': self.new_password,
            'new_password_confirm': self.new_password,
        }

    def test_valid_payload_returns_200(self):
        response = self.client.post(self.url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_password_is_changed(self):
        self.client.post(self.url, self.valid_payload)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))

    def test_old_password_no_longer_works(self):
        self.client.post(self.url, self.valid_payload)
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password('OldPassword432+'))

    def test_token_cannot_be_reused(self):
        self.client.post(self.url, self.valid_payload)
        response = self.client.post(self.url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_token_returns_400(self):
        payload = {**self.valid_payload, 'token': 'invalid-token'}
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_uid_returns_400(self):
        payload = {**self.valid_payload, 'uid': 'invalid-uid'}
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_uid_returns_400(self):
        uid = urlsafe_base64_encode(force_bytes(99999))
        payload = {**self.valid_payload, 'uid': uid}
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_passwords_mismatch_returns_400(self):
        payload = {**self.valid_payload, 'new_password_confirm': 'DifferentPassword432+'}
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password(self.new_password))

    def test_weak_password_returns_400(self):
        payload = {**self.valid_payload, 'new_password': '123', 'new_password_confirm': '123'}
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password('123'))

    def test_missing_fields_returns_400(self):
        for field in ('uid', 'token', 'new_password', 'new_password_confirm'):
            with self.subTest(missing=field):
                payload = {k: v for k, v in self.valid_payload.items() if k != field}
                response = self.client.post(self.url, payload)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
