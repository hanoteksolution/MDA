"""Production guard: a MOCK payment provider can never collect Safari's real money.

MOCK is the only payment adapter that exists, so without this guard a production
deployment would either let anyone holding the mock webhook secret "pay" for
subscriptions and SMS credits, or silently fall back to MOCK when no real
provider is configured. The guard is enforced twice — at Platform Admin
selection and again when the billing provider is resolved at runtime.

See ``apps/integrations/billing_guard.py``.
"""

from __future__ import annotations

import pytest
from django.test import override_settings

from apps.integrations.billing_guard import (
    MOCK_BLOCKED,
    billing_provider_problem,
    mock_providers_allowed,
    usable_billing_provider,
)
from apps.integrations.models import PaymentProviderConfig

pytestmark = [pytest.mark.unit, pytest.mark.critical]

PROD = override_settings(PAYMENT_ALLOW_MOCK_PROVIDERS=False)


def _mock_provider(**kwargs):
    """An unsaved MOCK provider; the guard never touches the database."""
    defaults = {"name": "Mock", "provider_type": PaymentProviderConfig.TYPE_MOCK, "is_active": True}
    defaults.update(kwargs)
    provider = PaymentProviderConfig(**defaults)
    provider.deleted_at = None
    return provider


# ── settings wiring ───────────────────────────────────────────────────────────

def test_production_settings_hardcode_the_guard_off():
    """production.py must not read this from the environment — a typo in .env cannot open it."""
    import ast
    from pathlib import Path

    src = Path(__file__).resolve().parents[2] / "config" / "settings" / "production.py"
    tree = ast.parse(src.read_text())
    assigned = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name) and target.id == "PAYMENT_ALLOW_MOCK_PROVIDERS"
    ]
    assert len(assigned) == 1, "production.py must assign PAYMENT_ALLOW_MOCK_PROVIDERS exactly once"
    assert isinstance(assigned[0], ast.Constant) and assigned[0].value is False, (
        "PAYMENT_ALLOW_MOCK_PROVIDERS must be the literal False in production, never config()"
    )


@override_settings(PAYMENT_ALLOW_MOCK_PROVIDERS=True)
def test_mock_allowed_in_development_and_test():
    assert mock_providers_allowed() is True
    assert billing_provider_problem(_mock_provider()) == ""
    assert usable_billing_provider(_mock_provider()) is not None


@PROD
def test_mock_not_allowed_in_production():
    assert mock_providers_allowed() is False


# ── Platform Admin cannot select MOCK as the billing provider ────────────────

@PROD
def test_platform_admin_selection_of_mock_is_rejected_in_production():
    assert billing_provider_problem(_mock_provider()) == MOCK_BLOCKED


@override_settings(PAYMENT_ALLOW_MOCK_PROVIDERS=True)
def test_platform_admin_selection_of_mock_is_permitted_outside_production():
    assert billing_provider_problem(_mock_provider()) == ""


# ── runtime resolution never falls back to MOCK ──────────────────────────────

@PROD
def test_runtime_resolution_treats_mock_as_no_provider():
    """A MOCK row reaching production — however it got there — resolves to None, not a fallback."""
    assert usable_billing_provider(_mock_provider()) is None


@PROD
def test_no_provider_configured_resolves_to_none():
    assert usable_billing_provider(None) is None
    assert billing_provider_problem(None) == ""


@PROD
def test_inactive_or_deleted_provider_resolves_to_none():
    from django.utils import timezone

    inactive = _mock_provider(is_active=False)
    assert usable_billing_provider(inactive) is None

    deleted = _mock_provider()
    deleted.deleted_at = timezone.now()
    assert usable_billing_provider(deleted) is None


# ── the two money paths fail safely ──────────────────────────────────────────

@PROD
def test_subscription_checkout_resolves_no_provider_when_only_mock_exists(monkeypatch):
    from apps.platform.services.subscription_billing_service import SubscriptionBillingService

    monkeypatch.setattr(
        SubscriptionBillingService, "config",
        staticmethod(lambda: {"payment_provider_id": "not-a-real-id"}),
    )
    assert SubscriptionBillingService.billing_provider() is None


@PROD
def test_sms_purchase_resolves_no_provider_when_only_mock_exists(monkeypatch):
    from apps.integrations.services import sms_credit_service
    from apps.integrations.services.sms_credit_service import SmsPurchaseService

    class _Settings:
        payment_provider = _mock_provider()

    monkeypatch.setattr(sms_credit_service.SmsBillingSettings, "load", staticmethod(lambda: _Settings()))
    assert SmsPurchaseService.billing_provider() is None
