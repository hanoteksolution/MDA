"""Production secret hygiene checks (STEP 30)."""

from __future__ import annotations

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_INSECURE_SECRET_MARKERS = (
    "dev-secret-key-change-in-production",
    "change-me",
    "django-insecure",
)


def validate_production_secrets() -> None:
    if getattr(settings, "DEBUG", True):
        return

    secret = getattr(settings, "SECRET_KEY", "") or ""
    lowered = secret.lower()
    for marker in _INSECURE_SECRET_MARKERS:
        if marker in lowered:
            logger.error(
                "Insecure SECRET_KEY detected in production. Set a unique SECRET_KEY env var."
            )
            break

    if len(secret) < 32:
        logger.warning("SECRET_KEY is shorter than 32 characters — use a longer random value.")

    db_password = settings.DATABASES.get("default", {}).get("PASSWORD", "")
    if db_password in ("postgres", "password", ""):
        logger.warning("Database password looks like a default — rotate credentials for production.")
