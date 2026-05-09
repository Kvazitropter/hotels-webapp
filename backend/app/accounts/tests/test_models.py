from django.db import IntegrityError
from django.test import TestCase
from django.contrib.auth import get_user_model

from app.accounts.models import Guest, Moderator, Administrator


User = get_user_model()


class UserModelTests(TestCase):
    def setUp(self):
        self.user_data = {
            'email': 'user@example.com',
            'first_name': 'User',
            'middle_name': 'Testovich',
            'last_name': 'Example',
            'phone_number': '+79000000000',
            'password': 'GoodPassword432+'
        }

    def test_create_user_success(self):
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.email, self.user_data['email'])
        self.assertEqual(user.first_name, self.user_data['first_name'])
        self.assertEqual(user.middle_name, self.user_data['middle_name'])
        self.assertEqual(user.last_name, self.user_data['last_name'])
        self.assertEqual(user.phone_number, self.user_data['phone_number'])
        self.assertTrue(user.check_password(self.user_data['password']))
        self.assertEqual(user.role, User.Role.NO_ROLE)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_guest)
        self.assertFalse(user.is_moderator)
        self.assertFalse(user.is_admin)

    def test_create_user_without_email_raises_error(self):
        with self.assertRaises(TypeError):
            User.objects.create_user(**self.user_data, email=None)

    def test_create_user_without_phone_number_raises_error(self):
        with self.assertRaises(TypeError):
            User.objects.create_user(**self.user_data, phone_number=None)

    def test_create_user_without_last_name_raises_error(self):
        with self.assertRaises(TypeError):
            User.objects.create_user(**self.user_data, last_name=None)

    def test_email_unique_constraint(self):
        user = User.objects.create_user(**self.user_data)
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email=user.email,
                first_name='User',
                last_name='Other',
                phone_number='+79222222222',
                password='GoodPassword432+'
            )

    def test_phone_number_unique_constraint(self):
        user = User.objects.create_user(**self.user_data)
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email='unique@example.com',
                first_name='User',
                last_name='Other',
                phone_number=user.phone_number,
                password='GoodPassword432+'
            )

    def test_full_name(self):
        user = User.objects.create_user(**self.user_data)
        expected_full_name1 = f'{user.last_name} {user.first_name} {user.middle_name}'
        self.assertEqual(user.full_name, expected_full_name1)

        user.middle_name = None
        user.save(update_fields=['middle_name'])
        expected_full_name2 = f'{user.last_name} {user.first_name}'
        self.assertEqual(user.full_name, expected_full_name2)

        self.assertEqual(user.get_full_name(), user.full_name)

    def test_short_name(self):
        user = User.objects.create_user(**self.user_data)
        expected_short_name1 = f'{user.last_name} {user.first_name[0]}.{user.middle_name[0]}.'
        self.assertEqual(user.short_name, expected_short_name1)

        user.middle_name = None
        user.save(update_fields=['middle_name'])
        expected_short_name2 = f'{user.last_name} {user.first_name[0]}.'
        self.assertEqual(user.short_name, expected_short_name2)

        self.assertEqual(user.get_short_name(), user.short_name)

    def test_assign_guest_role(self):
        user = User.objects.create_user(**self.user_data)
        user.assign_role(User.Role.GUEST)
        user.refresh_from_db()
        self.assertTrue(user.is_guest)
        self.assertEqual(user.role, User.Role.GUEST)
        self.assertTrue(Guest.objects.filter(user=user).exists())

    def test_assign_moderator_role(self):
        user = User.objects.create_user(**self.user_data)
        user.assign_role(User.Role.MODERATOR)
        user.refresh_from_db()
        self.assertTrue(user.is_moderator)
        self.assertEqual(user.role, User.Role.MODERATOR)
        self.assertTrue(Moderator.objects.filter(user=user).exists())

    def test_assign_admin_role(self):
        user = User.objects.create_user(**self.user_data)
        user.assign_role(User.Role.ADMIN)
        user.refresh_from_db()
        self.assertTrue(user.is_admin)
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertTrue(Administrator.objects.filter(user=user).exists())

    def test_assign_role_twice_raises_value_error(self):
        user = User.objects.create_user(**self.user_data)
        user.assign_role(User.Role.GUEST)
        with self.assertRaises(ValueError):
            user.assign_role(User.Role.GUEST)

    def test_assign_invalid_role_raises_value_error(self):
        user = User.objects.create_user(**self.user_data)
        with self.assertRaises(ValueError):
            user.assign_role('invalid')

    def test_assign_multiple_roles_possible(self):
        user = User.objects.create_user(**self.user_data)
        user.assign_role(User.Role.GUEST)
        user.assign_role(User.Role.MODERATOR)
        user.refresh_from_db()
        self.assertTrue(user.is_guest)
        self.assertTrue(user.is_moderator)
        self.assertEqual(user.role, User.Role.MODERATOR)
        user.assign_role(User.Role.ADMIN)
        user.refresh_from_db()
        self.assertTrue(user.is_admin)
        self.assertEqual(user.role, User.Role.ADMIN)

    def test_remove_guest_role(self):
        user = User.objects.create_user(**self.user_data)
        user.assign_role(User.Role.GUEST)
        user.remove_role(User.Role.GUEST)
        user.refresh_from_db()
        self.assertFalse(user.is_guest)
        self.assertEqual(user.role, User.Role.NO_ROLE)
        self.assertFalse(Guest.objects.filter(user=user).exists())

    def test_remove_moderator_role(self):
        user = User.objects.create_user(**self.user_data)
        user.assign_role(User.Role.MODERATOR)
        user.remove_role(User.Role.MODERATOR)
        user.refresh_from_db()
        self.assertFalse(user.is_moderator)
        self.assertEqual(user.role, User.Role.NO_ROLE)

    def test_remove_admin_role(self):
        user = User.objects.create_user(**self.user_data)
        user.assign_role(User.Role.ADMIN)
        user.remove_role(User.Role.ADMIN)
        user.refresh_from_db()
        self.assertFalse(user.is_admin)
        self.assertEqual(user.role, User.Role.NO_ROLE)

    def test_remove_nonexistent_role_raises_value_error(self):
        user = User.objects.create_user(**self.user_data)
        with self.assertRaises(ValueError):
            user.remove_role(User.Role.GUEST)

    def test_remove_invalid_role_raises_value_error(self):
        user = User.objects.create_user(**self.user_data)
        with self.assertRaises(ValueError):
            user.remove_role('invalid')

    def test_deleting_user_deletes_guest_record(self):
        user = User.objects.create_user(**self.user_data)
        user.assign_role(User.Role.GUEST)
        guest_pk = user.guest.pk
        user.delete()
        self.assertFalse(Guest.objects.filter(pk=guest_pk).exists())

    def test_deleting_user_deletes_moderator_record(self):
        user = User.objects.create_user(**self.user_data)
        user.assign_role(User.Role.MODERATOR)
        mod_pk = user.moderator.pk
        user.delete()
        self.assertFalse(Moderator.objects.filter(pk=mod_pk).exists())

    def test_deleting_user_deletes_admin_record(self):
        user = User.objects.create_user(**self.user_data)
        user.assign_role(User.Role.ADMIN)
        admin_pk = user.admin.pk
        user.delete()
        self.assertFalse(Administrator.objects.filter(pk=admin_pk).exists())

    def test_setters_raise_value_error(self):
        user = User.objects.create_user(**self.user_data)
        with self.assertRaises(ValueError):
            user.is_admin = True

        with self.assertRaises(ValueError):
            user.is_moderator = True

        with self.assertRaises(ValueError):
            user.is_guest = True

        with self.assertRaises(ValueError):
            user.is_superuser = True

        with self.assertRaises(ValueError):
            user.is_staff = True
