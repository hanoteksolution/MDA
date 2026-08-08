from django.urls import path

from .views import health, health_cache, health_celery, health_database, health_ready

urlpatterns = [
    path("", health, name="health"),
    path("database/", health_database, name="health-database"),
    path("cache/", health_cache, name="health-cache"),
    path("celery/", health_celery, name="health-celery"),
    path("ready/", health_ready, name="health-ready"),
]
