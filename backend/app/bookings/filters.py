from django_filters.rest_framework import DateFilter, FilterSet, MultipleChoiceFilter, NumberFilter

from app.bookings.models import Booking, Review


class BookingFilter(FilterSet):
    status = MultipleChoiceFilter(choices=Booking.Status.choices)
    hotel_id = NumberFilter(field_name='room__hotel__id')
    check_in_from = DateFilter(field_name='check_in_date', lookup_expr='gte')
    check_in_to = DateFilter(field_name='check_in_date', lookup_expr='lte')

    class Meta:
        model = Booking
        fields = ['status', 'hotel_id', 'check_in_from', 'check_in_to']


class ReviewFilter(FilterSet):
    status = MultipleChoiceFilter(choices=Review.Status.choices)
    rating = NumberFilter()

    class Meta:
        model = Review
        fields = ['status', 'rating']
