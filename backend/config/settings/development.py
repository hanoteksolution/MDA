from .base import *  # noqa: F401,F403

DEBUG = True
PAYMENT_ALLOW_MOCK_PROVIDERS = True  # MOCK billing for local development

DATABASES["default"]["ENGINE"] = "django.db.backends.sqlite3"  # noqa: F405
DATABASES["default"]["NAME"] = BASE_DIR / "db.sqlite3"  # noqa: F405
