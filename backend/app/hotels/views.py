from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import NotFound

from app.hotels.filters import RoomFilter
from app.hotels.models import Hotel, Room
from app.hotels.serializers import (
    HotelSerializer,
    RoomListSerializer,
    RoomDetailSerializer
)


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
