"""STEP 35 Phase I — AR / AP aging vs control accounts."""

from datetime import timedelta
from decimal import Decimal

import pytest

from apps.customers.models import Customer
from apps.finance.selectors.payables import PayablesAgingSelector
from apps.finance.selectors.receivables import ReceivablesAgingSelector
from apps.finance.services.chart_service import ChartService
from apps.inventory.models import Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.inventory.services.receiving_service import PurchaseReceivingService, ReceiveLineInput
from apps.platform.models import Tenant
from apps.products.models import Category, Product, Unit
from apps.purchases.models import PurchaseOrder, PurchaseOrderItem
from apps.sales.services.pos_service import PosService
from apps.settings_app.models import Branch, Company
from apps.suppliers.models import Supplier
from core.tenancy import tenant_context
from django.utils import timezone


@pytest.fixture
def aging_env(db):
    tenant = Tenant.objects.create(name="Aging Co", slug="aging-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="Aging Co", tenant=tenant)
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
        sku="AGE-1",
        name="Aging Item",
        category=category,
        unit=unit,
        cost_price=Decimal("5"),
        selling_price=Decimal("20"),
    )
    inv = InventoryService.ensure_inventory_record(product=product, warehouse=warehouse)
    inv.quantity = Decimal("100")
    inv.tenant_id = tenant.id
    inv.save(update_fields=["quantity", "tenant_id", "updated_at"])
    Customer.objects.create(
        tenant=tenant, customer_code="WALK", full_name="Walk-in Customer", branch=branch
    )
    registered = Customer.objects.create(
        tenant=tenant, customer_code="REG", full_name="Credit Customer", branch=branch
    )
    supplier = Supplier.objects.create(
        tenant=tenant, supplier_code="SUP-A", company_name="Supply Co"
    )
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="aging_user", password="pass12345", tenant=tenant, branch=branch
    )
    ChartService.ensure_default_chart(tenant_id=tenant.id)
    return {
        "tenant": tenant,
        "branch": branch,
        "warehouse": warehouse,
        "product": product,
        "user": user,
        "registered": registered,
        "supplier": supplier,
    }


@pytest.mark.django_db
def test_ar_aging_on_account_reconciles(aging_env):
    user = aging_env["user"]
    product = aging_env["product"]
    customer = aging_env["registered"]
    tenant = aging_env["tenant"]

    PosService.checkout(
        data={
            "branch_id": str(aging_env["branch"].id),
            "customer_id": str(customer.id),
            "waiter_name": "Alex",
            "payment_method": "on_account",
            "items": [
                {"product_id": str(product.id), "quantity": "1", "unit_price": "20"}
            ],
        },
        user=user,
    )

    with tenant_context(tenant, enforce=True):
        report = ReceivablesAgingSelector.run()

    assert report["totals"]["outstanding"] == 20.0
    assert report["reconciled"] is True
    assert len(report["rows"]) == 1
    assert report["rows"][0]["balance"] == 20.0


@pytest.mark.django_db
def test_ar_aging_buckets_by_due_date(aging_env):
    user = aging_env["user"]
    product = aging_env["product"]
    customer = aging_env["registered"]
    tenant = aging_env["tenant"]

    result = PosService.checkout(
        data={
            "branch_id": str(aging_env["branch"].id),
            "customer_id": str(customer.id),
            "waiter_name": "Alex",
            "payment_method": "on_account",
            "items": [
                {"product_id": str(product.id), "quantity": "1", "unit_price": "20"}
            ],
        },
        user=user,
    )
    from apps.sales.models import Invoice

    inv = Invoice.objects.get(pk=result["invoice"]["id"])
    inv.due_date = timezone.localdate() - timedelta(days=45)
    inv.save(update_fields=["due_date", "updated_at"])

    with tenant_context(tenant, enforce=True):
        report = ReceivablesAgingSelector.run()

    assert report["buckets"]["31_60"] == 20.0
    assert report["rows"][0]["bucket"] == "31_60"


@pytest.mark.django_db
def test_ap_aging_after_receive_reconciles(aging_env):
    tenant = aging_env["tenant"]
    product = aging_env["product"]
    supplier = aging_env["supplier"]
    branch = aging_env["branch"]
    warehouse = aging_env["warehouse"]

    po = PurchaseOrder.objects.create(
        tenant=tenant,
        order_number="PO-AGE-1",
        supplier=supplier,
        branch=branch,
        status=PurchaseOrder.STATUS_ORDERED,
        order_date=timezone.localdate() - timedelta(days=10),
    )
    PurchaseOrderItem.objects.create(
        purchase_order=po,
        product=product,
        quantity_ordered=Decimal("4"),
        quantity_received=Decimal("0"),
        unit_cost=Decimal("5.00"),
    )
    PurchaseReceivingService.receive(
        purchase_order_id=po.id,
        warehouse_id=warehouse.id,
        lines=[ReceiveLineInput(product_id=product.id, quantity_received=Decimal("4"))],
        user=aging_env["user"],
    )

    with tenant_context(tenant, enforce=True):
        report = PayablesAgingSelector.run()

    assert report["totals"]["outstanding"] == 20.0  # 4 * 5
    assert report["reconciled"] is True
    assert len(report["rows"]) == 1
