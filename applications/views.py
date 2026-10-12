from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Application, Environment
from .serializers import (
    ApplicationSerializer,
    EnvironmentSerializer,
)


class ApplicationViewSet(ReadOnlyModelViewSet):
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Application.objects
            .filter(owner=self.request.user)
            .select_related("owner")
        )


class EnvironmentViewSet(ReadOnlyModelViewSet):
    serializer_class = EnvironmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Environment.objects
            .filter(application__owner=self.request.user)
            .select_related("application")
        )