# homeser/urls.py
# This is the main URL configuration for the entire HomeSer Django project.
# It acts as the central dispatcher, including URL patterns from individual apps
# and defining project-wide routes like the admin interface and API documentation.

"""URL configuration for homeser project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (SpectacularAPIView, SpectacularRedocView,
                                   SpectacularSwaggerView)

from .views import favicon_view, home_view

urlpatterns = [
    path("", home_view, name="home"),
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    # Swagger/OpenAPI documentation endpoints
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # Handle favicon request
    path("favicon.ico", favicon_view, name="favicon"),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
