from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

User = get_user_model()


class MeViewTest(APITestCase):
    def setUp(self):
        self.base_url = reverse('me')
        self.request_change_url = reverse('me-contact-request')
        self.confirm_change_url = reverse('me-contact-confirm')
        self.admin = User.objects.create_user(
            email='admin@example.com',
            first_name='Admin',
            last_name='Admin',
            phone_number='+79000000000',
            password='GoodPassword432+'
        )
        self.moderator = User.objects.create_user(
            email='moderator@example.com',
            first_name='Moderator',
            last_name='Test',
            phone_number='+79222222222',
            password='GoodPassword432+'
        )
        self.guest = User.objects.create_user(
            email='guest@example.com',
            first_name='Guest',
            last_name='Test',
            phone_number='+79333333333',
            password='GoodPassword432+'
        )
        self.no_role_user = User.objects.create_user(
            email='user@example.com',
            first_name='User',
            last_name='NoRole',
            phone_number='+79444444444',
            password='GoodPassword432+'
        )

        self.admin.assign_role(role=User.Role.ADMIN)
        self.moderator.assign_role(role=User.Role.MODERATOR)
        self.guest.assign_role(role=User.Role.GUEST)

    def _set_pending(self, user, change_type, new_value):
        cache.set(f'contact_change:{user.pk}', {
            'change_type': change_type,
            'new_value': new_value,
        }, timeout=600)

    def _make_confirm_payload(self, user):
        return {
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': default_token_generator.make_token(user),
        }

    def test_unauthenticated_cannot_retrieve_self(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_cannot_update_self(self):
        response = self.client.patch(self.base_url, {'first_name': 'NewName'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_cannot_delete_self(self):
        response = self.client.delete(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_cannot_request_change(self):
        response = self.client.patch(self.request_change_url, {'email': 'new@email.com'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_any_authenticated_user_can_retrieve_self(self):
        users = [self.admin, self.moderator, self.guest, self.no_role_user]
        for user in users:
            with self.subTest(user=user.email):
                self.client.force_authenticate(user)
                response = self.client.get(self.base_url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data['email'], user.email)
                self.assertEqual(response.data['first_name'], user.first_name)
                self.assertEqual(response.data['last_name'], user.last_name)
                self.assertEqual(response.data['phone_number'], user.phone_number)
                self.assertEqual(response.data['role'], user.role)

    def test_guest_can_update_not_sensitive_data(self):
        self.client.force_authenticate(self.guest)
        new_data = {
            'last_name': 'NewLastName',
            'first_name': 'NewName',
            'middle_name': 'NewMiddleName',
            'date_of_birth': '2000-01-01',
        }
        response = self.client.patch(self.base_url, new_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.guest.refresh_from_db()
        self.assertEqual(self.guest.first_name, new_data['first_name'])
        self.assertEqual(self.guest.last_name, new_data['last_name'])
        self.assertEqual(self.guest.middle_name, new_data['middle_name'])
        self.assertEqual(self.guest.date_of_birth.strftime("%Y-%m-%d"), new_data['date_of_birth'])

    def test_invalid_date_of_birth_returns_400(self):
        self.client.force_authenticate(self.guest)
        response = self.client.patch(self.base_url, {'date_of_birth': 'not-a-date'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_guest_cannot_update_email_directly(self):
        self.client.force_authenticate(self.guest)
        new_email = 'new@email.com'
        self.client.patch(self.base_url, {'email': new_email})
        self.guest.refresh_from_db()
        self.assertNotEqual(self.guest.email, new_email)

    def test_guest_cannot_update_phone_directly(self):
        self.client.force_authenticate(self.guest)
        new_phone = '+79123456789'
        self.client.patch(self.base_url, {'phone_number': new_phone})
        self.guest.refresh_from_db()
        self.assertNotEqual(str(self.guest.phone_number), new_phone)

    def test_non_guest_cannot_update_profile(self):
        non_guests = [self.admin, self.moderator, self.no_role_user]
        new_name = 'NewName'
        for user in non_guests:
            with self.subTest(user=user.email):
                self.client.force_authenticate(user)
                response = self.client.patch(self.base_url, {'first_name': new_name})
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
                user.refresh_from_db()
                self.assertNotEqual(user.first_name, new_name)

    def test_guest_can_delete_own_account(self):
        self.client.force_authenticate(self.guest)
        response = self.client.delete(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.guest.refresh_from_db()
        self.assertFalse(self.guest.is_active)

    # def test_delete_blacklists_tokens_and_invalidates_password(self):
    #     password = 'GoodPassword432+'
    #     refresh = RefreshToken.for_user(self.guest)
    #     self.client.force_authenticate(self.guest)
    #     self.client.delete(self.base_url)
    #     self.assertTrue(
    #         BlacklistedToken.objects.filter(token__jti=refresh['jti']).exists()
    #     )
    #     self.assertFalse(self.guest.check_password(password))

    def test_deleted_guest_cannot_auth(self):
        auth_data = {
            'email': 'guest@example.com',
            'password': 'GoodPassword432+'
        }
        self.client.force_authenticate(self.guest)
        self.client.delete(self.base_url)
        self.client.force_authenticate(None)
        response = self.client.post(reverse('login'), auth_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_deleted_guest_cannot_access_api(self):
        refresh = RefreshToken.for_user(self.guest)
        access = str(refresh.access_token)
        self.client.force_authenticate(self.guest)
        self.client.delete(self.base_url)
        self.client.force_authenticate(None)
        response = self.client.get(self.base_url, HTTP_AUTHORIZATION=f'Bearer {access}')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_guest_cannot_deactivate_own_account(self):
        non_guests = [self.admin, self.moderator, self.no_role_user]
        for user in non_guests:
            with self.subTest(user=user.email):
                self.client.force_authenticate(user)
                response = self.client.delete(self.base_url)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
                user.refresh_from_db()
                self.assertTrue(user.is_active)

    def test_guest_can_request_email_change(self):
        self.client.force_authenticate(self.guest)
        new_email = 'new@email.com'
        response = self.client.patch(self.request_change_url, {'email': new_email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [new_email])
        self.assertEqual(email.subject, 'Подтверждение смены email')
        self.assertIn('Для подтверждения перейдите по ссылке:', email.body)
        self.assertIn('/me/confirm-change?uid=', email.body)

    def test_guest_can_request_phone_number_change(self):
        self.client.force_authenticate(self.guest)
        new_phone = '+79123456789'
        response = self.client.patch(self.request_change_url, {'phone_number': new_phone})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.guest.email])
        self.assertEqual(email.subject, 'Подтверждение смены номера телефона')
        self.assertIn('Для подтверждения перейдите по ссылке:', email.body)
        self.assertIn('/me/confirm-change?uid=', email.body)

    def test_request_change_saves_to_cache(self):
        self.client.force_authenticate(self.guest)
        new_email = 'new@email.com'
        self.client.patch(self.request_change_url, {'email': new_email})
        pending = cache.get(f'contact_change:{self.guest.pk}')
        self.assertIsNotNone(pending)
        self.assertEqual(pending['change_type'], 'email')
        self.assertEqual(pending['new_value'], new_email)

    def test_new_request_change_overwrites_previous(self):
        self.client.force_authenticate(self.guest)
        self.client.patch(self.request_change_url, {'email': 'first@example.com'})
        self.client.patch(self.request_change_url, {'email': 'second@example.com'})
        pending = cache.get(f'contact_change:{self.guest.pk}')
        self.assertEqual(pending['new_value'], 'second@example.com')
        self.assertEqual(len(mail.outbox), 2)

    def test_request_change_with_existing_email_returns_400(self):
        self.client.force_authenticate(self.guest)
        response = self.client.patch(self.request_change_url, {'email': self.moderator.email})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)

    def test_request_change_with_existing_phone_returns_400(self):
        self.client.force_authenticate(self.guest)
        response = self.client.patch(
            self.request_change_url, {'phone_number': str(self.admin.phone_number)}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)

    def test_request_change_with_both_fields_returns_400(self):
        self.client.force_authenticate(self.guest)
        response = self.client.patch(self.request_change_url, {
            'email': 'new@email.com',
            'phone_number': '+79123456789',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)

    def test_request_change_with_empty_body_returns_400(self):
        self.client.force_authenticate(self.guest)
        response = self.client.patch(self.request_change_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)

    def test_request_change_with_invalid_email_returns_400(self):
        self.client.force_authenticate(self.guest)
        response = self.client.patch(self.request_change_url, {'email': 'not-an-email'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)

    def test_request_change_with_invalid_phone_returns_400(self):
        self.client.force_authenticate(self.guest)
        response = self.client.patch(self.request_change_url, {'phone_number': '123'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)

    def test_non_guest_cannot_request_change_email_or_phone(self):
        users = [self.admin, self.moderator, self.no_role_user]
        for user in users:
            with self.subTest(user=user.email):
                self.client.force_authenticate(user)
                response = self.client.patch(self.request_change_url, {'email': 'new@email.com'})
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_confirm_email_change(self):
        new_email = 'new@example.com'
        self._set_pending(self.guest, 'email', new_email)
        payload = self._make_confirm_payload(self.guest)
        self.client.force_authenticate(self.guest)
        response = self.client.patch(self.confirm_change_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.guest.refresh_from_db()
        self.assertEqual(self.guest.email, new_email)

    def test_confirm_phone_change(self):
        new_phone = '+79123456789'
        self._set_pending(self.guest, 'phone', new_phone)
        payload = self._make_confirm_payload(self.guest)
        self.client.force_authenticate(self.guest)
        response = self.client.patch(self.confirm_change_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.guest.refresh_from_db()
        self.assertEqual(str(self.guest.phone_number), new_phone)

    def test_confirm_change_clears_cache(self):
        self._set_pending(self.guest, 'email', 'new@example.com')
        payload = self._make_confirm_payload(self.guest)
        self.client.force_authenticate(self.guest)
        self.client.patch(self.confirm_change_url, payload)
        self.assertIsNone(cache.get(f'contact_change:{self.guest.pk}'))

    def test_confirm_change_without_pending_returns_400(self):
        payload = self._make_confirm_payload(self.guest)
        self.client.force_authenticate(self.guest)
        response = self.client.patch(self.confirm_change_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_change_with_invalid_token_returns_400(self):
        new_email = 'new@example.com'
        self._set_pending(self.guest, 'email', new_email)
        payload = self._make_confirm_payload(self.guest)
        payload['token'] = 'invalid-token'
        self.client.force_authenticate(self.guest)
        response = self.client.patch(self.confirm_change_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.guest.refresh_from_db()
        self.assertNotEqual(self.guest.email, new_email)

    def test_confirm_change_with_invalid_uid_returns_400(self):
        self._set_pending(self.guest, 'email', 'new@example.com')
        payload = self._make_confirm_payload(self.guest)
        payload['uid'] = 'invalid-uid'
        self.client.force_authenticate(self.guest)
        response = self.client.patch(self.confirm_change_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_change_token_cannot_be_reused(self):
        self._set_pending(self.guest, 'email', 'new@example.com')
        payload = self._make_confirm_payload(self.guest)
        self.client.force_authenticate(self.guest)
        self.client.patch(self.confirm_change_url, payload)

        another_email = 'another@example.com'
        self._set_pending(self.guest, 'email', another_email)
        response = self.client.patch(self.confirm_change_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.guest.refresh_from_db()
        self.assertNotEqual(self.guest.email, another_email)
