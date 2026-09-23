"""SEC-5 sweep: a branch-A user calling every branch-scoped endpoint with a branch-B id.

``test_branch_isolation_api.py`` covers organization, inventory, dashboard, availability,
reports and notifications. This file covers the rest: branch transfers, POS shifts,
finance, payments and integrations. The caller has *every* relevant permission, but only
on HODAN; each row is owned by BAKAARO or MAIN. The only acceptable outcomes are 403/404
(or, for lists, the row is absent) — never the foreign data.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from cryptography.fernet import Fernet
from rest_framework.test import APIClient

from apps.inventory.services.branch_transfer_service import BranchTransferService, TransferLineInput
from apps.integrations.models import PaymentProviderConfig
from apps.sales.services.cashier_session_service import CashierSessionService
from tests.helpers.branch_factory import add_owner, add_product, add_user, grant, make_profile, set_inventory
from tests.helpers.payment_factory import build_payment_ctx, make_invoice, make_provider, start_payment
from tests.helpers.shop_factory import auth_client_as
from tests.unit.test_branch_pos import make_terminal

pytestmark = [pytest.mark.django_db, pytest.mark.isolation]

REJECTED = {403, 404}

CODENAMES = [
    "inventory.view", "inventory.transfer", "pos.access", "finance.view", "reports.view",
    "integrations.view", "integrations.manage", "integrations.payments.view",
    "integrations.payments.collect", "integrations.payments.reconcile",
]


@pytest.fixture
def world(db, settings):
    settings.INTEGRATION_ENCRYPTION_KEY = Fernet.generate_key().decode()
    ctx = build_payment_ctx("sweep", branches=("HODAN", "BAKAARO", "MAIN"))
    profile = make_profile(tenant=ctx.tenant, code="SWEEP", name="Sweep", codenames=CODENAMES)
    user = add_user(ctx, username="sweep_hodan", role_slug="admin")
    grant(ctx, user=user, branch_code="HODAN", profile=profile, is_default=True)
    owner = add_owner(ctx, username="sweep_owner")

    product = add_product(ctx, sku="SWEEP-1")
    set_inventory(ctx, product=product, branch_code="BAKAARO", quantity=Decimal("50"))
    transfer = BranchTransferService.request_transfer(
        source_branch_id=ctx.branch("BAKAARO").pk,
        destination_branch_id=ctx.branch("MAIN").pk,
        source_warehouse_id=ctx.warehouse("BAKAARO").pk,
        destination_warehouse_id=ctx.warehouse("MAIN").pk,
        lines=[TransferLineInput(product_id=product.pk, quantity=Decimal("5"))],
        user=owner,
    )

    make_terminal(ctx, "BAKAARO")
    shift = CashierSessionService.open_session(user=owner, branch_id=ctx.branch("BAKAARO").pk)

    provider = make_provider(ctx, branch="BAKAARO", name="bak-pay")
    invoice = make_invoice(ctx, "BAKAARO")
    intent, _ = start_payment(ctx, invoice, provider=provider)
    return {
        "ctx": ctx, "user": user, "client": auth_client_as(APIClient(), user),
        "transfer": transfer, "shift": shift, "provider": provider, "invoice": invoice, "intent": intent,
    }


def _ids(response):
    body = response.json()
    data = body.get("data", body)
    rows = data.get("results", data) if isinstance(data, dict) else data
    return {str(r.get("id")) for r in rows} if isinstance(rows, list) else set()


def test_branch_transfer_endpoints_refuse_a_transfer_between_foreign_branches(world):
    client, t = world["client"], world["transfer"]
    base = f"/api/v1/inventory/branch-transfers/{t.pk}/"
    assert client.get(base).status_code in REJECTED
    for action in ("approve", "reject", "reserve", "dispatch", "receive", "complete", "cancel"):
        response = client.post(f"{base}{action}/", {"lines": []}, format="json")
        assert response.status_code in REJECTED, (action, response.status_code)  # 404: not even visible
    listing = client.get("/api/v1/inventory/branch-transfers/")
    assert listing.status_code == 200
    assert str(t.pk) not in _ids(listing)
    t.refresh_from_db()
    assert t.status == "REQUESTED"  # nothing moved


def test_branch_transfer_list_refuses_a_forged_branch_filter(world):
    ctx, client = world["ctx"], world["client"]
    for code in ("BAKAARO", "MAIN"):
        response = client.get(f"/api/v1/inventory/branch-transfers/?branch_id={ctx.branch(code).pk}")
        assert response.status_code in REJECTED or _ids(response) == set(), code
        response = client.get("/api/v1/inventory/branch-transfers/", HTTP_X_BRANCH_ID=str(ctx.branch(code).pk))
        assert response.status_code in REJECTED or _ids(response) == set(), code


def test_a_transfer_cannot_be_requested_from_a_foreign_source_branch(world):
    ctx, client = world["ctx"], world["client"]
    product = add_product(ctx, sku="SWEEP-2")
    response = client.post(
        "/api/v1/inventory/branch-transfers/",
        {
            "source_branch_id": str(ctx.branch("BAKAARO").pk),
            "destination_branch_id": str(ctx.branch("MAIN").pk),
            "source_warehouse_id": str(ctx.warehouse("BAKAARO").pk),
            "destination_warehouse_id": str(ctx.warehouse("MAIN").pk),
            "lines": [{"product_id": str(product.pk), "quantity": "1"}],
        },
        format="json",
    )
    assert response.status_code in REJECTED | {400}, response.status_code
    assert response.status_code != 201


def test_pos_shift_endpoints_refuse_a_foreign_branch(world):
    ctx, client, shift = world["ctx"], world["client"], world["shift"]
    bakaaro = str(ctx.branch("BAKAARO").pk)

    assert client.get(f"/api/v1/pos/sessions/?branch_id={bakaaro}").status_code in REJECTED or \
        str(shift.pk) not in _ids(client.get(f"/api/v1/pos/sessions/?branch_id={bakaaro}"))
    assert str(shift.pk) not in _ids(client.get("/api/v1/pos/sessions/"))

    current = client.get(f"/api/v1/pos/sessions/current/?branch_id={bakaaro}")
    assert current.status_code in REJECTED or not (current.json().get("data") or {}).get("id")

    opened = client.post("/api/v1/pos/sessions/open/", {"branch_id": bakaaro, "opening_float": "0"}, format="json")
    assert opened.status_code in REJECTED | {400}, opened.status_code
    assert opened.status_code != 201

    moved = client.post(
        "/api/v1/pos/sessions/cash-movement/",
        {"branch_id": bakaaro, "movement_type": "CASH_OUT", "amount": "10", "reason": "x"},
        format="json",
    )
    assert moved.status_code in REJECTED | {400}, moved.status_code
    shift.refresh_from_db()
    assert shift.status == "open"


def test_finance_branch_trial_balance_never_shows_foreign_branches(world):
    body = world["client"].get("/api/v1/finance/reports/trial-balance/by-branch/")
    assert body.status_code in {200} | REJECTED
    if body.status_code == 200:
        text = body.content.decode()
        for code in ("BAKAARO", "MAIN"):
            assert f'"branch_code": "{code}"' not in text and f'"branch_code":"{code}"' not in text, code


def test_payment_intents_are_invisible_and_unreadable_across_branches(world):
    client, intent, invoice, ctx = world["client"], world["intent"], world["invoice"], world["ctx"]
    base = "/api/v1/integrations/payments"
    assert client.get(f"{base}/intents/{intent.pk}/").status_code in REJECTED
    assert str(intent.pk) not in _ids(client.get(f"{base}/intents/"))
    created = client.post(
        f"{base}/intents/", {"invoice_id": str(invoice.pk), "idempotency_key": "sweep-1"}, format="json"
    )
    assert created.status_code in REJECTED, created.status_code
    # Webhook events and reconciliation are Platform Admin only.
    platform, q = "/api/v1/platform/integrations/payments", f"?tenant_id={ctx.tenant.pk}"
    assert client.get(f"{platform}/webhook-events/{q}").status_code == 403
    assert client.post(f"{platform}/reconciliation/{uuid.uuid4()}/resolve/{q}", {"note": "x"}, format="json").status_code == 403


def test_payment_providers_are_not_visible_or_manageable_by_tenant_users(world):
    ctx, client, provider = world["ctx"], world["client"], world["provider"]
    base, q = "/api/v1/platform/integrations/payment-providers/", f"?tenant_id={ctx.tenant.pk}"
    listing = client.get(f"{base}{q}")
    assert listing.status_code == 403
    assert str(provider.pk) not in listing.content.decode()
    response = client.patch(f"{base}{provider.pk}/{q}", {"branch_id": str(ctx.branch("HODAN").pk)}, format="json")
    assert response.status_code in REJECTED, response.status_code
    provider.refresh_from_db()
    assert str(provider.branch_id) == str(ctx.branch("BAKAARO").pk)
    assert PaymentProviderConfig.objects.filter(pk=provider.pk).exists()


def test_sms_and_credentials_endpoints_do_not_leak_secrets_or_foreign_rows(world):
    client, provider = world["client"], world["provider"]
    for path in (f"/api/v1/platform/integrations/credentials/?tenant_id={world['ctx'].tenant.pk}", "/api/v1/integrations/sms-logs/"):
        response = client.get(path)
        assert response.status_code in {200} | REJECTED
        assert "whsec" not in response.content.decode().lower()
