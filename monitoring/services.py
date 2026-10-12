import time

import httpx

from .models import MonitorCheck


def run_monitor_check(monitor):
    environment = monitor.environment
    application = environment.application

    if not (
        monitor.is_active
        and environment.is_active
        and application.is_active
    ):
        raise ValueError(
            "Monitor, environment and application must be active."
        )

    checked_url = monitor.url
    expected_code = monitor.expected_status_code

    status_code = None
    error_message = ""
    check_status = MonitorCheck.Status.ERROR

    started = time.perf_counter()

    try:
        with httpx.Client(
            timeout=monitor.timeout_seconds,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            with client.stream("GET", checked_url) as response:
                status_code = response.status_code

                if status_code == expected_code:
                    check_status = MonitorCheck.Status.UP
                else:
                    check_status = MonitorCheck.Status.DOWN

    except httpx.TimeoutException:
        error_message = "Request timed out."

    except httpx.RequestError:
        error_message = "Could not connect to the service."

    except httpx.InvalidURL:
        error_message = "Invalid monitoring URL."

    elapsed_ms = round(
        (time.perf_counter() - started) * 1000,
        2,
    )

    return MonitorCheck.objects.create(
        monitor=monitor,
        checked_url=checked_url,
        expected_status_code=expected_code,
        status=check_status,
        status_code=status_code,
        response_time_ms=elapsed_ms,
        error_message=error_message,
    )