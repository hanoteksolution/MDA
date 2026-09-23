"""Disposable Phase 5 verification database; never deploy these settings."""
from .school_phase3_verification import *  # noqa: F401,F403
DATABASES['default']['NAME']='school_phase5_verify'
DATABASES['default']['TEST']['NAME']='test_school_phase5_verify'
SCHOOL_PRIVATE_ROOT='/tmp/mda-school-phase5-private'
MEDIA_ROOT='/tmp/mda-school-phase5-media'
