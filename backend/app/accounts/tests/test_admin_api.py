from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status


User = get_user_model()


class AdminViewSetTest(APITestCase):
    def setUp(self):
        self.base_url = reverse('admin-list')

        self.admin1 = User.objects.create_user(
            email='admin1@example.com',
            first_name='Admin',
            last_name='One',
            phone_number='+79000000001',
            password='GoodPassword432+'
        )
        self.admin2 = User.objects.create_user(
            email='admin2@example.com',
            first_name='Admin',
            last_name='Two',
            phone_number='+79000000002',
            password='GoodPassword432+'
        )
        self.moderator = User.objects.create_user(
            email='moderator@example.com',
            first_name='Moderator',
            last_name='Test',
            phone_number='+79111111111',
            password='GoodPassword432+'
        )
        self.guest = User.objects.create_user(
            email='guest@example.com',
            first_name='Guest',
            last_name='Test',
            phone_number='+79222222222',
            password='GoodPassword432+'
        )
        self.no_role_user = User.objects.create_user(
            email='user@example.com',
            first_name='User',
            last_name='NoRole',
            phone_number='+79555555555',
            password='GoodPassword432+'
        )

        self.admin1.assign_role(role=User.Role.ADMIN)
        self.admin2.assign_role(role=User.Role.ADMIN)
        self.moderator.assign_role(role=User.Role.MODERATOR)
        self.guest.assign_role(role=User.Role.GUEST)

    def _get_detail_url(self, id):
        return reverse('admin-detail', kwargs={'pk': id})

    def test_unauthenticated_list_returns_401(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_detail_returns_401(self):
        response = self.client.get(self._get_detail_url(self.admin1.pk))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_list_admins(self):
        self.client.force_authenticate(self.admin1)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        emails = [user['email'] for user in response.data]
        self.assertIn(self.admin1.email, emails)
        self.assertIn(self.admin2.email, emails)

    def test_other_users_cannot_list_admins(self):
        users = [self.moderator, self.guest, self.no_role_user]
        for user in users:
            with self.subTest(user=user.role):
                self.client.force_authenticate(user)
                response = self.client.get(self.base_url)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_search_by_last_name(self):
        self.client.force_authenticate(self.admin1)
        response = self.client.get(self.base_url, {'search': 'Two'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['last_name'], 'Two')

    def test_search_by_email(self):
        self.client.force_authenticate(self.admin1)
        response = self.client.get(self.base_url, {'search': 'admin1@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['email'], self.admin1.email)

    def test_search_by_phone_number(self):
        self.client.force_authenticate(self.admin1)
        response = self.client.get(self.base_url, {'search': '79000000001'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['phone_number'], self.admin1.phone_number)

    def test_ordering_by_email(self):
        self.client.force_authenticate(self.admin1)
        response = self.client.get(self.base_url, {'ordering': '-email'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = [user['email'] for user in response.data]
        self.assertEqual(emails, sorted(emails, reverse=True))

    def test_filter_by_is_active(self):
        self.admin2.is_active = False
        self.admin2.save()
        self.client.force_authenticate(self.admin1)

        response_active = self.client.get(self.base_url, {'is_active': 'True'})
        self.assertEqual(len(response_active.data), 1)
        self.assertEqual(response_active.data[0]['email'], self.admin1.email)

        response_inactive = self.client.get(self.base_url, {'is_active': 'False'})
        self.assertEqual(len(response_inactive.data), 1)
        self.assertEqual(response_inactive.data[0]['email'], self.admin2.email)

    def test_admin_can_retrieve_admin(self):
        self.client.force_authenticate(self.admin1)
        response = self.client.get(self._get_detail_url(self.admin2.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.admin2.email)

    def test_other_users_cannot_retrieve_admin(self):
        users = [self.moderator, self.guest, self.no_role_user]
        url = self._get_detail_url(self.admin2.pk)
        for user in users:
            with self.subTest(user=user.role):
                self.client.force_authenticate(user)
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_nonexistent_admin_returns_404(self):
        self.client.force_authenticate(self.admin1)
        response = self.client.get(self._get_detail_url(9999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
