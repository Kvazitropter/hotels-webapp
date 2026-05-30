from datetime import date, timedelta

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from app.hotels.filters import RoomFilter
from app.hotels.models import Hotel, Room
from app.hotels.serializers import (
    HotelSerializer,
    RoomListSerializer,
    RoomDetailSerializer
)
from app.hotels.utils.helpers.get_vacant_dates import get_vacant_dates


class HotelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Hotel.objects.filter(is_active=True)
    permission_classes = [AllowAny]
    serializer_class = HotelSerializer
    search_fields = ['country', 'city', 'name']


class HotelNestedMixin:
    def get_hotel(self):
        hotel_pk = self.kwargs.get('hotel_pk')
        try:
            return Hotel.objects.get(pk=hotel_pk, is_active=True)
        except Hotel.DoesNotExist as e:
            raise NotFound(detail=f'Отель с ID "{hotel_pk}" не найден') from e


class RoomViewSet(HotelNestedMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    filterset_class = RoomFilter
    search_fields = ['room_type__name']

    def get_queryset(self):
        hotel = self.get_hotel()
        return Room.objects.filter(hotel=hotel) \
            .annotate_is_premium() \
            .annotate_is_standard() \
            .select_related('room_type__category') \
            .prefetch_related('photos')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return RoomDetailSerializer
        return RoomListSerializer

    @action(detail=True, methods=['get'], url_path='vacant-dates')
    def vacant_dates(self, request, *args, **kwargs):
        room = self.get_object()
        try:
            after = date.fromisoformat(request.query_params.get('after', str(date.today())))
            before = date.fromisoformat(request.query_params.get(
                'before', str(date.today() + timedelta(days=365))
            ))
        except ValueError:
            return Response(
                {'detail': 'Некорректный формат даты, ожидается YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if after >= before:
            return Response(
                {'detail': 'after должен быть меньше before'},
                status=status.HTTP_400_BAD_REQUEST
            )
        vacant = get_vacant_dates(Room.objects.filter(pk=room.pk), after, before)
        return Response({'vacant_dates': vacant[room.pk]})
