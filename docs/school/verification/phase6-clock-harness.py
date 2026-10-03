"""Repeat the recorded regression business date without freezing audit timestamps."""
from datetime import date

def pytest_sessionstart(session):
    from django.utils import timezone
    original=timezone.localdate
    def business_date(value=None,timezone=None):
        return date(2026,9,21) if value is None else original(value,timezone)
    timezone.localdate=business_date
