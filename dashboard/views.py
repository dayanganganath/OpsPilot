from django.db.models import Count, OuterRef, Q, Subquery
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from applications.models import Application
from incidents.models import Incident
from monitoring.models import MonitorCheck, ServiceMonitor


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        applications = Application.objects.filter(
            owner=request.user
        )

        monitors = ServiceMonitor.objects.filter(
            environment__application__owner=request.user
        )

        active_monitors = monitors.filter(
            is_active=True,
            environment__is_active=True,
            environment__application__is_active=True,
        )

        latest_check = (
            MonitorCheck.objects
            .filter(monitor_id=OuterRef("pk"))
            .order_by("-checked_at", "-id")
        )

        monitor_statuses = active_monitors.annotate(
            latest_status=Subquery(
                latest_check.values("status")[:1]
            )
        )

        counts = monitor_statuses.aggregate(
            up=Count(
                "pk",
                filter=Q(latest_status=MonitorCheck.Status.UP),
            ),
            down=Count(
                "pk",
                filter=Q(latest_status=MonitorCheck.Status.DOWN),
            ),
            error=Count(
                "pk",
                filter=Q(latest_status=MonitorCheck.Status.ERROR),
            ),
            unchecked=Count(
                "pk",
                filter=Q(latest_status__isnull=True),
            ),
        )

        incidents = Incident.objects.filter(
            monitor__environment__application__owner=request.user
        )

        return Response({
            "total_applications": applications.count(),
            "total_monitors": monitors.count(),
            "active_monitors": active_monitors.count(),
            "up_monitors": counts["up"],
            "down_monitors": counts["down"],
            "error_monitors": counts["error"],
            "unchecked_monitors": counts["unchecked"],
            "open_incidents": incidents.filter(
                status=Incident.Status.OPEN
            ).count(),
            "resolved_incidents": incidents.filter(
                status=Incident.Status.RESOLVED
            ).count(),
        })