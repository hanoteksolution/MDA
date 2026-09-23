"""Shared fixtures for the Phase 8 payment framework tests (SQLite unit tests and the PG race test)."""

from __future__ import annotations

import json
import time
from decimal import Decimal

from apps.customers.models import Customer
from apps.finance.services.chart_service import ChartService
from apps.integrations.models import PaymentProviderConfig
from apps.integrations.providers.payment_base import sign
from apps.integrations.services import CredentialService, PaymentService
from apps.sales.models import Invoice
from tests.helpers.branch_factory import build_branch_tenant

WEBHOOK_SECRET = "whsec-TEST-9f8e7d6c5b4a"


def build_payment_ctx(slug: str, branches=("HODAN", "BAKAARO")):
    ctx = build_branch_tenant(slug=slug, branch_codes=branches)
    ChartService.ensure_default_chart(tenant_id=ctx.tenant.pk)
    return ctx


def make_provider(ctx, *, branch=None, name="mockpay", secret=WEBHOOK_SECRET, **config) -> PaymentProviderConfig:
    cred = CredentialService.create(tenant=ctx.tenant, label=f"{name}-webhook", secret=secret)
    return PaymentProviderConfig.objects.create(
        tenant=ctx.tenant, name=name, provider_type="MOCK", webhook_credential=cred,
        branch=ctx.branch(branch) if branch else None, config=config,
    )


def make_invoice(ctx, branch_code="HODAN", *, total="100", status="sent", amount_paid="0", number=None) -> Invoice:
    branch = ctx.branch(branch_code)
    customer, _ = Customer.objects.get_or_create(
        tenant=ctx.tenant, customer_code=f"C-{branch_code}", defaults={"full_name": "Cust", "branch": branch}
    )
    count = Invoice.objects.filter(tenant=ctx.tenant).count() + 1
    return Invoice.objects.create(
        tenant=ctx.tenant, branch=branch, customer=customer, invoice_number=number or f"INV-{branch_code}-{count}",
        status=status, subtotal=Decimal(total), total_amount=Decimal(total), amount_paid=Decimal(amount_paid),
    )


def start_payment(ctx, invoice, *, key="key-1", amount=None, provider=None):
    return PaymentService.create_intent(
        tenant=ctx.tenant, invoice=invoice, idempotency_key=key, amount=amount,
        provider_id=provider.pk if provider else None,
    )


def signed(*, event_id, reference, amount, kind="payment.succeeded", secret=WEBHOOK_SECRET, ts=None):
    """``(raw_body, signature, timestamp)`` exactly as a provider would send them."""
    body = json.dumps(
        {"event_id": event_id, "type": kind, "reference": reference, "amount": str(amount)}
    ).encode()
    timestamp = str(int(time.time()) if ts is None else int(ts))
    return body, sign(secret, timestamp, body), timestamp


def deliver(provider, *, event_id, reference, amount, kind="payment.succeeded", secret=WEBHOOK_SECRET, ts=None):
    body, signature, timestamp = signed(
        event_id=event_id, reference=reference, amount=amount, kind=kind, secret=secret, ts=ts
    )
    return PaymentService.receive_webhook(provider=provider, raw_body=body, signature=signature, timestamp=timestamp)
