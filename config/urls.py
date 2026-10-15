from django.contrib import admin
from django.urls import include, path

from .views import health

urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("api/", include("applications.urls")),
    path("api/", include("monitoring.urls")),
    path("api-auth/", include("rest_framework.urls")),
]