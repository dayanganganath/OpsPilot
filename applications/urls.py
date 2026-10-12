from rest_framework.routers import DefaultRouter

from .views import ApplicationViewSet, EnvironmentViewSet

router = DefaultRouter()
router.register(
    "applications",
    ApplicationViewSet,
    basename="application",
)
router.register(
    "environments",
    EnvironmentViewSet,
    basename="environment",
)

urlpatterns = router.urls