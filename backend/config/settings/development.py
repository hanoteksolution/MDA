from .base import *  # noqa: F401,F403

DEBUG = True

DATABASES["default"]["ENGINE"] = "django.db.backends.sqlite3"  # noqa: F405
DATABASES["default"]["NAME"] = BASE_DIR / "db.sqlite3"  # noqa: F405
