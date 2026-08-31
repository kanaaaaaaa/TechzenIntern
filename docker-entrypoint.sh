#!/bin/sh
set -e

cd /app/backend

python manage.py migrate --noinput

# The database is disposable, so recreate the admin account when credentials
# are supplied. Existing accounts are kept as they are.
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput || true
fi

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --access-logfile - \
  --error-logfile -
