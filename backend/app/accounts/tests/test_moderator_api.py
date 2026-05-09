from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status


User = get_user_model()


class ModeratorViewSetTest(APITestCase):
    def setUp(self):
        self.base_url = reverse('moderator-list')
        self.admin = User.objects.create_user(
            email='admin@example.com',
            first_name='Admin',
            last_name='Admin',
            phone_number='+79000000000',
            password='GoodPassword432+'
        )
        self.moderator1 = User.objects.create_user(
            email='moderator1@example.com',
            first_name='Moderator',
            last_name='One',
            phone_number='+79111111111',
            password='GoodPassword432+'
        )
        self.moderator2 = User.objects.create_user(
            email='moderator2@example.com',
            first_name='Moderator',
            last_name='Two',
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
            phone_number='+79555555555',
            password='GoodPassword432+'
        )

        self.admin.assign_role(role=User.Role.ADMIN)
        self.moderator1.assign_role(role=User.Role.MODERATOR)
        self.moderator2.assign_role(role=User.Role.MODERATOR)
        self.guest.assign_role(role=User.Role.GUEST)

    def _get_detail_url(self, mod_id):
        return reverse('moderator-detail', kwargs={'pk': mod_id})

    def test_unauthenticated_list_returns_401(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_detail_returns_401(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_guest_cannot_access(self):
        self.client.force_authenticate(self.guest)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_can_list_moderators(self):
        self.client.force_authenticate(self.moderator1)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        emails = [user['email'] for user in response.data]
        self.assertIn(self.moderator1.email, emails)
        self.assertIn(self.moderator2.email, emails)

    def test_admin_can_list_moderators(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        emails = [user['email'] for user in response.data]
        self.assertIn(self.moderator1.email, emails)
        self.assertIn(self.moderator2.email, emails)

    def test_other_users_cannot_list_moderators(self):
        users = [self.guest, self.no_role_user]
        for user in users:
            with self.subTest(user=user.role):
                self.client.force_authenticate(user)
                response = self.client.get(self.base_url)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_search_by_last_name(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.base_url, {'search': 'One'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['last_name'], 'One')

    def test_search_by_email(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.base_url, {'search': 'moderator1'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['email'], self.moderator1.email)

    def test_search_by_phone_number(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.base_url, {'search': '79111111111'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['phone_number'], self.moderator1.phone_number)

    def test_ordering_by_email(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.base_url, {'ordering': '-email'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = [user['email'] for user in response.data]
        self.assertEqual(emails, sorted(emails, reverse=True))

    def test_filter_by_is_active(self):
        self.moderator1.is_active = False
        self.moderator1.save()
        self.client.force_authenticate(self.admin)

        response_active = self.client.get(self.base_url, {'is_active': 'True'})
        self.assertEqual(len(response_active.data), 1)
        self.assertEqual(response_active.data[0]['email'], self.moderator2.email)

        response_inactive = self.client.get(self.base_url, {'is_active': 'False'})
        self.assertEqual(len(response_inactive.data), 1)
        self.assertEqual(response_inactive.data[0]['email'], self.moderator1.email)

    def test_moderator_can_retrieve_moderator(self):
        self.client.force_authenticate(self.moderator1)
        response = self.client.get(self._get_detail_url(self.moderator2.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.moderator2.email)

    def test_admin_can_retrieve_moderator(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self._get_detail_url(self.moderator2.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.moderator2.email)

    def test_other_users_cannot_retrieve_moderators(self):
        users = [self.guest, self.no_role_user]
        url = self._get_detail_url(self.moderator2.pk)
        for user in users:
            with self.subTest(user=user.role):
                self.client.force_authenticate(user)
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_nonexistent_moderator_returns_404(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self._get_detail_url(9999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
