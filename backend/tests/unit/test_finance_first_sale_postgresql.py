"""First-sale finance seeding race (PostgreSQL only; skips loudly elsewhere).

A brand-new tenant's first postings seed its chart of accounts, account mappings, posting rules
and the open period. These used to be check-then-create, so simultaneous first sales raced on
``uniq_fin_account_tenant_code`` (and could duplicate periods). ``ChartService.ensure_finance_ready``
/ ``PeriodService._create_open_period`` now serialise seeding per tenant.

    cd backend && DJANGO_SETTINGS_MODULE=config.settings.branch_verification \\
        python3 -m pytest tests/unit/test_finance_first_sale_postgresql.py
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import connection, connections
from django.db.models import Count, Sum
from rest_framework.test import APIClient

from apps.finance.models import Account, AccountMapping, JournalEntry, JournalLine, PostingRule
from apps.finance.models.financial_period import FinancialPeriod
from apps.inventory.models import Inventory
from apps.sales.models import Invoice
from tests.helpers.branch_factory import add_product, add_user, build_branch_tenant, set_inventory
from tests.helpers.shop_factory import auth_client_as

pytestmark = pytest.mark.django_db(transaction=True)
SALES = 8


@pytest.fixture
def fresh_tenant():
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL transactions and row locking.")
    ctx = build_branch_tenant(slug="pg-first-sale", branch_codes=("HODAN", "BAKAARO", "KM4"))
    product = add_product(ctx, sku="PG-FIRST")
    for code in ("HODAN", "BAKAARO", "KM4"):
        set_inventory(ctx, product=product, branch_code=code, quantity=Decimal("50"))
    assert not Account.objects.filter(tenant=ctx.tenant).exists()  # truly the first postings
    return ctx, product


def test_simultaneous_first_sales_seed_one_chart_and_all_succeed(fresh_tenant):
    ctx, product = fresh_tenant
    codes = ("HODAN", "BAKAARO", "KM4")
    users = {c: add_user(ctx, username=f"pg_first_{c.lower()}", branches=(c,)) for c in codes}
    barrier = Barrier(SALES)

    def sell(i):
        code = codes[i % 3]
        try:
            client = auth_client_as(APIClient(), users[code])
            barrier.wait(timeout=20)
            r = client.post("/api/v1/pos/checkout/", {
                "branch_id": str(ctx.branch(code).pk), "customer_id": "walkin", "waiter_name": "Counter",
                "payment_method": "cash", "idempotency_key": f"first-sale-{i}",
                "items": [{"product_id": str(product.pk), "quantity": "1", "unit_price": "10"}],
            }, format="json", HTTP_X_BRANCH_ID=str(ctx.branch(code).pk))
            return r.status_code if r.status_code == 201 else (r.status_code, r.content[:1500])
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=SALES) as pool:
        statuses = [f.result() for f in [pool.submit(sell, i) for i in range(SALES)]]

    assert statuses == [201] * SALES  # no request lost to the seeding race
    tenant = ctx.tenant
    # One canonical structure: no duplicated account codes, mappings, rules or periods.
    assert not Account.active_objects().filter(tenant=tenant).values("code").annotate(n=Count("id")).filter(n__gt=1).exists()
    assert Account.active_objects().filter(tenant=tenant, code="1000").count() == 1
    assert not AccountMapping.active_objects().filter(tenant=tenant).values("mapping_key", "business_type_code").annotate(n=Count("id")).filter(n__gt=1).exists()
    assert not PostingRule.active_objects().filter(tenant=tenant).values("event_type", "name").annotate(n=Count("id")).filter(n__gt=1).exists()
    assert FinancialPeriod.active_objects().filter(tenant=tenant).values("start_date").annotate(n=Count("id")).filter(n__gt=1).count() == 0
    # Sales exactly once each, stock deducted once per sale, journals balanced.
    assert Invoice.objects.filter(branch__tenant=tenant).count() == SALES
    assert sum(Inventory.objects.get(product=product, warehouse=ctx.warehouse(c)).quantity for c in codes) == Decimal(150 - SALES)
    entries = JournalEntry.active_objects().filter(tenant=tenant, status=JournalEntry.STATUS_POSTED)
    assert entries.exists()
    for entry in entries:
        totals = JournalLine.objects.filter(entry=entry).aggregate(d=Sum("debit"), c=Sum("credit"))
        assert totals["d"] == totals["c"], entry.pk
    assert entries.values("idempotency_key").annotate(n=Count("id")).filter(n__gt=1).count() == 0
