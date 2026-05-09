from django.urls import path, include
from rest_framework.routers import DefaultRouter

from app.bookings.views import (
    BookingCreateView,
    MyBookingViewSet,
    MyReviewViewSet
)


router = DefaultRouter()
router.register(r'me/bookings', MyBookingViewSet, basename='my-booking')
router.register(r'me/reviews', MyReviewViewSet, basename='my-review')

urlpatterns = [
    path('bookings/', BookingCreateView.as_view(), name='create-booking'),
    path(r'', include(router.urls)),
]
