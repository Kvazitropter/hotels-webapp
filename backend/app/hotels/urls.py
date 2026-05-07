from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from app.hotels.views import HotelViewSet, RoomViewSet

router = DefaultRouter()
router.register(r'hotels', HotelViewSet)

hotels_router = routers.NestedDefaultRouter(router, r'hotels', lookup='hotel')
hotels_router.register(r'rooms', RoomViewSet, basename='hotel-room')

urlpatterns = [
    path(r'', include(router.urls)),
    path(r'', include(hotels_router.urls)),
]
