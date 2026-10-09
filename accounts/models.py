from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """OpsPilot user account."""

    def __str__(self):
        return self.username