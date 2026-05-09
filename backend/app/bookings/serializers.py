from rest_framework import serializers

from app.bookings.models import Booking, CancelledBooking, Review
from app.hotels.models import Room
from utils.validators import validate_instance_for_serializer


class BookingListSerializer(serializers.ModelSerializer):
    hotel_name = serializers.CharField(source='room.hotel.name', read_only=True)
    room_number = serializers.CharField(source='room.room_number', read_only=True)
    room_type_name = serializers.CharField(source='room.room_type.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'hotel_name', 'room_number', 'room_type_name',
            'check_in_date', 'check_out_date', 'days_count',
            'adults_count', 'children_count', 'pets_count',
            'status', 'status_display', 'type', 'created_at',
        ]


class _CancelledBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CancelledBooking
        fields = ['id', 'cancelled_at', 'cancellation_reason']


class BookingDetailSerializer(BookingListSerializer):
    cancellation = _CancelledBookingSerializer(read_only=True, allow_null=True)
    moved_to_id = serializers.IntegerField(source='moved_to.id', read_only=True, allow_null=True)

    class Meta(BookingListSerializer.Meta):
        fields = BookingListSerializer.Meta.fields + [
            'cancellation', 'moved_to_id',
        ]


class BookingCreateSerializer(serializers.ModelSerializer):
    room_id = serializers.IntegerField()

    class Meta:
        model = Booking
        fields = [
            'room_id', 'check_in_date', 'check_out_date',
            'adults_count', 'children_count', 'pets_count', 'type',
        ]
        read_only_fields = ['id']

    def validate_room_id(self, value):
        try:
            Room.objects.get(pk=value)
        except Room.DoesNotExist as e:
            raise serializers.ValidationError(
                f'Номера с ID "{value}" не существует'
            ) from e
        return value

    def create(self, validated_data):
        guest = self.context['request'].user.guest
        room_id = validated_data.pop('room_id')
        room = Room.objects.get(pk=room_id)
        instance = Booking(guest=guest, room=room, **validated_data)
        validate_instance_for_serializer(instance)
        instance.save()
        return instance


class BookingCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)


class BookingMoveSerializer(serializers.Serializer):
    check_in_date = serializers.DateField()
    check_out_date = serializers.DateField()

    def validate(self, data):
        check_in = data.get('check_in_date')
        check_out = data.get('check_out_date')
        if check_in and check_out and check_in >= check_out:
            raise serializers.ValidationError(
                'Дата выселения должна быть позже даты заселения'
            )
        return data


class ReviewListSerializer(serializers.ModelSerializer):
    hotel_name = serializers.CharField(source='booking.room.hotel.name', read_only=True)
    room_type_name = serializers.CharField(source='booking.room.room_type.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'hotel_name', 'room_type_name', 'rating',
            'status', 'status_display', 'created_at'
        ]
        read_only_fields = ('status', 'created_at')


class ReviewDetailSerializer(serializers.ModelSerializer):
    booking_id = serializers.IntegerField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'booking_id', 'rating', 'comment', 'status', 'status_display',
            'moderated_by', 'rejection_reason', 'created_at', 'published_at'
        ]
        read_only_fields = ('status', 'moderated_by', 'created_at', 'published_at')


class ReviewCreateSerializer(serializers.ModelSerializer):
    booking_id = serializers.IntegerField()

    class Meta:
        model = Review
        fields = ['id', 'booking_id', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_booking_id(self, value):
        user = self.context['request'].user
        try:
            Booking.objects.get(
                pk=value, guest__user=user, status=Booking.Status.CLOSED
            )
        except Booking.DoesNotExist as e:
            raise serializers.ValidationError(
                f'У пользователя нет записи о закрытом бронировании с ID "{value}"'
            ) from e
        return value

    def create(self, validated_data):
        booking_id = validated_data.pop('booking_id')
        booking = Booking.objects.get(pk=booking_id)
        instance = Review(booking=booking, **validated_data)
        validate_instance_for_serializer(instance)
        instance.save()
        return instance


class ReviewUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['rating', 'comment']

    def validate(self, data):
        if self.instance.status != Review.Status.DRAFT:
            raise serializers.ValidationError('Редактировать можно только черновик')
        return data

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        validate_instance_for_serializer(instance)
        instance.save()
        return instance
