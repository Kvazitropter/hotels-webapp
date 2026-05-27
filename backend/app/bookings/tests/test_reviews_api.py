from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from app.accounts.models import Administrator, Guest, Moderator
from app.bookings.models import Booking, Review
from app.hotels.models import Hotel, Room, RoomCategory, RoomType


User = get_user_model()


class MyReviewViewSetTest(APITestCase):
    def setUp(self):
        self.list_url = reverse('review-list')
        self.hotel = Hotel.objects.create(
            name='Тестовый Отель',
            phone_number='+79123456789',
            email='hotel@example.com',
            country='Тестия',
            city='Тестов',
            address='ул. Тест, д. 1',
            floor_count=5,
            is_active=True,
        )
        self.category = RoomCategory.objects.create(
            tier=RoomCategory.Tier.FIRST,
            min_area=10,
            requires_kitchen=False,
            required_bathroom_type=RoomCategory.BathroomType.PARTIAL,
            min_rooms=1,
        )
        self.room_type = RoomType.objects.create(
            name='Стандартный',
            category=self.category,
            description='Описание',
            size=20,
            standard_capacity=2,
            bedroom_count=1,
            living_room_count=0,
            bathroom_count=1,
            bathroom_type=RoomCategory.BathroomType.PARTIAL,
            has_kitchen=False,
        )
        self.room = Room.objects.create(
            hotel=self.hotel,
            room_type=self.room_type,
            bed_count=2,
            price_per_night=Decimal('100.00'),
            extra_pay_per_person=Decimal('20.00'),
            is_pets_allowed=True,
            is_smoking_allowed=True,
            floor=2,
            number_on_floor=5,
            variant='A',
        )

        self.guest_user1 = User.objects.create_user(
            email='guest1@example.com',
            first_name='Guest',
            last_name='Test',
            phone_number='+79111111111',
            password='GoodPassword432+'
        )
        self.guest1 = Guest.objects.create(user=self.guest_user1)
        self.guest_user2 = User.objects.create_user(
            email='guest2@example.com',
            first_name='Guest',
            last_name='Test',
            phone_number='+79222222222',
            password='GoodPassword432+',
        )
        self.guest2 = Guest.objects.create(user=self.guest_user2)
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            first_name='Admin',
            last_name='Test',
            phone_number='+79000000000',
            password='GoodPassword432+'
        )
        self.admin = Administrator.objects.create(user=self.admin_user)
        self.moderator_user = User.objects.create_user(
            email='moderator@example.com',
            first_name='Moderator',
            last_name='Test',
            phone_number='+79333333333',
            password='GoodPassword432+'
        )
        self.moderator = Moderator.objects.create(user=self.moderator_user)
        self.no_role_user = User.objects.create_user(
            email='user@example.com',
            first_name='User',
            last_name='NoRole',
            phone_number='+79444444444',
            password='GoodPassword432+'
        )

        closed_bookings = [
            Booking.objects.create(
                room=self.room,
                guest=self.guest1,
                adults_count=1,
                children_count=0,
                pets_count=0,
                check_in_date=date(2000 + i, 1, 1),
                check_out_date=date(2000 + i, 1, 7),
                status=Booking.Status.CLOSED
            ) for i in range(1, 6)
        ]
        self.published_review = Review.objects.create(
            booking=closed_bookings[0],
            rating=3,
            comment='Нормально',
            status=Review.Status.PUBLISHED,
            moderated_by=self.moderator,
            published_at=timezone.now()
        )
        self.on_moderation_review = Review.objects.create(
            booking=closed_bookings[1],
            rating=5,
            comment='Отлично!',
            status=Review.Status.ON_MODERATION,
            moderated_by=self.moderator
        )
        self.draft_review = Review.objects.create(
            booking=closed_bookings[2],
            rating=4,
            comment='Хорошо в целом',
            status=Review.Status.DRAFT
        )
        self.rejected_review = Review.objects.create(
            booking=closed_bookings[3],
            rating=2,
            comment='жфрпзфршщтям',
            status=Review.Status.REJECTED,
            moderated_by=self.moderator,
            rejection_reason='Неконструктивно'
        )
        self.archived_review = Review.objects.create(
            booking=closed_bookings[4],
            rating=4,
            comment='Хорошо',
            status=Review.Status.ARCHIVED,
            moderated_by=self.moderator,
            published_at=timezone.now()
        )

        self.other_published_review = Review.objects.create(
            booking=Booking.objects.create(
                room=self.room,
                guest=self.guest2,
                adults_count=1,
                children_count=0,
                pets_count=0,
                check_in_date=date(2011, 1, 1),
                check_out_date=date(2011, 1, 7),
                status=Booking.Status.CLOSED
            ),
            rating=4,
            comment='Хорошо отдохнули',
            status=Review.Status.PUBLISHED,
            moderated_by=self.moderator,
            published_at=timezone.now()
        )

        self.closed_booking = Booking.objects.create(
            room=self.room,
            guest=self.guest1,
            adults_count=1,
            children_count=0,
            pets_count=0,
            check_in_date=date(2000, 7, 1),
            check_out_date=date(2000, 7, 5),
            status=Booking.Status.CLOSED
        )
        self.review_data = {
            'booking_id': self.closed_booking.pk,
            'rating': 5,
            'comment': 'Лучший отель в мире',
        }

    def _get_detail_url(self, review_id):
        return reverse('review-detail', kwargs={'pk': review_id})

    def _get_archive_url(self, review_id):
        return reverse('review-archive', kwargs={'pk': review_id})

    def _get_submit_url(self, review_id):
        return reverse('review-submit', kwargs={'pk': review_id})

    def _get_publish_url(self, pk):
        return reverse('review-publish', kwargs={'pk': pk})

    def _get_reject_url(self, pk):
        return reverse('review-reject', kwargs={'pk': pk})

    def test_unauthenticated_cannot_list_reviews(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_role_user_cannot_list_reviews(self):
        self.client.force_authenticate(self.no_role_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_admin_can_list_all_reviews(self):
        users = [self.moderator_user, self.admin_user]

        for user in users:
            with self.subTest(role=user.role):
                self.client.force_authenticate(user)
                response = self.client.get(self.list_url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 6)

    def test_guest_can_list_own_reviews(self):
        self.client.force_authenticate(self.guest_user1)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)
        ids = [r['id'] for r in response.data]
        self.assertIn(self.draft_review.id, ids)
        self.assertIn(self.on_moderation_review.id, ids)
        self.assertIn(self.published_review.id, ids)
        self.assertIn(self.rejected_review.id, ids)
        self.assertIn(self.archived_review.id, ids)
        self.assertNotIn(self.other_published_review.id, ids)

    def test_guest_cannot_list_other_guest_reviews(self):
        self.client.force_authenticate(self.guest_user2)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(self.other_published_review.id, response.data[0]['id'])

    def test_filter_by_status(self):
        self.client.force_authenticate(self.guest_user1)
        response = self.client.get(self.list_url, {'status': Review.Status.DRAFT})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.draft_review.id)

        response = self.client.get(
            self.list_url,
            {'status': [Review.Status.PUBLISHED, Review.Status.REJECTED]}
        )
        ids = [r['id'] for r in response.data]
        self.assertEqual(len(ids), 2)
        self.assertIn(self.published_review.id, ids)
        self.assertIn(self.rejected_review.id, ids)

    def test_filter_by_rating(self):
        self.client.force_authenticate(self.guest_user1)
        response = self.client.get(self.list_url, {'rating': 4})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r['id'] for r in response.data]
        self.assertEqual(len(ids), 2)
        self.assertIn(self.draft_review.id, ids)
        self.assertIn(self.archived_review.id, ids)

    def test_default_ordering(self):
        self.client.force_authenticate(self.guest_user1)
        response = self.client.get(self.list_url)
        created_at_list = [timezone.datetime.fromisoformat(r['created_at']) for r in response.data]
        self.assertEqual(created_at_list, sorted(created_at_list, reverse=True))

    def test_ordering_by_created_at(self):
        self.client.force_authenticate(self.guest_user1)
        response = self.client.get(self.list_url, {'ordering': 'created_at'})
        created_at_list = [timezone.datetime.fromisoformat(r['created_at']) for r in response.data]
        self.assertEqual(created_at_list, sorted(created_at_list))

    def test_ordering_by_published_at(self):
        self.client.force_authenticate(self.guest_user1)
        response = self.client.get(self.list_url, {'ordering': 'published_at'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['id'], self.published_review.pk)

    def test_unauthenticated_cannot_retrieve_review(self):
        response = self.client.get(self._get_detail_url(self.draft_review.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_role_user_cannot_retrieve_reviews(self):
        self.client.force_authenticate(self.no_role_user)
        response = self.client.get(self._get_detail_url(self.draft_review.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_guest_can_retrieve_own_review(self):
        self.client.force_authenticate(self.guest_user1)
        response = self.client.get(self._get_detail_url(self.draft_review.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.draft_review.id)
        self.assertEqual(response.data['rating'], self.draft_review.rating)
        self.assertEqual(response.data['comment'], self.draft_review.comment)
        self.assertEqual(response.data['status'], Review.Status.DRAFT)
        self.assertEqual(response.data['booking_id'], self.draft_review.booking_id)

    def test_moderator_admin_can_retrieve_review(self):
        users = [self.moderator_user, self.admin_user]

        for user in users:
            with self.subTest(role=user.role):
                self.client.force_authenticate(user)
                response = self.client.get(self._get_detail_url(self.draft_review.id))
                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_guest_cannot_retrieve_other_guest_review(self):
        self.client.force_authenticate(self.guest_user2)
        response = self.client.get(self._get_detail_url(self.draft_review.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_nonexist_review_returns_404(self):
        self.client.force_authenticate(self.guest_user1)
        response = self.client.get(self._get_detail_url(9999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_guest_can_create_review_for_closed_booking(self):
        self.client.force_authenticate(self.guest_user1)
        response = self.client.post(self.list_url, self.review_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['rating'], self.review_data['rating'])
        self.assertEqual(response.data['comment'], self.review_data['comment'])
        self.assertIsNotNone(response.data['created_at'])
        review = Review.objects.filter(pk=response.data['id']).first()
        self.assertIsNotNone(review)
        self.assertEqual(review.status, Review.Status.DRAFT)
        self.assertIsNone(review.moderated_by)
        self.assertIsNone(review.published_at)

    def test_guest_cannot_create_review_for_active_booking(self):
        self.client.force_authenticate(self.guest_user1)
        self.closed_booking.status = Booking.Status.ACTIVE
        self.closed_booking.save(update_fields=['status'])
        self.closed_booking.refresh_from_db()
        response = self.client.post(self.list_url, self.review_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_guest_cannot_create_review_for_other_guest_booking(self):
        self.client.force_authenticate(self.guest_user2)
        response = self.client.post(self.list_url, self.review_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('booking', str(response.data))

    def test_guest_cannot_create_duplicate_review(self):
        self.client.force_authenticate(self.guest_user1)
        review_data = self.review_data.copy()
        review_data['booking_id'] = self.published_review.booking.pk
        response = self.client.post(self.list_url, review_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_guest_cannot_create_review(self):
        users = [self.moderator_user, self.admin_user]

        for user in users:
            with self.subTest(role=user.role):
                self.client.force_authenticate(user)
                response = self.client.post(self.list_url, self.review_data)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_review_without_comment(self):
        review_data = self.review_data.copy()
        del review_data['comment']
        self.client.force_authenticate(self.guest_user1)
        response = self.client.post(self.list_url, review_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['comment'])

    def test_create_review_validates_rating(self):
        review_data = self.review_data.copy()
        review_data['rating'] = 0
        self.client.force_authenticate(self.guest_user1)

        response1 = self.client.post(self.list_url, review_data)
        self.assertEqual(response1.status_code, status.HTTP_400_BAD_REQUEST)

        review_data['rating'] = 6
        response2 = self.client.post(self.list_url, review_data)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_review_validates_booking_id(self):
        review_data = self.review_data.copy()
        review_data['booking_id'] = 9999
        self.client.force_authenticate(self.guest_user1)
        response = self.client.post(self.list_url, review_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_cannot_update_draft_review(self):
        data = {'rating': 5, 'comment': 'Исправленный отзыв'}
        response = self.client.patch(self._get_detail_url(self.draft_review.pk), data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_guest_cannot_update_draft_review(self):
        users = [self.moderator_user, self.admin_user]
        data = {'rating': 5, 'comment': 'Исправленный отзыв'}

        for user in users:
            with self.subTest(role=user.role):
                self.client.force_authenticate(user)
                response = self.client.patch(self._get_detail_url(self.draft_review.pk), data)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_guest_can_update_draft_review(self):
        self.client.force_authenticate(self.guest_user1)
        data = {'rating': 5, 'comment': 'Исправленный отзыв'}
        response = self.client.patch(self._get_detail_url(self.draft_review.pk), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.draft_review.refresh_from_db()
        self.assertEqual(self.draft_review.rating, data['rating'])
        self.assertEqual(self.draft_review.comment, data['comment'])
        self.assertEqual(self.draft_review.status, Review.Status.DRAFT)

    def test_guest_cannot_update_non_draft_review(self):
        self.client.force_authenticate(self.guest_user1)
        reviews = [
            self.on_moderation_review, self.published_review,
            self.rejected_review, self.archived_review
        ]
        data = {'rating': 5, 'comment': 'Исправленный отзыв'}

        for review in reviews:
            with self.subTest(status=review.status):
                old_rating, old_comment = review.rating, review.comment
                response = self.client.patch(self._get_detail_url(review.pk), data)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                review.refresh_from_db()
                self.assertEqual(review.rating, old_rating)
                self.assertEqual(review.comment, old_comment)

    def test_guest_cannot_update_other_guest_review(self):
        self.client.force_authenticate(self.guest_user2)
        data = {'rating': 5, 'comment': 'Исправленный отзыв'}
        response = self.client.patch(self._get_detail_url(self.draft_review.pk), data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_nonexist_review_returns_404(self):
        self.client.force_authenticate(self.guest_user1)
        data = {'rating': 5, 'comment': 'Исправленный отзыв'}
        response = self.client.patch(self._get_detail_url(9999), data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_cannot_delete_review(self):
        data = {'rating': 5, 'comment': 'Исправленный отзыв'}
        response = self.client.patch(self._get_detail_url(self.draft_review.pk), data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_role_user_moderator_cannot_delete_review(self):
        users = [self.no_role_user, self.moderator_user]
        data = {'rating': 5, 'comment': 'Исправленный отзыв'}

        for user in users:
            with self.subTest(role=user.role):
                self.client.force_authenticate(user)
                response = self.client.patch(self._get_detail_url(self.draft_review.pk), data)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_guest_can_delete_draft_on_moderation_rejected_review(self):
        self.client.force_authenticate(self.guest_user1)
        reviews = [self.draft_review, self.on_moderation_review, self.rejected_review]

        for review in reviews:
            with self.subTest(status=review.status):
                response = self.client.delete(self._get_detail_url(review.pk))
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
                self.assertFalse(Review.objects.filter(id=review.pk).exists())

    def test_admin_can_delete_draft_on_moderation_rejected_review(self):
        self.client.force_authenticate(self.admin_user)
        reviews = [self.draft_review, self.on_moderation_review, self.rejected_review]

        for review in reviews:
            with self.subTest(status=review.status):
                response = self.client.delete(self._get_detail_url(review.pk))
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
                self.assertFalse(Review.objects.filter(id=review.pk).exists())

    def test_guest_cannot_delete_published_or_archived_review(self):
        self.client.force_authenticate(self.guest_user1)
        reviews = [self.published_review, self.archived_review]

        for review in reviews:
            with self.subTest(status=review.status):
                response = self.client.delete(self._get_detail_url(review.pk))
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
                self.assertTrue(Review.objects.filter(id=review.pk).exists())

    def test_guest_cannot_delete_other_guest_review(self):
        self.client.force_authenticate(self.guest_user2)
        response = self.client.delete(self._get_detail_url(self.draft_review.pk))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_cannot_archive_review(self):
        response = self.client.post(self._get_archive_url(self.published_review.pk))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_role_user_moderator_cannot_archive_review(self):
        users = [self.no_role_user, self.moderator_user]

        for user in users:
            with self.subTest(role=user.role):
                self.client.force_authenticate(user)
                response = self.client.post(self._get_archive_url(self.published_review.pk))
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_guest_can_archive_published_review(self):
        self.client.force_authenticate(self.guest_user1)
        response = self.client.post(self._get_archive_url(self.published_review.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.published_review.refresh_from_db()
        self.assertEqual(self.published_review.status, Review.Status.ARCHIVED)

    def test_admin_can_archive_published_review(self):
        self.client.force_authenticate(self.admin_user)
        response = self.client.post(self._get_archive_url(self.other_published_review.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.other_published_review.refresh_from_db()
        self.assertEqual(self.other_published_review.status, Review.Status.ARCHIVED)

    def test_guest_cannot_archive_review_beside_published(self):
        self.client.force_authenticate(self.guest_user1)
        reviews = [
            self.draft_review, self.on_moderation_review,
            self.rejected_review, self.archived_review
        ]

        for review in reviews:
            with self.subTest(status=review.status):
                response = self.client.post(self._get_archive_url(review.pk))
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                old_status = review.status
                review.refresh_from_db()
                self.assertEqual(review.status, old_status)

    def test_guest_cannot_archive_other_guest_review(self):
        self.client.force_authenticate(self.guest_user2)
        response = self.client.post(self._get_archive_url(self.published_review.pk))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_archive_nonexist_review_returns_404(self):
        self.client.force_authenticate(self.guest_user1)
        response = self.client.post(self._get_archive_url(9999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_guest_can_submit_draft_review(self):
        self.client.force_authenticate(self.guest_user1)
        response = self.client.post(self._get_submit_url(self.draft_review.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.draft_review.refresh_from_db()
        self.assertEqual(self.draft_review.status, Review.Status.ON_MODERATION)
        self.assertIsNotNone(self.draft_review.moderated_by)
        self.assertEqual(self.draft_review.moderated_by, self.moderator)

    def test_guest_cannot_submit_non_draft_review(self):
        self.client.force_authenticate(self.guest_user1)
        reviews = [
            self.published_review, self.on_moderation_review,
            self.rejected_review, self.archived_review
        ]

        for review in reviews:
            with self.subTest(status=review.status):
                response = self.client.post(self._get_submit_url(review.pk))
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                old_status = review.status
                review.refresh_from_db()
                self.assertEqual(review.status, old_status)

    def test_submit_fails_when_no_moderator_available(self):
        Review.objects.filter(moderated_by=self.moderator).update(
            status=Review.Status.DRAFT,
            moderated_by=None
        )
        self.moderator.delete()
        self.client.force_authenticate(self.guest_user1)
        response = self.client.post(self._get_submit_url(self.draft_review.pk))
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.draft_review.refresh_from_db()
        self.assertEqual(self.draft_review.status, Review.Status.DRAFT)
        self.assertIsNone(self.draft_review.moderated_by)

    def test_submit_selects_moderator_with_least_reviews_on_moderation(self):
        Moderator.objects.create(user=self.no_role_user)
        self.client.force_authenticate(self.guest_user1)
        self.client.post(self._get_submit_url(self.draft_review.pk))
        self.draft_review.refresh_from_db()
        self.assertEqual(self.draft_review.moderated_by, self.no_role_user.moderator)

    def test_guest_cannot_submit_other_guest_review(self):
        Guest.objects.create(user=self.no_role_user)
        self.no_role_user.refresh_from_db()
        self.client.force_authenticate(self.no_role_user)
        response = self.client.post(self._get_submit_url(self.draft_review.pk))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_submit_nonexist_review_returns_404(self):
        self.client.force_authenticate(self.guest_user1)
        response = self.client.post(self._get_submit_url(9999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_cannot_publish(self):
        response = self.client.post(self._get_publish_url(self.on_moderation_review.pk))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_moderator_cannot_publish_review(self):
        users = [self.no_role_user, self.guest_user1, self.admin_user]

        for user in users:
            with self.subTest(role=user.role):
                self.client.force_authenticate(user)
                response = self.client.post(self._get_publish_url(self.on_moderation_review.pk))
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_can_publish_on_moderation_review(self):
        self.client.force_authenticate(self.moderator_user)
        response = self.client.post(self._get_publish_url(self.on_moderation_review.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.on_moderation_review.refresh_from_db()
        self.assertEqual(self.on_moderation_review.status, Review.Status.PUBLISHED)
        self.assertIsNotNone(self.on_moderation_review.published_at)

    def test_moderator_can_publish_with_explicit_published_at(self):
        self.client.force_authenticate(self.moderator_user)
        published_at = timezone.make_aware(datetime(2025, 1, 1, 12))
        response = self.client.post(
            self._get_publish_url(self.on_moderation_review.pk),
            {'published_at': published_at},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.on_moderation_review.refresh_from_db()
        self.assertEqual(self.on_moderation_review.published_at, published_at)

    def test_publish_nonexistent_review_returns_404(self):
        self.client.force_authenticate(self.moderator_user)
        response = self.client.post(self._get_publish_url(9999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_cannot_reject(self):
        response = self.client.post(
            self._get_reject_url(self.on_moderation_review.pk), {'reason': 'Причина'}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_moderator_cannot_reject_review(self):
        users = [self.no_role_user, self.guest_user1, self.admin_user]

        for user in users:
            with self.subTest(role=user.role):
                self.client.force_authenticate(user)
                response = self.client.post(
                    self._get_reject_url(self.on_moderation_review.pk), {'reason': 'Причина'}
                )
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_can_reject_on_moderation_review(self):
        self.client.force_authenticate(self.moderator_user)
        response = self.client.post(
            self._get_reject_url(self.on_moderation_review.pk), {'reason': 'Спам'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.on_moderation_review.refresh_from_db()
        self.assertEqual(self.on_moderation_review.status, Review.Status.REJECTED)
        self.assertEqual(self.on_moderation_review.rejection_reason, 'Спам')

    def test_reject_without_reason_returns_400(self):
        self.client.force_authenticate(self.moderator_user)
        response = self.client.post(self._get_reject_url(self.on_moderation_review.pk), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_nonexistent_review_returns_404(self):
        self.client.force_authenticate(self.moderator_user)
        response = self.client.post(self._get_reject_url(9999), {'reason': 'x'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
