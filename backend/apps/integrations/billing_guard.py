"""Production guard: a MOCK payment provider can never collect Safari's real money.

MOCK is the only payment adapter today and is essential for development and tests, but in
production it would let anyone holding its webhook secret "pay" for subscriptions or SMS credits.
``PAYMENT_ALLOW_MOCK_PROVIDERS`` is hard ``False`` in ``config.settings.production`` (not
env-overridable), defaults to ``DEBUG`` elsewhere, and is explicitly ``True`` for development/test.

Enforced twice: when a Platform Admin selects a billing provider (rejected), and at runtime when the
billing provider is resolved (a MOCK row — however it got there — is treated as "no provider", so
checkout and package purchasing fail safely as "not available").
"""

from __future__ import annotations

from django.conf import settings

MOCK_BLOCKED = "MOCK payment providers cannot be used as the billing provider in production."


def mock_providers_allowed() -> bool:
    return bool(getattr(settings, "PAYMENT_ALLOW_MOCK_PROVIDERS", False))


def billing_provider_problem(provider) -> str:
    """Why ``provider`` may not collect Safari billing payments here, or ``""``."""
    from apps.integrations.models import PaymentProviderConfig

    if provider is None:
        return ""
    if provider.provider_type == PaymentProviderConfig.TYPE_MOCK and not mock_providers_allowed():
        return MOCK_BLOCKED
    return ""


def usable_billing_provider(provider):
    """The provider if it may collect billing payments now, else ``None`` (never a MOCK fallback)."""
    if provider is None or not provider.is_active or provider.deleted_at is not None:
        return None
    return None if billing_provider_problem(provider) else provider
