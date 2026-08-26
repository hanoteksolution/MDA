"""Sales demo seeder — named-customer invoice on catalog stock."""

from __future__ import annotations

from apps.customers.models import Customer
from apps.platform.demo import catalog as catalog_demo
from apps.products.models import Product
from apps.sales.models import Invoice
from apps.sales.services.sales_service import InvoiceService
from apps.settings_app.models import Branch
from core.tenancy import tenant_context

DEMO_NOTE = "Demo seed invoice"


def seed(*, tenant, user=None, module_code: str = "retail") -> dict:
    catalog = catalog_demo.seed(tenant=tenant, user=user, module_code=module_code)
    with tenant_context(tenant, enforce=True):
        branch = (
            Branch.active_objects().filter(tenant=tenant, is_default=True).first()
            or Branch.active_objects().filter(tenant=tenant).first()
        )
        customer = Customer.active_objects().filter(
            tenant=tenant, customer_code="CUST-DEMO-01"
        ).first()
        product = Product.active_objects().filter(tenant=tenant, sku="DEMO-POS-SHAKE").first()
        if branch is None or customer is None or product is None:
            return {**catalog, "sales": {"seeded": False, "reason": "catalog missing"}}

        existing = Invoice.active_objects().filter(tenant=tenant, notes=DEMO_NOTE).first()
        if existing is not None:
            return {
                **catalog,
                "sales": {
                    "seeded": True,
                    "idempotent": True,
                    "invoice": existing.invoice_number,
                },
            }

        invoice = InvoiceService.create(
            data={
                "branch_id": branch.id,
                "customer_id": customer.id,
                "status": Invoice.STATUS_SENT,
                "notes": DEMO_NOTE,
            },
            items=[
                {
                    "product_id": product.id,
                    "quantity": 1,
                    "unit_price": product.selling_price,
                }
            ],
            user=user,
        )
        return {
            **catalog,
            "sales": {
                "seeded": True,
                "invoice": invoice.invoice_number,
                "customer": customer.full_name,
            },
        }
