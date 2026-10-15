from rest_framework.routers import DefaultRouter

from .views import ServiceMonitorViewSet

router = DefaultRouter()
router.register(
    "monitors",
    ServiceMonitorViewSet,
    basename="monitor",
)

urlpatterns = router.urls