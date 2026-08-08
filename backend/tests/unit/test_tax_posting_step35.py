"""STEP 35 Phase L — sales tax on GL (Tax Payable)."""

from decimal import Decimal

import pytest

from apps.customers.models import Customer
from apps.finance.models import Account, JournalEntry
from apps.finance.selectors.tax_report import TaxReportSelector
from apps.finance.services.chart_service import ChartService
from apps.finance.services.journal_service import JournalService
from apps.finance.services.mapping_service import MappingService
from apps.inventory.services.inventory_service import InventoryService
from apps.platform.models import Tenant
from apps.products.models import Category, Product, Unit
from apps.sales.services.pos_service import PosService
from apps.settings_app.models import Branch, Company
from core.tenancy import tenant_context


@pytest.fixture
def tax_env(db):
    tenant = Tenant.objects.create(name="Tax Co", slug="tax-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="Tax Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="HQ", code="HQ", is_default=True
    )
    from apps.inventory.models import Warehouse

    warehouse = Warehouse.objects.create(
        branch=branch, tenant=tenant, name="WH", code="WH1", is_default=True
    )
    category = Category.objects.create(name="General", tenant=tenant)
    unit = Unit.objects.create(name="Piece", abbreviation="pc", tenant=tenant)
    product = Product.objects.create(
        tenant=tenant,
        sku="TAX-1",
        name="Taxed Item",
        category=category,
        unit=unit,
        cost_price=Decimal("4"),
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
        username="tax_user", password="pass12345", tenant=tenant, branch=branch
    )
    ChartService.ensure_default_chart(tenant_id=tenant.id)
    return {"tenant": tenant, "branch": branch, "product": product, "user": user}


@pytest.mark.django_db
def test_tax_payable_account_seeded(tax_env):
    tenant = tax_env["tenant"]
    assert Account.active_objects().filter(tenant_id=tenant.id, code="2100").exists()
    tax = MappingService.resolve(key="DEFAULT_TAX_PAYABLE", tenant_id=tenant.id)
    assert tax.code == "2100"


@pytest.mark.django_db
def test_sale_with_tax_splits_revenue_and_payable(tax_env):
    user = tax_env["user"]
    product = tax_env["product"]
    tenant = tax_env["tenant"]

    # 2 × 10 = 20 subtotal, 10% tax = 2, total = 22; COGS = 8
    result = PosService.checkout(
        data={
            "branch_id": str(tax_env["branch"].id),
            "customer_id": "walkin",
            "waiter_name": "Alex",
            "payment_method": "cash",
            "tax_rate": "0.1",
            "items": [
                {"product_id": str(product.id), "quantity": "2", "unit_price": "10"}
            ],
        },
        user=user,
    )
    journal = JournalEntry.active_objects().get(
        source_type="invoice",
        source_id=result["invoice"]["id"],
        source_module="sales",
    )
    data = JournalService.serialize(journal)
    assert data["is_balanced"] is True
    assert data["total_debit"] == 30.0  # 22 cash + 8 COGS

    memos = {line["memo"]: line for line in data["lines"]}
    assert memos["Sales revenue"]["credit"] == 20.0
    assert memos["Sales tax"]["credit"] == 2.0

    tax = MappingService.resolve(key="DEFAULT_TAX_PAYABLE", tenant_id=tenant.id)
    assert float(ChartService.account_balance(account=tax)) == 2.0

    with tenant_context(tenant, enforce=True):
        report = TaxReportSelector.run()
    assert report["collected"] == 2.0
    assert report["refunded"] == 0.0
    assert report["net_payable"] == 2.0
    assert report["reconciled"] is True


@pytest.mark.django_db
def test_sale_without_tax_unchanged(tax_env):
    user = tax_env["user"]
    product = tax_env["product"]

    result = PosService.checkout(
        data={
            "branch_id": str(tax_env["branch"].id),
            "customer_id": "walkin",
            "waiter_name": "Alex",
            "payment_method": "cash",
            "items": [
                {"product_id": str(product.id), "quantity": "2", "unit_price": "10"}
            ],
        },
        user=user,
    )
    journal = JournalEntry.active_objects().get(source_id=result["invoice"]["id"])
    data = JournalService.serialize(journal)
    assert data["total_debit"] == 28.0
    memos = {line["memo"] for line in data["lines"]}
    assert "Sales tax" not in memos
    assert "Sales revenue" in memos
