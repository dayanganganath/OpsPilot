from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Incident
from .serializers import IncidentSerializer


class IncidentViewSet(ReadOnlyModelViewSet):
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Incident.objects
            .filter(
                monitor__environment__application__owner=(
                    self.request.user
                )
            )
            .select_related(
                "monitor",
                "monitor__environment",
                "monitor__environment__application",
            )
        )