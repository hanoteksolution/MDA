from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("api.v1.urls")),
]

# django.conf.urls.static.static() is a no-op when DEBUG=False — wire media
# explicitly so nginx can proxy /media/ to the API when needed.
if settings.MEDIA_URL and settings.MEDIA_ROOT:
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
