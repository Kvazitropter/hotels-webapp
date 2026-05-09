from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status


User = get_user_model()


class GuestViewSetTest(APITestCase):
    def setUp(self):
        self.base_url = reverse('guest-list')
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
        self.guest1 = User.objects.create_user(
            email='guest1@example.com',
            first_name='Guest',
            last_name='One',
            phone_number='+79333333333',
            password='GoodPassword432+'
        )
        self.guest2 = User.objects.create_user(
            email='guest2@example.com',
            first_name='Guest',
            last_name='Two',
            phone_number='+79444444444',
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
        self.moderator.assign_role(role=User.Role.MODERATOR)
        self.guest1.assign_role(role=User.Role.GUEST)
        self.guest2.assign_role(role=User.Role.GUEST)

    def _get_detail_url(self, guest_id):
        return reverse('guest-detail', kwargs={'pk': guest_id})

    def test_unauthenticated_cannot_access(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_can_list_guests(self):
        users = [self.admin, self.moderator]
        for user in users:
            with self.subTest(user=user.role):
                self.client.force_authenticate(user)
                response = self.client.get(self.base_url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 2)

    def test_non_staff_cannot_list_guests(self):
        users = [self.guest1, self.no_role_user]
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

    def test_ordering_by_email(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.base_url, {'ordering': '-email'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = [g['email'] for g in response.data]
        self.assertEqual(emails, sorted(emails, reverse=True))

    def test_filter_guests_by_is_active(self):
        self.guest1.is_active = False
        self.guest1.save()
        self.client.force_authenticate(self.admin)

        response1 = self.client.get(self.base_url, {'is_active': 'True'})
        self.assertEqual(len(response1.data), 1)
        self.assertEqual(response1.data[0]['email'], self.guest2.email)

        response2 = self.client.get(self.base_url, {'is_active': 'False'})
        self.assertEqual(len(response2.data), 1)
        self.assertEqual(response2.data[0]['email'], self.guest1.email)

    def test_staff_can_retrieve_guest(self):
        users = [self.admin, self.moderator]
        url = self._get_detail_url(self.guest1.pk)
        for user in users:
            with self.subTest(user=user.role):
                self.client.force_authenticate(user)
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data['email'], self.guest1.email)

    def test_non_staff_cannot_retrieve_guest(self):
        users = [self.guest2, self.no_role_user]
        url = self._get_detail_url(self.guest1.pk)
        for user in users:
            with self.subTest(user=user.role):
                self.client.force_authenticate(user)
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_nonexistent_guest_returns_404(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self._get_detail_url(9999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
