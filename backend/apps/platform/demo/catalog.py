"""Shared catalog + partners for POS / inventory / sales / purchases demos."""

from __future__ import annotations

from decimal import Decimal

from apps.customers.models import Customer
from apps.inventory.models import Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.products.models import Brand, Category, Product, Unit
from apps.settings_app.models import Branch
from apps.suppliers.models import Supplier
from core.tenancy import tenant_context

DEMO_SKU_PREFIX = "DEMO-POS-"

DEMO_PRODUCTS = (
    {
        "sku": "DEMO-POS-WATER",
        "barcode": "8900000000011",
        "name": "Bottled Water 500ml",
        "category": "Beverages",
        "brand": "Demo Brand",
        "cost": "0.20",
        "sell": "0.75",
        "qty": "80",
    },
    {
        "sku": "DEMO-POS-SNACK",
        "barcode": "8900000000028",
        "name": "Energy Bar",
        "category": "Snacks",
        "brand": "Demo Brand",
        "cost": "0.40",
        "sell": "1.50",
        "qty": "60",
    },
    {
        "sku": "DEMO-POS-TOWEL",
        "barcode": "8900000000035",
        "name": "Gym Towel",
        "category": "Accessories",
        "brand": "Demo Brand",
        "cost": "2.00",
        "sell": "6.00",
        "qty": "25",
    },
    {
        "sku": "DEMO-POS-SHAKE",
        "barcode": "8900000000042",
        "name": "Protein Shake",
        "category": "Beverages",
        "brand": "Demo Brand",
        "cost": "1.20",
        "sell": "4.50",
        "qty": "40",
    },
)


def _branch(*, tenant):
    return (
        Branch.active_objects().filter(tenant=tenant, is_default=True).first()
        or Branch.active_objects().filter(tenant=tenant).first()
    )


def _warehouse(*, tenant, branch):
    if branch is None:
        return None
    return (
        Warehouse.active_objects().filter(tenant=tenant, branch=branch, is_default=True).first()
        or Warehouse.active_objects().filter(tenant=tenant, branch=branch).first()
        or Warehouse.active_objects().filter(tenant=tenant).first()
    )


def seed(*, tenant, user=None, module_code: str = "retail") -> dict:
    """Idempotent catalog, stock, walk-in + named customers, and a supplier."""
    code = (module_code or "retail").strip().lower() or "retail"
    with tenant_context(tenant, enforce=True):
        branch = _branch(tenant=tenant)
        if branch is None:
            return {"catalog": {"seeded": False, "reason": "no branch"}}
        warehouse = _warehouse(tenant=tenant, branch=branch)
        if warehouse is None:
            return {"catalog": {"seeded": False, "reason": "no warehouse"}}

        unit, _ = Unit.objects.get_or_create(
            tenant=tenant,
            abbreviation="pc",
            defaults={"name": "Piece", "is_active": True, "created_by": user},
        )
        brand, _ = Brand.objects.get_or_create(
            tenant=tenant,
            name="Demo Brand",
            defaults={"is_active": True, "created_by": user},
        )

        products = []
        for spec in DEMO_PRODUCTS:
            cat, _ = Category.objects.get_or_create(
                tenant=tenant,
                name=spec["category"],
                defaults={"is_active": True, "created_by": user},
            )
            product = Product.active_objects().filter(tenant=tenant, sku=spec["sku"]).first()
            if product is None:
                product = Product.objects.create(
                    tenant=tenant,
                    sku=spec["sku"],
                    barcode=spec["barcode"],
                    name=spec["name"],
                    category=cat,
                    brand=brand,
                    unit=unit,
                    cost_price=Decimal(spec["cost"]),
                    selling_price=Decimal(spec["sell"]),
                    minimum_stock=5,
                    is_active=True,
                    module_code=code,
                    created_by=user,
                )
            elif (product.module_code or "") != code:
                product.module_code = code
                product.save(update_fields=["module_code", "updated_at"])
            from apps.platform.demo.product_images import ensure_product_image

            ensure_product_image(product)
            inv = InventoryService.ensure_inventory_record(
                product=product, warehouse=warehouse, user=user
            )
            if inv.quantity == 0:
                inv.quantity = Decimal(spec["qty"])
                inv.save(update_fields=["quantity", "updated_at"])
            products.append(product)

        walkin = Customer.active_objects().filter(
            tenant=tenant, full_name__iexact="Walk-in Customer"
        ).first()
        if walkin is None:
            walkin = Customer.objects.create(
                tenant=tenant,
                customer_code="WALKIN-DEMO",
                full_name="Walk-in Customer",
                customer_type="retail",
                branch=branch,
                is_active=True,
                created_by=user,
            )

        named = []
        for code, name, phone in (
            ("CUST-DEMO-01", "Hodan Yusuf", "+252610000201"),
            ("CUST-DEMO-02", "Abdi Warsame", "+252610000202"),
        ):
            row = Customer.active_objects().filter(tenant=tenant, customer_code=code).first()
            if row is None:
                row = Customer.objects.create(
                    tenant=tenant,
                    customer_code=code,
                    full_name=name,
                    phone=phone,
                    customer_type="retail",
                    credit_limit=Decimal("200"),
                    branch=branch,
                    is_active=True,
                    created_by=user,
                )
            named.append(row)

        supplier = Supplier.active_objects().filter(
            tenant=tenant, supplier_code="SUP-DEMO-01"
        ).first()
        if supplier is None:
            supplier = Supplier.objects.create(
                tenant=tenant,
                supplier_code="SUP-DEMO-01",
                company_name="Demo Wholesale",
                contact_person="Demo Buyer",
                phone="+252610000300",
                payment_terms=14,
                is_active=True,
                created_by=user,
            )

        return {
            "catalog": {
                "seeded": True,
                "products": len(products),
                "customers": 1 + len(named),
                "suppliers": 1,
                "warehouse": warehouse.code,
            },
            "inventory": {
                "seeded": True,
                "skus": [p.sku for p in products],
                "on_hand": int(
                    sum(
                        InventoryService.ensure_inventory_record(
                            product=p, warehouse=warehouse, user=user
                        ).quantity
                        for p in products
                    )
                ),
            },
        }
