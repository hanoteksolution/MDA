"""STEP 35 Phase C — POS checkout → Central Accounting Engine."""

from decimal import Decimal

import pytest

from apps.customers.models import Customer
from apps.finance.models import AccountingEvent, JournalEntry
from apps.finance.services.chart_service import ChartService
from apps.finance.services.journal_service import JournalService
from apps.inventory.models import Inventory
from apps.inventory.services.inventory_service import InventoryService
from apps.platform.models import Tenant
from apps.products.models import Category, Product, Unit
from apps.sales.models import Payment
from apps.sales.services.pos_service import PosService
from apps.settings_app.models import Branch, Company


@pytest.fixture
def pos_gl_env(db):
    tenant = Tenant.objects.create(name="POS GL Co", slug="pos-gl-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="POS GL Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="Main", code="MAIN", is_default=True
    )
    from apps.inventory.models import Warehouse

    warehouse = Warehouse.objects.create(
        branch=branch, tenant=tenant, name="WH", code="WH1", is_default=True
    )
    category = Category.objects.create(name="General", tenant=tenant)
    unit = Unit.objects.create(name="Piece", abbreviation="pc", tenant=tenant)
    product = Product.objects.create(
        tenant=tenant,
        sku="GL-1",
        name="GL Item",
        category=category,
        unit=unit,
        cost_price=Decimal("4"),
        selling_price=Decimal("10"),
    )
    inv = InventoryService.ensure_inventory_record(product=product, warehouse=warehouse)
    inv.quantity = Decimal("20")
    inv.tenant_id = tenant.id
    inv.save(update_fields=["quantity", "tenant_id", "updated_at"])
    Customer.objects.create(
        tenant=tenant,
        customer_code="WALK",
        full_name="Walk-in Customer",
        branch=branch,
    )
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="pos_gl_cashier",
        password="pass12345",
        tenant=tenant,
        branch=branch,
    )
    registered = Customer.objects.create(
        tenant=tenant,
        customer_code="REG1",
        full_name="Registered Customer",
        branch=branch,
    )
    return {
        "tenant": tenant,
        "branch": branch,
        "product": product,
        "user": user,
        "registered": registered,
        "warehouse": warehouse,
    }


def _cart(product, qty="2", price="10"):
    return [{"product_id": str(product.id), "quantity": qty, "unit_price": price}]


@pytest.mark.django_db
def test_pos_cash_sale_posts_balanced_journal(pos_gl_env):
    user = pos_gl_env["user"]
    product = pos_gl_env["product"]
    ChartService.ensure_default_chart(tenant_id=pos_gl_env["tenant"].id)

    result = PosService.checkout(
        data={
            "branch_id": str(pos_gl_env["branch"].id),
            "customer_id": "walkin",
            "waiter_name": "Alex",
            "payment_method": "cash",
            "items": _cart(product, "2"),
        },
        user=user,
    )
    invoice_id = result["invoice"]["id"]
    journal = JournalEntry.active_objects().get(
        source_type="invoice",
        source_id=invoice_id,
        source_module="sales",
    )
    data = JournalService.serialize(journal)
    assert data["is_balanced"] is True
    assert data["total_debit"] == 28.0  # revenue 20 + COGS 8

    event = AccountingEvent.active_objects().get(journal_entry_id=journal.id)
    assert event.event_type == "SALE_COMPLETED"
    assert event.status == AccountingEvent.STATUS_POSTED


@pytest.mark.django_db
def test_pos_split_sale_debits_multiple_assets(pos_gl_env):
    user = pos_gl_env["user"]
    product = pos_gl_env["product"]

    PosService.checkout(
        data={
            "branch_id": str(pos_gl_env["branch"].id),
            "customer_id": "walkin",
            "waiter_name": "Alex",
            "payment_method": "split",
            "items": _cart(product, "2"),
            "payments": [
                {"method": "cash", "amount": "12"},
                {"method": "mobile", "amount": "8"},
            ],
        },
        user=user,
    )
    journal = JournalEntry.active_objects().filter(source_module="sales").latest("created_at")
    memos = {line["memo"] for line in JournalService.serialize(journal)["lines"]}
    assert "cash" in memos
    assert "mobile" in memos


@pytest.mark.django_db
def test_pos_on_account_posts_receivable(pos_gl_env):
    user = pos_gl_env["user"]
    product = pos_gl_env["product"]
    customer = pos_gl_env["registered"]
    ChartService.ensure_default_chart(tenant_id=pos_gl_env["tenant"].id)

    result = PosService.checkout(
        data={
            "branch_id": str(pos_gl_env["branch"].id),
            "customer_id": str(customer.id),
            "waiter_name": "Alex",
            "payment_method": "on_account",
            "items": _cart(product, "1"),
        },
        user=user,
    )
    journal = JournalEntry.active_objects().get(source_id=result["invoice"]["id"])
    ar_line = next(
        line
        for line in JournalService.serialize(journal)["lines"]
        if line["account_code"] == "1100"
    )
    assert ar_line["debit"] == 10.0


@pytest.mark.django_db
def test_pos_checkout_journal_idempotent(pos_gl_env):
    user = pos_gl_env["user"]
    product = pos_gl_env["product"]
    payload = {
        "branch_id": str(pos_gl_env["branch"].id),
        "customer_id": "walkin",
        "waiter_name": "Alex",
        "payment_method": "cash",
        "items": _cart(product, "1"),
        "idempotency_key": "pos-gl-idem-1",
    }
    PosService.checkout(data=payload, user=user)
    PosService.checkout(data=payload, user=user)
    assert JournalEntry.active_objects().filter(idempotency_key__startswith="SALE_COMPLETED:").count() == 1
    assert AccountingEvent.active_objects().filter(event_type="SALE_COMPLETED").count() == 1


@pytest.mark.django_db
def test_refund_posts_return_journal(pos_gl_env):
    user = pos_gl_env["user"]
    product = pos_gl_env["product"]

    result = PosService.checkout(
        data={
            "branch_id": str(pos_gl_env["branch"].id),
            "customer_id": "walkin",
            "waiter_name": "Alex",
            "payment_method": "cash",
            "items": _cart(product, "2"),
        },
        user=user,
    )
    from apps.sales.services.refund_service import RefundService

    RefundService.refund_invoice(
        invoice_id=result["invoice"]["id"],
        items=[{"product_id": str(product.id), "quantity": "1"}],
        reason="Return",
        user=user,
    )
    refund_journal = JournalEntry.active_objects().filter(source_module="sales").order_by("-created_at").first()
    assert refund_journal.source_type == "refund"
    data = JournalService.serialize(refund_journal)
    assert data["is_balanced"] is True
    assert data["total_debit"] == 14.0  # return 10 + COGS restore 4

    event = AccountingEvent.active_objects().get(event_type="SALE_REFUNDED")
    assert event.status == AccountingEvent.STATUS_POSTED
