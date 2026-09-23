"""Isolated local PostgreSQL release verification; never use for deployment."""
import os
from .test import *  # noqa: F401,F403

DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': 'school_verify',
    'USER': os.environ.get('SCHOOL_VERIFY_PG_USER', 'postgres'),
    'HOST': '127.0.0.1',
    'PORT': os.environ.get('SCHOOL_VERIFY_PG_PORT', '55439'),
    'TEST': {'NAME': 'test_school_verify', 'CHARSET': 'UTF8', 'TEMPLATE': 'template0'},
}}
# Test uploads must not create artifacts inside application media storage.
MEDIA_ROOT = '/tmp/mda-school-verification-media'
