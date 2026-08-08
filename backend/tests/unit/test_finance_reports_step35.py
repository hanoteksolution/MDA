"""STEP 35 Phase F — P&L, balance sheet, expense reverse, health."""

from decimal import Decimal

import pytest

from apps.finance.models import AccountingEvent, JournalEntry
from apps.finance.selectors.balance_sheet import BalanceSheetSelector
from apps.finance.selectors.profit_loss import ProfitLossSelector
from apps.finance.services.chart_service import ChartService
from apps.finance.services.health_service import AccountingHealthService
from apps.finance.services.journal_service import JournalService
from apps.finance.services.reversal_service import AccountingReversalService
from apps.platform.models import Tenant
from apps.sales.models import Expense
from apps.sales.services.daily_ops_service import DailyOpsService
from apps.sales.services.pos_service import PosService
from apps.customers.models import Customer
from apps.inventory.services.inventory_service import InventoryService
from apps.products.models import Category, Product, Unit
from apps.inventory.models import Warehouse
from apps.settings_app.models import Branch, Company
from core.tenancy import tenant_context


@pytest.fixture
def report_env(db):
    tenant = Tenant.objects.create(name="Report Co", slug="report-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="Report Co", tenant=tenant)
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
        sku="RPT-1",
        name="Report Item",
        category=category,
        unit=unit,
        cost_price=Decimal("3"),
        selling_price=Decimal("10"),
    )
    inv = InventoryService.ensure_inventory_record(product=product, warehouse=warehouse)
    inv.quantity = Decimal("50")
    inv.tenant_id = tenant.id
    inv.save(update_fields=["quantity", "tenant_id", "updated_at"])
    Customer.objects.create(
        tenant=tenant, customer_code="WALK", full_name="Walk-in Customer", branch=branch
    )
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="report_user", password="pass12345", tenant=tenant, branch=branch
    )
    ChartService.ensure_default_chart(tenant_id=tenant.id)
    return {
        "tenant": tenant,
        "branch": branch,
        "product": product,
        "user": user,
    }


@pytest.mark.django_db
def test_expense_update_reverses_and_reposts(report_env):
    payload = DailyOpsService.create_expense(
        data={
            "branch_id": str(report_env["branch"].id),
            "description": "Old rent",
            "category": "rent",
            "amount": "100",
        },
        user=report_env["user"],
    )
    expense_id = payload["id"]
    first = JournalEntry.active_objects().get(
        source_type="expense", source_id=expense_id, reverses_entry__isnull=True
    )

    DailyOpsService.update_expense(
        expense_id=expense_id,
        data={"amount": "150", "description": "Updated rent"},
        user=report_env["user"],
    )

    assert JournalEntry.active_objects().filter(reverses_entry=first).exists()
    active = AccountingReversalService.find_posted_for_source(
        tenant_id=report_env["tenant"].id,
        source_type="expense",
        source_id=expense_id,
    )
    assert active is not None
    data = JournalService.serialize(active)
    assert data["total_debit"] == 150.0
    assert AccountingEvent.active_objects().filter(
        source_id=expense_id, status=AccountingEvent.STATUS_REVERSED
    ).exists()


@pytest.mark.django_db
def test_expense_delete_reverses_journal(report_env):
    payload = DailyOpsService.create_expense(
        data={
            "branch_id": str(report_env["branch"].id),
            "description": "Temp",
            "category": "supplies",
            "amount": "40",
        },
        user=report_env["user"],
    )
    expense_id = payload["id"]
    original = JournalEntry.active_objects().get(source_type="expense", source_id=expense_id)

    DailyOpsService.delete_expense(expense_id=expense_id, user=report_env["user"])

    assert JournalEntry.active_objects().filter(reverses_entry=original).exists()
    assert (
        AccountingReversalService.find_posted_for_source(
            tenant_id=report_env["tenant"].id,
            source_type="expense",
            source_id=expense_id,
        )
        is None
    )
    assert Expense.active_objects().filter(pk=expense_id).count() == 0


@pytest.mark.django_db
def test_profit_loss_and_balance_sheet(report_env):
    tenant = report_env["tenant"]
    user = report_env["user"]
    product = report_env["product"]

    PosService.checkout(
        data={
            "branch_id": str(report_env["branch"].id),
            "customer_id": "walkin",
            "waiter_name": "Alex",
            "payment_method": "cash",
            "items": [
                {"product_id": str(product.id), "quantity": "2", "unit_price": "10"}
            ],
        },
        user=user,
    )
    DailyOpsService.create_expense(
        data={
            "branch_id": str(report_env["branch"].id),
            "description": "Utilities",
            "category": "utilities",
            "amount": "5",
        },
        user=user,
    )

    with tenant_context(tenant, enforce=True):
        pl = ProfitLossSelector.run()
        bs = BalanceSheetSelector.run()
        health = AccountingHealthService.check()

    assert pl["totals"]["revenue"] >= 20.0
    assert pl["totals"]["expenses"] >= 5.0
    assert pl["totals"]["net_profit"] == pl["totals"]["revenue"] - pl["totals"]["expenses"]
    assert bs["totals"]["assets"] > 0
    assert bs["totals"]["is_balanced"] is True
    assert health["status"] in ("healthy", "degraded")
    assert any(c["id"] == "journals_balanced" and c["ok"] for c in health["checks"])
