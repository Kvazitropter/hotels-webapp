from decouple import config
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from health_check.views import HealthCheckView


HEALTH_TOKEN = config('HEALTH_TOKEN')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('app.accounts.urls')),
    path('api/', include('app.hotels.urls')),
    path('api/', include('app.bookings.urls')),
    path('health/{HEALTH_TOKEN}/',  HealthCheckView.as_view(
            checks=[
                "health_check.Cache",
                "health_check.Database",
                "health_check.Mail"
            ]
        )
    )
]

if settings.DEBUG:
    urlpatterns += [
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path(
            'api/docs/',
            SpectacularSwaggerView.as_view(url_name='schema'),
            name='swagger-ui'
        ),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
