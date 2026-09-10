import secrets

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core import signing
from rest_framework.authentication import TokenAuthentication
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


class AppAccessAuthentication(TokenAuthentication):
    def authenticate(self, request):
        scheme, _, token_value = request.headers.get("Authorization", "").partition(" ")
        if scheme.lower() == "bearer" and token_is_valid(token_value):
            return (AnonymousUser(), token_value)
        return super().authenticate(request)


class HasAppAccess(BasePermission):
    """Allows requests that carry a token handed out for the app password."""

    message = "Enter the app password to continue."

    def has_permission(self, request, view):
        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        return scheme.lower() == "bearer" and token_is_valid(token)


class IsAuthenticatedOrHasAppAccess(BasePermission):
    """Allows authenticated users or valid app access tokens."""

    message = "Authentication credentials were not provided or were invalid."

    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            return True
        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        return scheme.lower() == "bearer" and token_is_valid(token)
