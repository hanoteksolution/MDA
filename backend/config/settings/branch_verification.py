"""Isolated local PostgreSQL verification for the multi-branch gates (decision D9).

SQLite ignores ``select_for_update`` and cannot prove any locking or concurrency
claim, so the branch concurrency gates must run against a real PostgreSQL 14+.
Mirrors ``school_verification``; never use for deployment.

    cd backend && DJANGO_SETTINGS_MODULE=config.settings.branch_verification \\
        python3 -m pytest tests/unit/test_branch_postgresql.py
"""

import os

from .test import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("BRANCH_VERIFY_PG_NAME", "branch_verify"),
        "USER": os.environ.get("BRANCH_VERIFY_PG_USER", "postgres"),
        "PASSWORD": os.environ.get("BRANCH_VERIFY_PG_PASSWORD", "postgres"),
        "HOST": os.environ.get("BRANCH_VERIFY_PG_HOST", "127.0.0.1"),
        "PORT": os.environ.get("BRANCH_VERIFY_PG_PORT", "5432"),
        "TEST": {"NAME": "test_branch_verify", "CHARSET": "UTF8", "TEMPLATE": "template0"},
    }
}

# Test uploads must not create artifacts inside application media storage.
MEDIA_ROOT = "/tmp/mda-branch-verification-media"
