from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from app.accounts.views import (
    UserViewSet,
    GuestViewSet,
    ModeratorViewSet,
    AdminViewSet,
    RegisterView,
    LogoutView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    MeView,
)


router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'guests', GuestViewSet, basename='guest')
router.register(r'moderators', ModeratorViewSet, basename='moderator')
router.register(r'admins', AdminViewSet, basename='admin')

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/password-reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('auth/password-reset/confirm/',
        PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('me',
        MeView.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'deactivate'}),
        name='me'
    ),
    path('me/contact-change/',
        MeView.as_view({'patch': 'request_change'}), name='me-contact-request'),
    path('me/contact-change/confirm/',
        MeView.as_view({'post': 'confirm_change'}), name='me-contact-confirm'),
    path('', include(router.urls)),
]
