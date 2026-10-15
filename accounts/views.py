import json

from django.contrib.auth import (
    authenticate,
    login,
    logout,
)
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST


def user_details(user):
    return {
        "id": user.pk,
        "username": user.username,
        "email": user.email,
    }


@never_cache
@require_GET
@ensure_csrf_cookie
def csrf_token(request):
    return JsonResponse({
        "csrfToken": get_token(request),
    })


@never_cache
@require_POST
def login_view(request):
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse(
            {"detail": "Invalid JSON request."},
            status=400,
        )

    if not isinstance(data, dict):
        return JsonResponse(
            {"detail": "Request must be a JSON object."},
            status=400,
        )

    username = data.get("username")
    password = data.get("password")

    if (
        not isinstance(username, str)
        or not isinstance(password, str)
        or not username.strip()
        or not password
    ):
        return JsonResponse(
            {"detail": "Username and password are required."},
            status=400,
        )

    user = authenticate(
        request,
        username=username.strip(),
        password=password,
    )

    if user is None:
        return JsonResponse(
            {"detail": "Invalid username or password."},
            status=401,
        )

    login(request, user)

    return JsonResponse({
        "user": user_details(user),
        "csrfToken": get_token(request),
    })


@never_cache
@require_GET
def session_view(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"detail": "Not authenticated."},
            status=401,
        )

    return JsonResponse({
        "user": user_details(request.user),
        "csrfToken": get_token(request),
    })


@never_cache
@require_POST
def logout_view(request):
    logout(request)

    return JsonResponse({
        "detail": "Logged out successfully.",
    })