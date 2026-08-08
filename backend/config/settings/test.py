from .base import *  # noqa: F401,F403

DATABASES["default"] = {  # noqa: F405
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": ":memory:",
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

ALLOWED_HOSTS = ["*"]  # noqa: F405
TENANT_HOST_ENFORCEMENT = True  # noqa: F405

CELERY_TASK_ALWAYS_EAGER = True  # noqa: F405
CELERY_TASK_EAGER_PROPAGATES = True  # noqa: F405
