"""STEP 35 Phase M — historical backfill + health hardening."""

from datetime import timedelta
from decimal import Decimal

import pytest

from apps.customers.models import Customer
from apps.finance.models import AccountingEvent, JournalEntry
from apps.finance.services.backfill_service import AccountingBackfillService
from apps.finance.services.chart_service import ChartService
from apps.finance.services.health_service import AccountingHealthService
from apps.inventory.services.inventory_service import InventoryService
from apps.platform.models import Tenant, TenantSettings
from apps.products.models import Category, Product, Unit
from apps.sales.models import Expense, Invoice, InvoiceItem
from apps.sales.services.pos_service import PosService
from apps.settings_app.models import Branch, Company
from core.tenancy import tenant_context
from django.utils import timezone


@pytest.fixture
def harden_env(db):
    tenant = Tenant.objects.create(name="Harden Co", slug="harden-co", status=Tenant.STATUS_ACTIVE)
    TenantSettings.objects.create(
        tenant=tenant,
        accounting_cutover_date=timezone.localdate() + timedelta(days=1),
    )
    company = Company.objects.create(name="Harden Co", tenant=tenant)
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
        sku="H-1",
        name="Harden Item",
        category=category,
        unit=unit,
        cost_price=Decimal("4"),
        selling_price=Decimal("10"),
    )
    inv = InventoryService.ensure_inventory_record(product=product, warehouse=warehouse)
    inv.quantity = Decimal("20")
    inv.tenant_id = tenant.id
    inv.save(update_fields=["quantity", "tenant_id", "updated_at"])
    walkin = Customer.objects.create(
        tenant=tenant, customer_code="WALK", full_name="Walk-in Customer", branch=branch
    )
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="harden_user", password="pass12345", tenant=tenant, branch=branch
    )
    ChartService.ensure_default_chart(tenant_id=tenant.id)
    return {
        "tenant": tenant,
        "branch": branch,
        "product": product,
        "user": user,
        "warehouse": warehouse,
        "customer": walkin,
    }


@pytest.mark.django_db
def test_backfill_dry_run_finds_orphan_invoice(harden_env):
    tenant = harden_env["tenant"]
    branch = harden_env["branch"]
    product = harden_env["product"]
    user = harden_env["user"]

    # Historical invoice without going through POS posting
    inv = Invoice.objects.create(
        tenant=tenant,
        branch=branch,
        customer=harden_env["customer"],
        invoice_number="INV-HIST-1",
        status=Invoice.STATUS_PAID,
        issue_date=timezone.localdate() - timedelta(days=10),
        subtotal=Decimal("10"),
        tax_amount=Decimal("0"),
        total_amount=Decimal("10"),
        amount_paid=Decimal("10"),
        created_by=user,
    )
    InvoiceItem.objects.create(
        invoice=inv,
        product=product,
        quantity=Decimal("1"),
        unit_price=Decimal("10"),
        line_total=Decimal("10"),
    )

    preview = AccountingBackfillService.preview(tenant_id=tenant.id)
    assert preview["counts"]["invoices"] >= 1
    assert any(r["id"] == str(inv.id) for r in preview["missing"]["invoices"])
    assert preview["dry_run"] is True


@pytest.mark.django_db
def test_backfill_commit_posts_invoice_and_expense(harden_env):
    tenant = harden_env["tenant"]
    branch = harden_env["branch"]
    product = harden_env["product"]
    user = harden_env["user"]

    inv = Invoice.objects.create(
        tenant=tenant,
        branch=branch,
        customer=harden_env["customer"],
        invoice_number="INV-HIST-2",
        status=Invoice.STATUS_PAID,
        issue_date=timezone.localdate() - timedelta(days=5),
        subtotal=Decimal("10"),
        tax_amount=Decimal("0"),
        total_amount=Decimal("10"),
        amount_paid=Decimal("10"),
        notes="Payment: cash",
        created_by=user,
    )
    InvoiceItem.objects.create(
        invoice=inv,
        product=product,
        quantity=Decimal("1"),
        unit_price=Decimal("10"),
        line_total=Decimal("10"),
    )
    exp = Expense.objects.create(
        tenant=tenant,
        branch=branch,
        description="Old rent",
        category="rent",
        amount=Decimal("50"),
        expense_date=timezone.localdate() - timedelta(days=3),
        created_by=user,
    )

    result = AccountingBackfillService.run(
        tenant_id=tenant.id, dry_run=False, user=user
    )
    assert result["dry_run"] is False
    assert result["posted"]["invoices"] >= 1
    assert result["posted"]["expenses"] >= 1

    event = AccountingEvent.active_objects().get(
        idempotency_key=f"SALE_COMPLETED:sales:invoice:{inv.id}"
    )
    assert event.status == AccountingEvent.STATUS_POSTED
    journal = JournalEntry.active_objects().get(pk=event.journal_entry_id)
    assert "historical backfill" in (journal.notes or "")

    # Idempotent second run
    again = AccountingBackfillService.run(tenant_id=tenant.id, dry_run=False, user=user)
    assert again["posted"]["invoices"] == 0


@pytest.mark.django_db
def test_health_includes_subledger_and_mappings(harden_env):
    user = harden_env["user"]
    product = harden_env["product"]
    tenant = harden_env["tenant"]

    PosService.checkout(
        data={
            "branch_id": str(harden_env["branch"].id),
            "customer_id": "walkin",
            "waiter_name": "Alex",
            "payment_method": "cash",
            "items": [
                {"product_id": str(product.id), "quantity": "1", "unit_price": "10"}
            ],
        },
        user=user,
    )

    with tenant_context(tenant, enforce=True):
        report = AccountingHealthService.check(user=user)

    ids = {c["id"] for c in report["checks"]}
    assert "journals_balanced" in ids
    assert "account_mappings" in ids
    assert "ar_control" in ids
    assert "ap_control" in ids
    assert "inventory_gl" in ids
    assert "revenue_dual_run" in ids
    assert "cutover_date" in ids
    assert report["status"] in ("healthy", "degraded")
    mapping = next(c for c in report["checks"] if c["id"] == "account_mappings")
    assert mapping["ok"] is True
    cutover = next(c for c in report["checks"] if c["id"] == "cutover_date")
    assert "cutover set" in cutover["message"]
