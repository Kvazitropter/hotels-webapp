from django_filters.rest_framework import BooleanFilter, DateFilter, FilterSet, NumberFilter
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError

from app.hotels.models import Room


class RoomFilter(FilterSet):
    check_in = DateFilter()
    check_out = DateFilter()
    min_capacity = NumberFilter(field_name='room_type__standard_capacity', lookup_expr='gte')
    is_premium = BooleanFilter(field_name='is_premium')
    is_standard = BooleanFilter(field_name='is_standard')

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        check_in = parse_date(self.data.get('check_in', ''))
        check_out = parse_date(self.data.get('check_out', ''))
        if check_in and check_out:
            if check_in >= check_out:
                raise ValidationError('Дата заселения не может быть позднее даты выселения')
            return queryset.available(check_in, check_out)
        elif check_in or check_out:
            raise ValidationError('Необходимо указать обе даты: заселения и выселения')
        return queryset

    class Meta:
        model = Room
        fields = [
            'floor', 'bed_count', 'is_pets_allowed', 'is_smoking_allowed'
        ]
