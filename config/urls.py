from django.contrib import admin
from django.urls import include, path

from .views import health

urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("applications.urls")),
    path("api/", include("monitoring.urls")),
    path("api/", include("incidents.urls")),
    path("api/", include("dashboard.urls")),
    path("api-auth/", include("rest_framework.urls")),
]