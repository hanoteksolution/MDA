"""
Desktop / offline mode — local SQLite database in the app data folder.
Used when MDA ERP runs inside the Tauri desktop shell.
"""
import os
from pathlib import Path

from decouple import config

from .base import *  # noqa: F401,F403

DEBUG = config("DEBUG", default=True, cast=bool)
DESKTOP_MODE = True

DATA_DIR = Path(os.environ.get("MDA_DATA_DIR", BASE_DIR))  # noqa: F405
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASES = {  # noqa: F405
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "mda_erp.sqlite3",
    }
}

MEDIA_ROOT = DATA_DIR / "media"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
STATIC_ROOT = DATA_DIR / "staticfiles"

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

CORS_ALLOWED_ORIGINS = [  # noqa: F405
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://tauri.localhost",
    "http://tauri.localhost",
    "tauri://localhost",
]

# Local API only — desktop shell talks to 127.0.0.1
API_HOST = "127.0.0.1"
API_PORT = int(os.environ.get("MDA_API_PORT", "8000"))
