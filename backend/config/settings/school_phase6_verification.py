"""Disposable Phase 6 PostgreSQL gate, never a deployment setting."""
from .school_phase5_verification import *
DATABASES['default']['NAME']='school_phase6_verify'
DATABASES['default']['TEST']['NAME']='test_school_phase6_verify'
SCHOOL_PRIVATE_ROOT='/tmp/mda-school-phase6-private'
MEDIA_ROOT='/tmp/mda-school-phase6-media'
