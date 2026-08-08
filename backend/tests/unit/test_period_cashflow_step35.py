"""STEP 35 Phase G — cash flow + financial period close/reopen."""

from decimal import Decimal

import pytest

from apps.customers.models import Customer
from apps.finance.models import FinancialPeriod
from apps.finance.selectors.cash_flow import CashFlowSelector
from apps.finance.services.chart_service import ChartService
from apps.finance.services.period_service import PeriodError, PeriodService
from apps.finance.services.posting_service import AccountingPostingService, PostingError
from apps.inventory.models import Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.platform.models import Tenant
from apps.products.models import Category, Product, Unit
from apps.sales.services.daily_ops_service import DailyOpsService
from apps.sales.services.pos_service import PosService
from apps.settings_app.models import Branch, Company
from core.tenancy import tenant_context


@pytest.fixture
def period_env(db):
    tenant = Tenant.objects.create(name="Period Co", slug="period-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="Period Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="HQ", code="HQ", is_default=True
    )
    warehouse = Warehouse.objects.create(
        branch=branch, tenant=tenant, name="WH", code="WH1", is_default=True
    )
    category = Category.objects.create(name="General", tenant=tenant)
    unit = Unit.objects.create(name="Piece", abbreviation="pc", tenant=tenant)
    product = Product.objects.create(
        tenant=tenant,
        sku="PER-1",
        name="Period Item",
        category=category,
        unit=unit,
        cost_price=Decimal("2"),
        selling_price=Decimal("10"),
    )
    inv = InventoryService.ensure_inventory_record(product=product, warehouse=warehouse)
    inv.quantity = Decimal("30")
    inv.tenant_id = tenant.id
    inv.save(update_fields=["quantity", "tenant_id", "updated_at"])
    Customer.objects.create(
        tenant=tenant, customer_code="WALK", full_name="Walk-in Customer", branch=branch
    )
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="period_user", password="pass12345", tenant=tenant, branch=branch
    )
    ChartService.ensure_default_chart(tenant_id=tenant.id)
    return {"tenant": tenant, "branch": branch, "product": product, "user": user}


@pytest.mark.django_db
def test_period_close_blocks_posting(period_env):
    tenant = period_env["tenant"]
    period = PeriodService.ensure_open_period(tenant_id=tenant.id)
    PeriodService.close(period_id=period.id)

    with pytest.raises(PostingError, match="closed"):
        DailyOpsService.create_expense(
            data={
                "branch_id": str(period_env["branch"].id),
                "description": "Should fail",
                "category": "rent",
                "amount": "10",
            },
            user=period_env["user"],
        )


@pytest.mark.django_db
def test_period_reopen_allows_posting(period_env):
    tenant = period_env["tenant"]
    period = PeriodService.ensure_open_period(tenant_id=tenant.id)
    PeriodService.close(period_id=period.id)
    PeriodService.reopen(period_id=period.id)
    period.refresh_from_db()
    assert period.status == FinancialPeriod.STATUS_OPEN

    payload = DailyOpsService.create_expense(
        data={
            "branch_id": str(period_env["branch"].id),
            "description": "After reopen",
            "category": "utilities",
            "amount": "12",
        },
        user=period_env["user"],
    )
    assert payload["amount"] == 12.0


@pytest.mark.django_db
def test_locked_period_cannot_reopen(period_env):
    period = PeriodService.ensure_open_period(tenant_id=period_env["tenant"].id)
    PeriodService.close(period_id=period.id)
    PeriodService.lock(period_id=period.id)
    with pytest.raises(PeriodError, match="Locked"):
        PeriodService.reopen(period_id=period.id)


@pytest.mark.django_db
def test_cash_flow_tracks_cash_movements(period_env):
    user = period_env["user"]
    product = period_env["product"]
    tenant = period_env["tenant"]

    PosService.checkout(
        data={
            "branch_id": str(period_env["branch"].id),
            "customer_id": "walkin",
            "waiter_name": "Alex",
            "payment_method": "cash",
            "items": [
                {"product_id": str(product.id), "quantity": "1", "unit_price": "10"}
            ],
        },
        user=user,
    )
    DailyOpsService.create_expense(
        data={
            "branch_id": str(period_env["branch"].id),
            "description": "Office supplies",
            "category": "supplies",
            "amount": "3",
        },
        user=user,
    )

    with tenant_context(tenant, enforce=True):
        report = CashFlowSelector.run()

    assert report["operating"]["net"] == 7.0  # +10 sale -3 expense
    assert report["closing_cash"] == report["opening_cash"] + report["net_change"]
    assert report["net_change"] == 7.0
