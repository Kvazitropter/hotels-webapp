from django.apps import apps
from django.db.models import Count, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.accounts.permissions import AdminOnly, GuestOnly, ModeratorOnly
from app.bookings.filters import BookingFilter, ReviewFilter
from app.bookings.models import Booking, Review
from app.bookings.serializers import (
    BookingListSerializer,
    BookingDetailSerializer,
    BookingCreateSerializer,
    BookingCancelSerializer,
    BookingMoveSerializer,
    ReviewListSerializer,
    ReviewDetailSerializer,
    ReviewCreateSerializer,
    ReviewUpdateSerializer
)


class BookingViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'post']
    filterset_class = BookingFilter
    ordering_fields = ['check_in_date', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Booking.objects.select_related(
            'guest__user', 'room__hotel', 'room__room_type',
            'cancellation', 'moved_to', 'moved_to__room__hotel'
        )
        if self.request.user.is_guest:
            return qs.filter(guest__user=self.request.user)
        return qs

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), GuestOnly()]
        if self.action in ('retrieve', 'cancel', 'move'):
            return [IsAuthenticated(), (AdminOnly|GuestOnly)()]
        if self.action == 'list':
            return [IsAuthenticated(), (AdminOnly|GuestOnly|ModeratorOnly)()]
        return [IsAuthenticated(), AdminOnly()]

    def get_serializer_class(self):
        if self.action == 'create':
            return BookingCreateSerializer
        if self.action == 'list':
            return BookingListSerializer
        return BookingDetailSerializer

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        serializer = BookingCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            booking.cancel(reason=serializer.validated_data['reason'])
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {'detail': 'Бронирование отменено.'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        booking = self.get_object()
        serializer = BookingMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            booking.move(
                new_check_in=serializer.validated_data['check_in_date'],
                new_check_out=serializer.validated_data['check_out_date'],
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            BookingDetailSerializer(booking.moved_to).data,
            status=status.HTTP_200_OK
        )


class ReviewViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'patch', 'delete']
    filterset_class = ReviewFilter
    ordering_fields = ['published_at', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Review.objects.select_related(
            'booking__room__hotel', 'booking__room__room_type'
        )
        if self.request.user.is_guest:
            return qs.filter(booking__guest__user=self.request.user)
        return qs

    def get_permissions(self):
        if self.action in ('create', 'partial_update', 'submit'):
            return [IsAuthenticated(), GuestOnly()]
        if self.action in ('destroy', 'archive'):
            return [IsAuthenticated(), (AdminOnly|GuestOnly)()]
        if self.action in ('publish', 'reject'):
            return [IsAuthenticated(), ModeratorOnly()]
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), (AdminOnly|GuestOnly|ModeratorOnly)()]
        return [IsAuthenticated(), AdminOnly()]

    def get_serializer_class(self):
        if self.action == 'create':
            return ReviewCreateSerializer
        if self.action in ('retrieve', 'submit', 'archive', 'publish', 'reject'):
            return ReviewDetailSerializer
        if self.action == 'partial_update':
            return ReviewUpdateSerializer
        return ReviewListSerializer

    def destroy(self, request, pk=None):
        review = self.get_object()
        if review.status in (Review.Status.PUBLISHED, Review.Status.ARCHIVED):
            return Response(
                {'detail': f'Нельзя удалить отзыв со статусом "{review.get_status_display()}"'},
                status=status.HTTP_403_FORBIDDEN
            )
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        review = self.get_object()
        if review.status != Review.Status.PUBLISHED:
            return Response(
                {'detail': 'Нельзя убрать из публичного доступа неопубликованный отзыв.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        review.status = Review.Status.ARCHIVED
        review.save(update_fields=['status'])
        return Response(
            {'detail': 'Отзыв скрыт из публичного доступа.'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        review = self.get_object()
        if review.status != Review.Status.DRAFT:
            return Response(
                {'detail': 'Отправить на модерацию можно только черновик'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Moderator = apps.get_model('accounts', 'Moderator')
        moderator = Moderator.objects.filter(user__is_active=True) \
            .annotate(
                active_reviews=Count(
                    'moderated_reviews',
                    filter=Q(moderated_reviews__status=Review.Status.ON_MODERATION)
                )
            ) \
            .order_by('active_reviews').first()
        if not moderator:
            return Response(
                {'detail': 'Нет доступных модераторов'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        review.status = Review.Status.ON_MODERATION
        review.moderated_by = moderator
        review.save(update_fields=['status', 'moderated_by'])
        return Response(
            {'detail': 'Отзыв отправлен на модерацию.'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        review = self.get_object()
        published_at = request.data.get('published_at')
        review.publish(request.user.moderator, published_at)
        return Response(ReviewDetailSerializer(review).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        review = self.get_object()
        reason = request.data.get('reason')
        if not reason:
            return Response(
                {'detail': 'Необходимо указать причину отказа.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        review.reject(request.user.moderator, reason)
        return Response(ReviewDetailSerializer(review).data, status=status.HTTP_200_OK)
