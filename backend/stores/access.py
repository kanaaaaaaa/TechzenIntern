import secrets

from django.conf import settings
from django.core import signing
from rest_framework.permissions import BasePermission


TOKEN_SALT = "stores.app-access"


def password_matches(password):
    """Constant time check against the shared app password."""
    return secrets.compare_digest(str(password or ""), settings.APP_PASSWORD)


def issue_token():
    return signing.dumps({"app": "paymethodfinder"}, salt=TOKEN_SALT)


def token_is_valid(token):
    try:
        signing.loads(token, salt=TOKEN_SALT, max_age=settings.APP_ACCESS_MAX_AGE)
    except signing.BadSignature:
        return False
    return True


class HasAppAccess(BasePermission):
    """Allows requests that carry a token handed out for the app password."""

    message = "Enter the app password to continue."

    def has_permission(self, request, view):
        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        return scheme.lower() == "bearer" and token_is_valid(token)
