from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("stores.urls")),
]

if (settings.FRONTEND_DIST / "index.html").exists():
    # Every other path is a frontend route, so hand it the single page app.
    urlpatterns.append(
        re_path(
            r"^(?!api/|admin/|static/|assets/).*$",
            TemplateView.as_view(template_name="index.html"),
            name="frontend",
        )
    )
