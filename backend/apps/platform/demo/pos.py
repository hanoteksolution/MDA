"""POS demo seeder — catalog plus a completed cash ticket."""

from __future__ import annotations

from apps.customers.models import Customer
from apps.platform.demo import catalog as catalog_demo
from apps.products.models import Product
from apps.sales.models import Invoice
from apps.sales.services.sales_service import InvoiceService
from apps.settings_app.models import Branch
from core.tenancy import tenant_context

DEMO_POS_KEY = "demo-pos-seed-v1"


def seed(*, tenant, user=None, module_code: str = "retail") -> dict:
    catalog = catalog_demo.seed(tenant=tenant, user=user, module_code=module_code)
    with tenant_context(tenant, enforce=True):
        branch = (
            Branch.active_objects().filter(tenant=tenant, is_default=True).first()
            or Branch.active_objects().filter(tenant=tenant).first()
        )
        walkin = Customer.active_objects().filter(
            tenant=tenant, full_name__iexact="Walk-in Customer"
        ).first()
        water = Product.active_objects().filter(tenant=tenant, sku="DEMO-POS-WATER").first()
        snack = Product.active_objects().filter(tenant=tenant, sku="DEMO-POS-SNACK").first()
        if branch is None or walkin is None or water is None or snack is None:
            return {**catalog, "pos": {"seeded": False, "reason": "catalog missing"}}

        existing = Invoice.active_objects().filter(
            tenant=tenant, idempotency_key=DEMO_POS_KEY
        ).first()
        if existing is not None:
            return {
                **catalog,
                "pos": {
                    "seeded": True,
                    "idempotent": True,
                    "invoice": existing.invoice_number,
                },
            }

        invoice = InvoiceService.create(
            data={
                "branch_id": branch.id,
                "customer_id": walkin.id,
                "status": Invoice.STATUS_PAID,
                "notes": "Payment: cash | Waiter: Demo Cashier | Demo POS seed sale",
                "idempotency_key": DEMO_POS_KEY,
            },
            items=[
                {
                    "product_id": water.id,
                    "quantity": 2,
                    "unit_price": water.selling_price,
                },
                {
                    "product_id": snack.id,
                    "quantity": 1,
                    "unit_price": snack.selling_price,
                },
            ],
            user=user,
        )
        if invoice.amount_paid == 0:
            invoice.amount_paid = invoice.total_amount
            invoice.save(update_fields=["amount_paid", "updated_at"])
        return {
            **catalog,
            "pos": {
                "seeded": True,
                "invoice": invoice.invoice_number,
                "total": str(invoice.total_amount),
                "module_code": module_code,
            },
        }
