from django.urls import path

from .views import (
    csrf_token,
    login_view,
    logout_view,
    session_view,
)

urlpatterns = [
    path("csrf/", csrf_token, name="auth-csrf"),
    path("login/", login_view, name="auth-login"),
    path("session/", session_view, name="auth-session"),
    path("logout/", logout_view, name="auth-logout"),
]