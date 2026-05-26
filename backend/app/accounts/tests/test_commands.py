from datetime import datetime
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth import get_user_model

from app.accounts.models import Guest, Moderator, Administrator
from utils.validators import validate_email, validate_phone


User = get_user_model()


class CreateTestUsersCommandTest(TestCase):
    def setUp(self):
        self.out = StringIO()

    def _call_command(self, *args, **kwargs):
        call_command('create_test_users', stdout=self.out, stderr=StringIO(), *args, **kwargs)

    def test_creates_guests_by_default(self):
        self._call_command()
        self.assertEqual(User.objects.count(), 5)
        self.assertEqual(Guest.objects.count(), 5)

    def test_creates_guests_with_role_flag(self):
        self._call_command('--users', '3', '--role', 'guest')
        self.assertEqual(User.objects.count(), 3)
        self.assertEqual(Guest.objects.count(), 3)
        self.assertEqual(Moderator.objects.count(), 0)
        self.assertEqual(Administrator.objects.count(), 0)

    def test_creates_moderators_with_role_flag(self):
        self._call_command('--users', '2', '--role', 'moderator')
        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(Moderator.objects.count(), 2)
        self.assertEqual(Guest.objects.count(), 0)
        self.assertEqual(Administrator.objects.count(), 0)

    def test_creates_admins_with_role_flag(self):
        self._call_command('--users', '1', '--role', 'admin')
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Administrator.objects.count(), 1)
        self.assertEqual(Guest.objects.count(), 0)
        self.assertEqual(Moderator.objects.count(), 0)

    def test_generated_data_is_valid(self):
        self._call_command('--users', '1')
        user = User.objects.first()
        self.assertTrue(validate_email(user.email))
        self.assertTrue(validate_phone(str(user.phone_number)))
        self.assertIsNotNone(user.first_name)
        self.assertIsNotNone(user.last_name)
        self.assertIsNotNone(user.date_of_birth)
        today = datetime.today()
        age = today.year - user.date_of_birth.year - (
            (today.month, today.day) < (user.date_of_birth.month, user.date_of_birth.day)
        )
        self.assertGreaterEqual(age, 18)

    def test_prints_created_users(self):
        self._call_command('--users', '1')
        output = self.out.getvalue()
        self.assertIn('Создан пользователь:', output)
        user = User.objects.first()
        self.assertIn(user.email, output)
        self.assertIn(str(user.phone_number), output)
        self.assertIn(user.last_name, output)
        self.assertIn(user.first_name, output)
        self.assertIn(User.Role.GUEST, output)

    @patch('app.accounts.management.commands.create_test_users.fake.email')
    def test_skips_existing_email(self, mock_fake_email):
        mock_fake_email.side_effect = [
            'test@example.com', 'other1@example.com', 'other2@example.com'
        ]
        User.objects.create_user(
            email='test@example.com',
            phone_number='+79123456789',
            last_name='Test',
            first_name='User',
            password='pass'
        )
        self._call_command('--users', '2')
        emails = User.objects.exclude(email='test@example.com') \
            .values_list('email', flat=True)
        self.assertEqual(emails.count(), 2)
        self.assertIn('other1@example.com', emails)
        self.assertIn('other2@example.com', emails)

    @patch('app.accounts.management.commands.create_test_users.fake.phone_number')
    def test_skips_existing_phone(self, mock_fake_phone):
        mock_fake_phone.side_effect = ['+79123456789', '+79111111111', '+79222222222']
        User.objects.create_user(
            email='test@example.com',
            phone_number='+79123456789',
            last_name='Test',
            first_name='User',
            password='pass'
        )
        self._call_command('--users', '2')
        phones = User.objects.exclude(phone_number='+79123456789') \
            .values_list('phone_number', flat=True)
        self.assertEqual(phones.count(), 2)
        phones = [str(p) for p in phones]
        self.assertIn('+79111111111', phones)
        self.assertIn('+79222222222', phones)

    def test_falls_back_to_default_password_when_env_missing(self):
        self._call_command('--users', '1')
        user = User.objects.first()
        self.assertTrue(user.check_password('qwert543@'))

    @patch('app.accounts.management.commands.create_test_users.config')
    def test_uses_password_from_env(self, mock_config):
        mock_config.return_value = 'custom_password_123'
        self._call_command('--users', '1')
        user = User.objects.first()
        self.assertTrue(user.check_password('custom_password_123'))

    @patch('app.accounts.management.commands.create_test_users.User.objects.bulk_create')
    def test_rollback_on_user_creation_error(self, mock_bulk_create):
        mock_bulk_create.side_effect = Exception('Database error during bulk create')

        with self.assertRaises(Exception):
            self._call_command('--users', '1')

        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Guest.objects.count(), 0)

    @patch('app.accounts.management.commands.create_test_users.Guest.objects.bulk_create')
    def test_rollback_on_role_creation_error(self, mock_role_bulk):
        mock_role_bulk.side_effect = Exception('Database error during role creation')

        with self.assertRaises(Exception):
            self._call_command('--users', '1')

        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Guest.objects.count(), 0)



class DeleteUsersCommandTest(TestCase):
    def setUp(self):
        self.out = StringIO()
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

    def _call_command(self, user_lookup='', inputs=None):
        if inputs is None:
            inputs = []
        with patch('builtins.input', side_effect=inputs):
            call_command(
                'delete_users', user_lookup=user_lookup,
                stdout=self.out, stderr=StringIO()
            )

    def test_empty_lookup_prompts_confirmation(self):
        self._call_command(user_lookup='', inputs=['y'])
        output = self.out.getvalue()
        self.assertIn('Пользователи удалены', output)
        self.assertEqual(User.objects.count(), 0)

    def test_empty_lookup_cancelled(self):
        self._call_command(user_lookup='', inputs=['n'])
        output = self.out.getvalue()
        self.assertIn('Отменено', output)
        self.assertEqual(User.objects.count(), 5)

    def test_delete_users_by_email(self):
        self._call_command(user_lookup='email=user@example.com', inputs=['y'])
        output = self.out.getvalue()
        self.assertIn('user@example.com', output)
        self.assertIn('Пользователи удалены', output)
        self.assertEqual(User.objects.count(), 4)
        self.assertFalse(User.objects.filter(email='user@example.com').exists())

    def test_delete_users_by_first_name(self):
        self._call_command(user_lookup='first_name=Guest', inputs=['y'])
        self.assertEqual(User.objects.count(), 3)
        self.assertFalse(User.objects.filter(first_name='Guest').exists())

    def test_delete_users_by_multiple_fields(self):
        self._call_command(user_lookup='first_name=Guest,last_name=One', inputs=['y'])
        self.assertEqual(User.objects.count(), 4)
        self.assertFalse(
            User.objects.filter(first_name='Guest', last_name='One').exists()
        )

    def test_cancel_deletion_after_preview(self):
        self._call_command(user_lookup='email=admin@example.com', inputs=['n'])
        output = self.out.getvalue()
        self.assertIn('Отменено', output)
        self.assertEqual(User.objects.count(), 5)
        self.assertTrue(User.objects.filter(email='admin@example.com').exists())

    def test_no_users_match_lookup(self):
        self._call_command(user_lookup='email=nonexistent@example.com')
        output = self.out.getvalue()
        self.assertIn('Нет пользователей для удаления', output)
        self.assertEqual(User.objects.count(), 5)

    def test_deletes_associated_guest_profile(self):
        self._call_command(user_lookup='email__icontains=guest', inputs=['y'])
        self.assertEqual(Guest.objects.count(), 0)
        self.assertEqual(User.objects.count(), 3)

        self._call_command(user_lookup='email__icontains=moderator', inputs=['y'])
        self.assertEqual(Moderator.objects.count(), 0)
        self.assertEqual(User.objects.count(), 2)

        self._call_command(user_lookup='email__icontains=admin', inputs=['y'])
        self.assertEqual(Administrator.objects.count(), 0)
        self.assertEqual(User.objects.count(), 1)

    def test_non_existent_field_returns_error_with_suggestion(self):
        self._call_command(user_lookup='malil=admin@example.com')
        output = self.out.getvalue()
        self.assertIn('malil', output)
        self.assertIn('email', output)
        self.assertEqual(User.objects.count(), 5)

    def test_multiple_non_existent_fields(self):
        self._call_command(user_lookup='wrong1=value1,wrong2=value2')
        output = self.out.getvalue()
        self.assertIn('wrong1', output)
        self.assertIn('wrong2', output)
        self.assertEqual(User.objects.count(), 5)

    def test_invalid_lookup_str_returns_error(self):
        self._call_command(user_lookup='email:invalid_separator')
        output = self.out.getvalue()
        self.assertIn('email:invalid_separator', output)
        self.assertEqual(User.objects.count(), 5)
