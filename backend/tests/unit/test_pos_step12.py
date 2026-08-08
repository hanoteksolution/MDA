"""STEP 12 — POS hold reserve, split payments, idempotency."""

from decimal import Decimal

import pytest

from apps.customers.models import Customer
from apps.inventory.models import Inventory, Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.platform.models import Tenant
from apps.products.models import Category, Product, Unit
from apps.sales.models import Invoice, Payment
from apps.sales.services.pos_service import PosService
from apps.sales.services.sales_service import InvoiceService
from apps.settings_app.models import Branch, Company


@pytest.fixture
def pos_env(db):
    tenant = Tenant.objects.create(name="POS Co", slug="pos-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="POS Co", tenant=tenant)
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
        sku="POS-1",
        name="Hold Item",
        category=category,
        unit=unit,
        cost_price=Decimal("1"),
        selling_price=Decimal("10"),
    )
    inv = InventoryService.ensure_inventory_record(product=product, warehouse=warehouse)
    inv.quantity = Decimal("10")
    inv.reserved_quantity = Decimal("0")
    inv.tenant_id = tenant.id
    inv.save(update_fields=["quantity", "reserved_quantity", "tenant_id", "updated_at"])
    customer = Customer.objects.create(
        tenant=tenant,
        customer_code="WALK",
        full_name="Walk-in Customer",
        branch=branch,
    )
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="pos_cashier",
        password="pass12345",
        tenant=tenant,
        branch=branch,
    )
    return {
        "tenant": tenant,
        "branch": branch,
        "warehouse": warehouse,
        "product": product,
        "customer": customer,
        "user": user,
        "inv": inv,
    }


def _cart(product, qty="2"):
    return [
        {
            "product_id": str(product.id),
            "quantity": qty,
            "unit_price": "10",
        }
    ]


@pytest.mark.django_db
def test_hold_reserves_without_reducing_on_hand(pos_env):
    product = pos_env["product"]
    user = pos_env["user"]
    inv = Inventory.active_objects().get(product=product, warehouse=pos_env["warehouse"])
    before_qty = inv.quantity

    invoice = PosService.hold(
        data={
            "branch_id": str(pos_env["branch"].id),
            "customer_id": "walkin",
            "waiter_name": "Alex",
            "items": _cart(product, "3"),
        },
        user=user,
    )
    inv.refresh_from_db()
    assert inv.quantity == before_qty
    assert inv.reserved_quantity == Decimal("3")
    assert invoice["status"] == Invoice.STATUS_ON_HOLD


@pytest.mark.django_db
def test_hold_cannot_reserve_beyond_available(pos_env):
    with pytest.raises(ValueError, match="Insufficient available"):
        PosService.hold(
            data={
                "branch_id": str(pos_env["branch"].id),
                "customer_id": "walkin",
                "waiter_name": "Alex",
                "items": _cart(pos_env["product"], "99"),
            },
            user=pos_env["user"],
        )


@pytest.mark.django_db
def test_checkout_from_hold_consumes_reserve_once(pos_env):
    product = pos_env["product"]
    user = pos_env["user"]
    held = PosService.hold(
        data={
            "branch_id": str(pos_env["branch"].id),
            "customer_id": "walkin",
            "waiter_name": "Alex",
            "items": _cart(product, "2"),
        },
        user=user,
    )
    inv = Inventory.active_objects().get(product=product, warehouse=pos_env["warehouse"])
    assert inv.reserved_quantity == Decimal("2")
    assert inv.quantity == Decimal("10")

    result = PosService.checkout(
        data={
            "branch_id": str(pos_env["branch"].id),
            "customer_id": "walkin",
            "waiter_name": "Alex",
            "payment_method": "cash",
            "hold_invoice_id": held["id"],
            "items": _cart(product, "2"),
        },
        user=user,
    )
    inv.refresh_from_db()
    assert inv.reserved_quantity == Decimal("0")
    assert inv.quantity == Decimal("8")
    assert result["invoice"]["status"] == Invoice.STATUS_PAID


@pytest.mark.django_db
def test_cancel_hold_releases_reserve(pos_env):
    product = pos_env["product"]
    user = pos_env["user"]
    held = PosService.hold(
        data={
            "branch_id": str(pos_env["branch"].id),
            "customer_id": "walkin",
            "waiter_name": "Alex",
            "items": _cart(product, "4"),
        },
        user=user,
    )
    invoice = Invoice.objects.get(pk=held["id"])
    InvoiceService.delete(instance=invoice, user=user)
    inv = Inventory.active_objects().get(product=product, warehouse=pos_env["warehouse"])
    assert inv.reserved_quantity == Decimal("0")
    assert inv.quantity == Decimal("10")


@pytest.mark.django_db
def test_split_payment_creates_payment_rows(pos_env):
    product = pos_env["product"]
    user = pos_env["user"]
    result = PosService.checkout(
        data={
            "branch_id": str(pos_env["branch"].id),
            "customer_id": "walkin",
            "waiter_name": "Alex",
            "payment_method": "split",
            "items": _cart(product, "2"),  # total 20
            "payments": [
                {"method": "cash", "amount": "12"},
                {"method": "mobile", "amount": "8", "reference": "MM-1"},
            ],
        },
        user=user,
    )
    invoice_id = result["invoice"]["id"]
    rows = list(Payment.objects.filter(invoice_id=invoice_id).order_by("method"))
    assert len(rows) == 2
    assert {r.method for r in rows} == {"cash", "mobile"}
    assert sum((r.amount for r in rows), Decimal("0")) == Decimal("20.00")


@pytest.mark.django_db
def test_checkout_idempotency_replays(pos_env):
    product = pos_env["product"]
    user = pos_env["user"]
    payload = {
        "branch_id": str(pos_env["branch"].id),
        "customer_id": "walkin",
        "waiter_name": "Alex",
        "payment_method": "cash",
        "items": _cart(product, "1"),
        "idempotency_key": "pos-key-abc",
    }
    first = PosService.checkout(data=payload, user=user)
    second = PosService.checkout(data=payload, user=user)
    assert first["invoice"]["id"] == second["invoice"]["id"]
    assert second.get("idempotent_replay") is True
    assert Invoice.objects.filter(idempotency_key="pos-key-abc").count() == 1
    inv = Inventory.active_objects().get(product=product, warehouse=pos_env["warehouse"])
    assert inv.quantity == Decimal("9")
