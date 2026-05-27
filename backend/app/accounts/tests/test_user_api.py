from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from app.accounts.models import Administrator, Guest, Moderator


User = get_user_model()


class UserViewSetTest(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@example.com',
            first_name='Admin',
            last_name='Test',
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

        Administrator.objects.create(user=self.admin)
        Moderator.objects.create(user=self.moderator)
        Guest.objects.create(user=self.guest)

    def _get_assign_url(self, user_pk):
        return reverse('user-assign-role', kwargs={'pk': user_pk})

    def _get_remove_url(self, user_pk):
        return reverse('user-remove-role', kwargs={'pk': user_pk})

    def _get_deactivate_url(self, user_pk):
        return reverse('user-deactivate', kwargs={'pk': user_pk})

    def _get_activate_url(self, user_pk):
        return reverse('user-activate', kwargs={'pk': user_pk})

    def test_unauthenticated_cannot_assign_role(self):
        url = self._get_assign_url(self.no_role_user.pk)
        response = self.client.post(url, {'role': User.Role.GUEST})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_cannot_remove_role(self):
        url = self._get_remove_url(self.guest.pk)
        response = self.client.delete(url, {'role': User.Role.GUEST})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_cannot_deactivate(self):
        url = self._get_deactivate_url(self.guest.pk)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_cannot_activate(self):
        self.guest.is_active = False
        self.guest.save(update_fields=['is_active'])
        url = self._get_activate_url(self.guest.pk)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_assign_role(self):
        assign_to = self.no_role_user
        roles = [User.Role.GUEST, User.Role.MODERATOR, User.Role.ADMIN]
        self.client.force_authenticate(self.admin)

        for role in roles:
            with self.subTest(assign_to=assign_to.email, role=role):
                if assign_to.role != User.Role.NO_ROLE:
                    assign_to.remove_role(assign_to.role)

                url = self._get_assign_url(assign_to.pk)
                response = self.client.post(url, {'role': role})
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                assign_to.refresh_from_db()
                self.assertEqual(assign_to.role, role)

    def test_non_admin_cannot_assign_role(self):
        non_admins = [self.no_role_user, self.guest, self.moderator]
        target = self.no_role_user

        for current_user in non_admins:
            with self.subTest(current=current_user.email, target=target.email):
                self.client.force_authenticate(current_user)
                url = self._get_assign_url(target.pk)
                role_before = target.role

                response = self.client.post(url, {'role': User.Role.GUEST})
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
                target.refresh_from_db()
                self.assertEqual(target.role, role_before)

    def test_assign_role_user_already_has_role_returns_400(self):
        self.client.force_authenticate(self.admin)
        url = self._get_assign_url(self.guest.pk)
        response = self.client.post(url, {'role': User.Role.GUEST})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_assign_user_with_role_other_role(self):
        self.client.force_authenticate(self.admin)
        url = self._get_assign_url(self.guest.pk)
        response = self.client.post(url, {'role': User.Role.ADMIN})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.guest.refresh_from_db()
        self.assertEqual(self.guest.role, User.Role.ADMIN)
        self.assertTrue(self.guest.is_guest)

    def test_assign_invalid_role_returns_400(self):
        self.client.force_authenticate(self.admin)
        url = self._get_assign_url(self.no_role_user.pk)
        response = self.client.post(url, {'role': 'invalid_role'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_assign_role_missing_role_in_body_returns_400(self):
        self.client.force_authenticate(self.admin)
        url = self._get_assign_url(self.no_role_user.pk)
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_assign_role_to_nonexistent_user_returns_404(self):
        self.client.force_authenticate(self.admin)
        url = self._get_assign_url(99999)
        response = self.client.post(url, {'role': User.Role.GUEST})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_remove_role(self):
        targets = [self.guest, self.moderator, self.admin]
        self.client.force_authenticate(self.admin)

        for target in targets:
            with self.subTest(target=target.email):
                url = self._get_remove_url(target.pk)
                response = self.client.delete(url, {'role': target.role})
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
                target.refresh_from_db()
                self.assertEqual(target.role, User.Role.NO_ROLE)

    def test_non_admin_cannot_remove_role(self):
        non_admins = [self.no_role_user, self.guest, self.moderator]
        targets = [self.guest, self.moderator, self.admin]

        for current_user in non_admins:
            for target in targets:
                with self.subTest(current=current_user.email, target=target.email):
                    self.client.force_authenticate(current_user)
                    url = self._get_remove_url(target.pk)
                    role_before = target.role

                    response = self.client.delete(url, {'role': target.role})
                    self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
                    target.refresh_from_db()
                    self.assertEqual(target.role, role_before)

    def test_remove_role_user_does_not_have_returns_400(self):
        self.client.force_authenticate(self.admin)
        url = self._get_remove_url(self.no_role_user.pk)
        response = self.client.delete(url, {'role': User.Role.GUEST})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_remove_invalid_role_returns_400(self):
        self.client.force_authenticate(self.admin)
        url = self._get_remove_url(self.guest.pk)
        response = self.client.delete(url, {'role': 'invalid_role'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_remove_role_missing_role_in_body_returns_400(self):
        self.client.force_authenticate(self.admin)
        url = self._get_remove_url(self.guest.pk)
        response = self.client.delete(url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_remove_role_from_nonexistent_user_returns_404(self):
        self.client.force_authenticate(self.admin)
        url = self._get_remove_url(99999)
        response = self.client.delete(url, {'role': User.Role.GUEST})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_deactivate_user(self):
        self.client.force_authenticate(self.admin)
        targets = [self.no_role_user, self.guest, self.moderator, self.admin]
        for target in targets:
            with self.subTest(target=target.email):
                url = self._get_deactivate_url(target.pk)
                response = self.client.post(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                target.refresh_from_db()
                self.assertFalse(target.is_active)

    def test_non_admin_cannot_deactivate_user(self):
        non_admins = [self.no_role_user, self.guest, self.moderator]
        targets = [self.no_role_user, self.guest, self.moderator, self.admin]

        for current_user in non_admins:
            for target in targets:
                with self.subTest(current=current_user.email, target=target.email):
                    self.client.force_authenticate(current_user)
                    url = self._get_deactivate_url(target.pk)
                    response = self.client.post(url)
                    self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
                    target.refresh_from_db()
                    self.assertTrue(target.is_active)

    def test_deactivate_already_inactive_user(self):
        self.guest.is_active = False
        self.guest.save()
        self.client.force_authenticate(self.admin)
        url = self._get_deactivate_url(self.guest.pk)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.guest.refresh_from_db()
        self.assertFalse(self.guest.is_active)

    def test_deactivate_nonexistent_user_returns_404(self):
        self.client.force_authenticate(self.admin)
        url = self._get_deactivate_url(99999)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_activate_user(self):
        self.client.force_authenticate(self.admin)
        targets = [self.no_role_user, self.guest, self.moderator, self.admin]
        for target in targets:
            target.is_active = False
            target.save(update_fields=['is_active'])
            target.refresh_from_db()
            with self.subTest(target=target.email):
                url = self._get_activate_url(target.pk)
                response = self.client.post(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                target.refresh_from_db()
                self.assertTrue(target.is_active)

    def test_non_admin_cannot_activate_user(self):
        non_admins = [self.no_role_user, self.guest, self.moderator]
        targets = [self.no_role_user, self.guest, self.moderator, self.admin]

        for current_user in non_admins:
            for target in targets:
                target.is_active = False
                target.save(update_fields=['is_active'])
                target.refresh_from_db()
                with self.subTest(current=current_user.email, target=target.email):
                    self.client.force_authenticate(current_user)
                    url = self._get_activate_url(target.pk)
                    response = self.client.post(url)
                    self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
                    target.refresh_from_db()
                    self.assertFalse(target.is_active)

    def test_activate_already_active_user(self):
        self.client.force_authenticate(self.admin)
        url = self._get_activate_url(self.guest.pk)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.guest.refresh_from_db()
        self.assertTrue(self.guest.is_active)

    def test_activate_nonexistent_user_returns_404(self):
        self.client.force_authenticate(self.admin)
        url = self._get_activate_url(99999)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
