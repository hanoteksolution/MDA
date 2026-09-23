"""Disposable Phase 3 PostgreSQL database; never deploy with these settings."""
import os
from .test import *  # noqa: F401,F403

DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': 'school_phase3_verify',
    'USER': os.environ.get('SCHOOL_VERIFY_PG_USER', 'postgres'),
    'PASSWORD': os.environ.get('SCHOOL_VERIFY_PG_PASSWORD', 'postgres'),
    'HOST': '127.0.0.1',
    'PORT': os.environ.get('SCHOOL_VERIFY_PG_PORT', '5432'),
    'TEST': {'NAME': 'test_school_phase3_verify', 'CHARSET': 'UTF8', 'TEMPLATE': 'template0'},
}}
SCHOOL_PRIVATE_ROOT = '/tmp/mda-school-phase3-private'
MEDIA_ROOT = '/tmp/mda-school-phase3-media'
