from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from .models import ServiceMonitor
from .serializers import (
    MonitorCheckSerializer,
    ServiceMonitorSerializer,
)
from .services import run_monitor_check


class ServiceMonitorViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    serializer_class = ServiceMonitorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            ServiceMonitor.objects
            .filter(
                environment__application__owner=self.request.user
            )
            .select_related(
                "environment",
                "environment__application",
            )
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="check-now",
    )
    def check_now(self, request, pk=None):
        monitor = self.get_object()

        try:
            result = run_monitor_check(monitor)
        except ValueError as error:
            return Response(
                {"detail": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = MonitorCheckSerializer(result)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="history",
    )
    def history(self, request, pk=None):
        monitor = self.get_object()
        checks = monitor.checks.all()[:100]

        serializer = MonitorCheckSerializer(
            checks,
            many=True,
        )

        return Response(serializer.data)