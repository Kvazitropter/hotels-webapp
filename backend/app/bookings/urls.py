from django.urls import path, include
from rest_framework.routers import DefaultRouter

from app.bookings.views import BookingViewSet, ReviewViewSet


router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'reviews', ReviewViewSet, basename='review')

urlpatterns = [
    path(r'me/', include(router.urls)),
]
