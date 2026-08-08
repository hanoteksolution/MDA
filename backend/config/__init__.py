from .celery import app as celery_app

# Celery CLI (`celery -A config`) looks for `app` or `celery`.
app = celery_app

__all__ = ("celery_app", "app")

