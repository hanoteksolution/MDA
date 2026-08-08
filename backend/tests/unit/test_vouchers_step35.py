"""STEP 35 Phase J — customer receipts + supplier payments settle AR/AP."""

from decimal import Decimal

import pytest

from apps.customers.models import Customer
from apps.finance.models import AccountingEvent, JournalEntry
from apps.finance.selectors.payables import PayablesAgingSelector
from apps.finance.selectors.receivables import ReceivablesAgingSelector
from apps.finance.services.chart_service import ChartService
from apps.finance.services.journal_service import JournalService
from apps.finance.services.voucher_service import VoucherError, VoucherService
from apps.inventory.models import Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.inventory.services.receiving_service import PurchaseReceivingService, ReceiveLineInput
from apps.platform.models import Tenant
from apps.products.models import Category, Product, Unit
from apps.purchases.models import PurchaseOrder, PurchaseOrderItem
from apps.sales.models import Invoice
from apps.sales.services.pos_service import PosService
from apps.settings_app.models import Branch, Company
from apps.suppliers.models import Supplier
from core.tenancy import tenant_context
from django.utils import timezone


@pytest.fixture
def voucher_env(db):
    tenant = Tenant.objects.create(name="Voucher Co", slug="voucher-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="Voucher Co", tenant=tenant)
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
        sku="V-1",
        name="Voucher Item",
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
        tenant=tenant, supplier_code="SUP-V", company_name="Supply Co"
    )
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="voucher_user", password="pass12345", tenant=tenant, branch=branch
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
def test_customer_receipt_settles_ar(voucher_env):
    user = voucher_env["user"]
    product = voucher_env["product"]
    customer = voucher_env["registered"]
    tenant = voucher_env["tenant"]

    result = PosService.checkout(
        data={
            "branch_id": str(voucher_env["branch"].id),
            "customer_id": str(customer.id),
            "waiter_name": "Alex",
            "payment_method": "on_account",
            "items": [
                {"product_id": str(product.id), "quantity": "1", "unit_price": "20"}
            ],
        },
        user=user,
    )
    invoice_id = result["invoice"]["id"]

    with tenant_context(tenant, enforce=True):
        before = ReceivablesAgingSelector.run()
        assert before["totals"]["outstanding"] == 20.0
        assert before["reconciled"] is True

        payment = VoucherService.record_customer_receipt(
            invoice_id=invoice_id,
            amount="20",
            method="cash",
            reference="RCP-1",
            user=user,
        )

        after = ReceivablesAgingSelector.run()
        assert after["totals"]["outstanding"] == 0.0
        assert after["reconciled"] is True

    inv = Invoice.objects.get(pk=invoice_id)
    assert inv.status == Invoice.STATUS_PAID
    assert Decimal(str(inv.amount_paid)) == Decimal("20.00")

    event = AccountingEvent.active_objects().get(
        event_type="CUSTOMER_PAYMENT_RECEIVED", source_id=payment.id
    )
    assert event.status == AccountingEvent.STATUS_POSTED
    journal = JournalEntry.active_objects().get(pk=event.journal_entry_id)
    data = JournalService.serialize(journal)
    assert data["is_balanced"] is True
    assert data["source_type"] == JournalEntry.SOURCE_PAYMENT
    assert data["total_debit"] == 20.0


@pytest.mark.django_db
def test_customer_receipt_rejects_overpay(voucher_env):
    user = voucher_env["user"]
    product = voucher_env["product"]
    customer = voucher_env["registered"]

    result = PosService.checkout(
        data={
            "branch_id": str(voucher_env["branch"].id),
            "customer_id": str(customer.id),
            "waiter_name": "Alex",
            "payment_method": "on_account",
            "items": [
                {"product_id": str(product.id), "quantity": "1", "unit_price": "20"}
            ],
        },
        user=user,
    )
    with pytest.raises(VoucherError, match="exceeds"):
        VoucherService.record_customer_receipt(
            invoice_id=result["invoice"]["id"],
            amount="25",
            method="cash",
            user=user,
        )


@pytest.mark.django_db
def test_supplier_payment_settles_ap(voucher_env):
    tenant = voucher_env["tenant"]
    product = voucher_env["product"]
    supplier = voucher_env["supplier"]
    branch = voucher_env["branch"]
    warehouse = voucher_env["warehouse"]
    user = voucher_env["user"]

    po = PurchaseOrder.objects.create(
        tenant=tenant,
        order_number="PO-V-1",
        supplier=supplier,
        branch=branch,
        status=PurchaseOrder.STATUS_ORDERED,
        order_date=timezone.localdate(),
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
        user=user,
    )

    with tenant_context(tenant, enforce=True):
        before = PayablesAgingSelector.run()
        assert before["totals"]["outstanding"] == 20.0
        assert before["reconciled"] is True

        payment = VoucherService.record_supplier_payment(
            purchase_order_id=po.id,
            amount="12",
            method="bank",
            reference="SP-1",
            user=user,
        )
        mid = PayablesAgingSelector.run()
        assert mid["totals"]["outstanding"] == 8.0
        assert mid["reconciled"] is True
        assert mid["rows"][0]["amount_paid"] == 12.0

        VoucherService.record_supplier_payment(
            purchase_order_id=po.id,
            amount="8",
            method="cash",
            user=user,
        )
        after = PayablesAgingSelector.run()
        assert after["totals"]["outstanding"] == 0.0
        assert after["reconciled"] is True
        assert after["rows"] == []

    event = AccountingEvent.active_objects().get(
        event_type="SUPPLIER_PAYMENT_COMPLETED", source_id=payment.id
    )
    assert event.status == AccountingEvent.STATUS_POSTED
    journal = JournalEntry.active_objects().get(pk=event.journal_entry_id)
    data = JournalService.serialize(journal)
    assert data["is_balanced"] is True
    assert data["total_debit"] == 12.0
