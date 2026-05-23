import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status


User = get_user_model()


class RegistrationTest(APITestCase):
    def setUp(self):
        self.register_url = reverse('register')
        self.user_data = {
            'email': 'test@example.com',
            'first_name': 'User',
            'last_name': 'Test',
            'phone_number': '+79999999999',
            'password': 'GoodPassword432+',
            'password_confirm': 'GoodPassword432+'
        }

    def test_register_success(self):
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        self.assertEqual(user.email, self.user_data['email'])
        self.assertEqual(user.phone_number, self.user_data['phone_number'])
        self.assertEqual(user.last_name, self.user_data['last_name'])
        self.assertEqual(user.first_name, self.user_data['first_name'])
        self.assertEqual(user.role, User.Role.GUEST)

    def test_register_sends_confirm_link_to_email(self):
        self.client.post(self.register_url, self.user_data)
        user = User.objects.first()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(user.email, mail.outbox[0].recipients())
        body = mail.outbox[0].body
        self.assertIn('uid=', body)
        self.assertIn('token=', body)

    def test_register_password_mismatch(self):
        data = self.user_data.copy()
        data['password_confirm'] = 'wrong'
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password_confirm', response.data)

    def test_register_duplicate_email(self):
        self.client.post(self.register_url, self.user_data)
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_register_not_send_confirm_link_duplicate_email(self):
        self.client.post(self.register_url, self.user_data)
        mail.outbox.clear()
        self.client.post(self.register_url, self.user_data)
        self.assertEqual(len(mail.outbox), 0)

    def test_register_duplicate_phone(self):
        self.client.post(self.register_url, self.user_data)
        response = self.client.post(
            self.register_url,
            {**self.user_data, 'email': 'other@email.com'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone_number', response.data)


class ConfirmEmailTest(APITestCase):
    def setUp(self):
        self.register_url = reverse('register')
        self.confirm_url = reverse('register-email-confirm')
        self.user_data = {
            'email': 'test@example.com',
            'first_name': 'User',
            'last_name': 'Test',
            'phone_number': '+79999999999',
            'password': 'GoodPassword432+',
            'password_confirm': 'GoodPassword432+'
        }
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.user = User.objects.get(email=self.user_data['email'])
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        match = re.search(r'uid=([^&]+)&token=([^\s]+)', body)
        self.assertIsNotNone(match)
        self.uid, self.token = match.groups()

    def test_confirm_email_success(self):
        response = self.client.post(self.confirm_url, {'uid': self.uid, 'token': self.token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'Email успешно подтвержден')

    def test_confirm_email_invalid_uid(self):
        response = self.client.post(
            self.confirm_url,
            {'uid': 'invalid', 'token': self.token}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('uid', response.data)

    def test_confirm_email_invalid_token(self):
        response = self.client.post(
            self.confirm_url,
            {'uid': self.uid, 'token': 'invalid-token'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('token', response.data)
