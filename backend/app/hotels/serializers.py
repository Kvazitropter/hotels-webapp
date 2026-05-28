from rest_framework import serializers

from app.hotels.models import Hotel, RoomType, Room, RoomPhoto


class HotelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hotel
        fields = [
            'id', 'name', 'email', 'phone_number', 'check_in_time', 'check_out_time',
            'country', 'city', 'address', 'floor_count'
        ]


class RoomTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomType
        fields = [
            'id', 'name', 'description', 'size', 'standard_capacity', 'bedroom_count',
            'living_room_count', 'bathroom_count', 'bathroom_type', 'has_kitchen',
            'has_balcony' 
        ]


class RoomPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomPhoto
        fields = ['id', 'photo_url', 'order_number']


class RoomListSerializer(serializers.ModelSerializer):
    room_type_name = serializers.CharField(source='room_type.name')
    room_type_description = serializers.CharField(source='room_type.description')
    category = serializers.CharField(source='room_type.category.get_tier_display')
    is_premium = serializers.BooleanField(source='room_type.category.is_premium')
    is_standard = serializers.BooleanField(source='room_type.category.is_standard')
    standard_capacity = serializers.IntegerField(source='room_type.standard_capacity')
    cover_photo = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            'id', 'category', 'room_type_name', 'room_type_description', 'is_premium',
            'is_standard', 'standard_capacity', 'cover_photo', 'price_per_night'
        ]

    def get_cover_photo(self, obj):
        photo = obj.photos.order_by('order_number').first()
        if photo:
            return RoomPhotoSerializer(photo, context=self.context).data
        return None


class RoomDetailSerializer(RoomListSerializer):
    room_number = serializers.CharField(read_only=True)
    size = serializers.IntegerField(source='room_type.size')
    room_type = RoomTypeSerializer(read_only=True)
    photos = RoomPhotoSerializer(many=True, read_only=True)
    is_premium = serializers.BooleanField(source='room_type.category.is_premium')
    is_standard = serializers.BooleanField(source='room_type.category.is_standard')

    class Meta(RoomListSerializer.Meta):
        fields = [
            'id', 'room_number', 'floor', 'category', 'is_premium',
            'is_standard', 'size', 'standard_capacity', 'bed_count', 
            'is_pets_allowed', 'is_smoking_allowed',
            'price_per_night', 'extra_pay_per_person',
            'room_type', 'photos'
        ]
