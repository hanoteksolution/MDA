"""STEP 12b — cashier sessions + sale refunds foundation."""

from decimal import Decimal

import pytest

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Role
from apps.customers.models import Customer
from apps.inventory.models import Inventory, Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.platform.models import Tenant
from apps.platform.services.module_service import sync_tenant_modules
from apps.products.models import Category, Product, Unit
from apps.sales.models import CashierSession, Invoice
from apps.sales.services.cashier_session_service import CashierSessionError, CashierSessionService
from apps.sales.services.pos_service import PosService
from apps.sales.services.refund_service import RefundError, RefundService
from apps.settings_app.models import Branch, Company


@pytest.fixture
def pos_session_env(db):
    bootstrap_roles_and_permissions()
    tenant = Tenant.objects.create(name="Session Co", slug="session-co", status=Tenant.STATUS_ACTIVE)
    sync_tenant_modules(tenant=tenant, enabled_codes=["pos", "inventory", "sales"])
    company = Company.objects.create(name="Session Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="Main", code="MAIN", is_default=True
    )
    warehouse = Warehouse.objects.create(
        branch=branch, tenant=tenant, name="Main WH", code="WH1", is_default=True
    )
    category = Category.objects.create(name="General", tenant=tenant)
    unit = Unit.objects.create(name="Piece", abbreviation="pc", tenant=tenant)
    product = Product.objects.create(
        tenant=tenant,
        sku="SES-1",
        name="Session Item",
        category=category,
        unit=unit,
        cost_price=Decimal("1"),
        selling_price=Decimal("10"),
    )
    inv = InventoryService.ensure_inventory_record(product=product, warehouse=warehouse)
    inv.quantity = Decimal("20")
    inv.reserved_quantity = Decimal("0")
    inv.tenant_id = tenant.id
    inv.save(update_fields=["quantity", "reserved_quantity", "tenant_id", "updated_at"])
    Customer.objects.create(
        tenant=tenant,
        customer_code="WALK",
        full_name="Walk-in Customer",
        branch=branch,
    )
    from django.contrib.auth import get_user_model

    User = get_user_model()
    role = Role.objects.get(slug="cashier")
    user = User.objects.create_user(
        username="session_cashier",
        password="pass12345",
        tenant=tenant,
        branch=branch,
        role=role,
    )
    return {
        "tenant": tenant,
        "branch": branch,
        "warehouse": warehouse,
        "product": product,
        "user": user,
        "inv": inv,
    }


def _cart(product, qty="1"):
    return [{"product_id": str(product.id), "quantity": qty, "unit_price": "10"}]


@pytest.mark.django_db
def test_open_and_close_cashier_session(pos_session_env):
    user = pos_session_env["user"]
    branch = pos_session_env["branch"]

    session = CashierSessionService.open_session(
        user=user, branch_id=str(branch.id), opening_float="50"
    )
    assert session.status == CashierSession.STATUS_OPEN

    with pytest.raises(CashierSessionError, match="already open"):
        CashierSessionService.open_session(user=user, branch_id=str(branch.id))

    PosService.checkout(
        data={
            "branch_id": str(branch.id),
            "customer_id": "walkin",
            "waiter_name": "Alex",
            "payment_method": "cash",
            "items": _cart(pos_session_env["product"]),
            "cashier_session_id": str(session.id),
        },
        user=user,
    )

    closed = CashierSessionService.close_session(
        session_id=session.id,
        user=user,
        closing_cash_counted="60",
    )
    assert closed.status == CashierSession.STATUS_CLOSED
    assert closed.total_sales == Decimal("10.00")
    assert closed.expected_cash == Decimal("60.00")
    assert closed.cash_variance == Decimal("0.00")


@pytest.mark.django_db
def test_refund_restores_stock(pos_session_env):
    user = pos_session_env["user"]
    branch = pos_session_env["branch"]
    product = pos_session_env["product"]
    inv = pos_session_env["inv"]

    result = PosService.checkout(
        data={
            "branch_id": str(branch.id),
            "customer_id": "walkin",
            "waiter_name": "Alex",
            "payment_method": "cash",
            "items": _cart(product, "3"),
        },
        user=user,
    )
    invoice_id = result["invoice"]["id"]
    inv.refresh_from_db()
    assert inv.quantity == Decimal("17")

    RefundService.refund_invoice(
        invoice_id=invoice_id,
        items=[{"product_id": str(product.id), "quantity": "2"}],
        reason="Customer return",
        user=user,
    )
    inv.refresh_from_db()
    assert inv.quantity == Decimal("19")

    invoice = Invoice.objects.get(pk=invoice_id)
    assert invoice.amount_refunded == Decimal("20.00")


@pytest.mark.django_db
def test_refund_blocks_over_refund(pos_session_env):
    user = pos_session_env["user"]
    branch = pos_session_env["branch"]
    product = pos_session_env["product"]

    result = PosService.checkout(
        data={
            "branch_id": str(branch.id),
            "customer_id": "walkin",
            "waiter_name": "Alex",
            "payment_method": "cash",
            "items": _cart(product, "1"),
        },
        user=user,
    )
    with pytest.raises(RefundError, match="remaining"):
        RefundService.refund_invoice(
            invoice_id=result["invoice"]["id"],
            items=[{"product_id": str(product.id), "quantity": "5"}],
            user=user,
        )
