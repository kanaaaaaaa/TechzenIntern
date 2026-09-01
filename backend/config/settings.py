import os
import sys
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured


def env_list(name, default):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

# Production is the default. A forgotten DJANGO_DEBUG must not open the app up,
# so development is the setting you have to ask for.
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"

# `manage.py test` runs with DEBUG off but still needs the secrets below. Only
# the literal test command matches; gunicorn's argv never does.
RUNNING_TESTS = sys.argv[1:2] == ["test"]


def env_secret(name, development_value):
    """A secret production must supply. Development gets a throwaway stand-in."""
    value = os.environ.get(name)
    if value:
        return value
    if DEBUG or RUNNING_TESTS:
        return development_value
    raise ImproperlyConfigured(
        f"{name} is not set. Set it in the environment before starting the server "
        f"(on Render: the service's Environment tab), or export DJANGO_DEBUG=true "
        f"to run locally with an insecure development value."
    )


# Never give these a usable default: a secret with a fallback baked into the
# repository is a secret everyone who can read the repository already has.
SECRET_KEY = env_secret("DJANGO_SECRET_KEY", "insecure-development-secret-key")
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")

# Render exposes the public hostname this way; other hosts use DJANGO_ALLOWED_HOSTS.
if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(os.environ["RENDER_EXTERNAL_HOSTNAME"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "stores",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    # The built frontend lives here, so index.html can be served for app routes.
    "DIRS": [FRONTEND_DIST],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ],
    },
}]
WSGI_APPLICATION = "config.wsgi.application"

# Set DATABASE_URL (e.g. postgres://...) to move off SQLite; nothing else changes.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    ),
}

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Tokyo"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
# Serve the frontend build (index.html, /assets/...) straight from WhiteNoise.
WHITENOISE_ROOT = FRONTEND_DIST if FRONTEND_DIST.exists() else None
WHITENOISE_INDEX_FILE = True

# Only needed while the frontend runs on its own Vite server.
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "")

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # The test client speaks plain HTTP, so redirecting it would turn every
    # assertion into a 301. The rest of the hardening below still applies.
    SECURE_SSL_REDIRECT = (
        not RUNNING_TESTS
        and os.environ.get("DJANGO_SECURE_SSL_REDIRECT", "true").lower() == "true"
    )
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

APP_PASSWORD = env_secret("APP_PASSWORD", "development-only-password")
APP_ACCESS_MAX_AGE = int(os.environ.get("APP_ACCESS_MAX_AGE", 60 * 60 * 24 * 30))

REST_FRAMEWORK = {
    # Everything needs the app password; the token is issued by /api/access/.
    "DEFAULT_PERMISSION_CLASSES": ["stores.access.HasAppAccess"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    # One password guards the whole app, so it is one target worth guessing at.
    # Only /api/access/ carries this scope; the rest of the API is unthrottled.
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "app-access": os.environ.get("APP_ACCESS_THROTTLE_RATE", "10/hour"),
    },
    # Throttling counts per client IP. Render terminates TLS on one proxy in
    # front of this service, so the last X-Forwarded-For entry is the real
    # client. Left unset, DRF keys off the whole header, which a client can
    # forge to hand itself a fresh bucket on every request. Set 0 when nothing
    # proxies this service.
    "NUM_PROXIES": int(os.environ.get("DJANGO_NUM_PROXIES", "1")),
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

