"""Purchases demo seeder — supplier purchase order on catalog items."""

from __future__ import annotations

from decimal import Decimal

from apps.platform.demo import catalog as catalog_demo
from apps.products.models import Product
from apps.purchases.models import PurchaseOrder
from apps.purchases.services.purchase_service import PurchaseOrderService
from apps.settings_app.models import Branch
from apps.suppliers.models import Supplier
from core.tenancy import tenant_context

DEMO_NOTE = "Demo seed purchase order"


def seed(*, tenant, user=None, module_code: str = "retail") -> dict:
    catalog = catalog_demo.seed(tenant=tenant, user=user, module_code=module_code)
    with tenant_context(tenant, enforce=True):
        branch = (
            Branch.active_objects().filter(tenant=tenant, is_default=True).first()
            or Branch.active_objects().filter(tenant=tenant).first()
        )
        supplier = Supplier.active_objects().filter(
            tenant=tenant, supplier_code="SUP-DEMO-01"
        ).first()
        product = Product.active_objects().filter(tenant=tenant, sku="DEMO-POS-TOWEL").first()
        if branch is None or supplier is None or product is None:
            return {**catalog, "purchases": {"seeded": False, "reason": "catalog missing"}}

        existing = PurchaseOrder.active_objects().filter(tenant=tenant, notes=DEMO_NOTE).first()
        if existing is not None:
            return {
                **catalog,
                "purchases": {
                    "seeded": True,
                    "idempotent": True,
                    "order": existing.order_number,
                },
            }

        order = PurchaseOrderService.create(
            data={
                "supplier_id": str(supplier.id),
                "branch_id": str(branch.id),
                "status": PurchaseOrder.STATUS_ORDERED,
                "notes": DEMO_NOTE,
            },
            items=[
                {
                    "product_id": str(product.id),
                    "quantity_ordered": Decimal("12"),
                    "unit_cost": product.cost_price,
                }
            ],
            user=user,
        )
        return {
            **catalog,
            "purchases": {
                "seeded": True,
                "order": order.order_number,
                "supplier": supplier.company_name,
            },
        }
