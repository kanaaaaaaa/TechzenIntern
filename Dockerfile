# 1. Build the Vue app.
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 2. Serve it, and the API, from one Django process.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY --from=frontend /app/frontend/dist/ frontend/dist/

# Static files for the admin site; the frontend build is served by WhiteNoise.
# Settings now refuse to load without these, and collectstatic has to load them.
# Both are throwaway build-time values; the running container gets the real ones
# from the environment.
RUN DJANGO_SECRET_KEY=build-only APP_PASSWORD=build-only \
    python backend/manage.py collectstatic --noinput

COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

EXPOSE 8000
CMD ["./docker-entrypoint.sh"]
