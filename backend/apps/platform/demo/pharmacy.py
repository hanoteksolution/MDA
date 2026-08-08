"""Pharmacy demo seeder — medicines, FEFO batches, and sample prescriptions."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.inventory.models import Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.pharmacy.models import Prescription, ProductBatch
from apps.pharmacy.services.batch_service import BatchService
from apps.pharmacy.services.prescription_service import PrescriptionService
from apps.products.models import Category, Product, Unit
from core.tenancy import tenant_context

DEMO_SKU_PREFIX = "DEMO-RX-"
DEMO_RX_NUMBER_PREFIX = "DEMO-RX-"

DEMO_CATEGORY_ANALGESICS = "Analgesics"
DEMO_CATEGORY_ANTIBIOTICS = "Antibiotics"

DEMO_MEDS = (
    {
        "sku": "DEMO-RX-PARA500",
        "name": "Paracetamol 500mg",
        "category": DEMO_CATEGORY_ANALGESICS,
        "cost_price": "0.40",
        "selling_price": "1.00",
        "batches": [
            {"batch_number": "PARA-NEAR", "days": 12, "qty": "40"},
            {"batch_number": "PARA-FAR", "days": 180, "qty": "120"},
        ],
    },
    {
        "sku": "DEMO-RX-AMOX250",
        "name": "Amoxicillin 250mg",
        "category": DEMO_CATEGORY_ANTIBIOTICS,
        "cost_price": "0.80",
        "selling_price": "2.50",
        "requires_prescription": True,
        "batches": [
            {"batch_number": "AMOX-A", "days": 60, "qty": "80"},
            {"batch_number": "AMOX-EXP", "days": -5, "qty": "10"},
        ],
    },
    {
        "sku": "DEMO-RX-IBU400",
        "name": "Ibuprofen 400mg",
        "category": DEMO_CATEGORY_ANALGESICS,
        "cost_price": "0.55",
        "selling_price": "1.75",
        "batches": [
            {"batch_number": "IBU-1", "days": 90, "qty": "100"},
        ],
    },
)

DEMO_PRESCRIPTIONS = (
    {
        "rx_number": "DEMO-RX-001",
        "patient_name": "Amina Hassan",
        "patient_phone": "+252610000001",
        "prescribed_by": "Dr. Omar Ali",
        "lines": [
            {
                "sku": "DEMO-RX-AMOX250",
                "quantity": "21",
                "dosage": "1 cap",
                "frequency": "TID",
                "instructions": "After meals — demo Rx",
            },
        ],
    },
    {
        "rx_number": "DEMO-RX-002",
        "patient_name": "Hassan Nur",
        "patient_phone": "+252610000002",
        "prescribed_by": "Dr. Sara Yusuf",
        "lines": [
            {
                "sku": "DEMO-RX-AMOX250",
                "quantity": "14",
                "dosage": "1 cap",
                "frequency": "BID",
            },
            {
                "drug_name": "Cough syrup (demo free-text)",
                "quantity": "1",
                "dosage": "10ml",
                "frequency": "TID",
            },
        ],
    },
    {
        "rx_number": "DEMO-RX-003",
        "patient_name": "Leyla Mohamed",
        "patient_phone": "+252610000003",
        "prescribed_by": "Dr. Omar Ali",
        "lines": [
            {
                "sku": "DEMO-RX-IBU400",
                "quantity": "20",
                "dosage": "1 tab",
                "frequency": "TID",
                "instructions": "With food — demo analgesics Rx",
            },
        ],
    },
)


def _ensure_category(*, tenant, user, name: str) -> Category:
    category = Category.active_objects().filter(tenant=tenant, name=name).first()
    if category is None:
        category = Category.objects.create(name=name, tenant=tenant, created_by=user)
    return category


def _seed_medicines(*, tenant, user, warehouse) -> dict:
    categories = {
        DEMO_CATEGORY_ANALGESICS: _ensure_category(
            tenant=tenant, user=user, name=DEMO_CATEGORY_ANALGESICS
        ),
        DEMO_CATEGORY_ANTIBIOTICS: _ensure_category(
            tenant=tenant, user=user, name=DEMO_CATEGORY_ANTIBIOTICS
        ),
    }

    unit = Unit.active_objects().filter(tenant=tenant, abbreviation="tab").first()
    if unit is None:
        unit = Unit.objects.create(
            name="Tablet",
            abbreviation="tab",
            tenant=tenant,
            created_by=user,
        )

    today = timezone.localdate()
    products_n = 0
    batches_n = 0
    created_products = 0
    created_batches = 0

    for med in DEMO_MEDS:
        category = categories[med["category"]]
        product = Product.active_objects().filter(
            tenant=tenant, sku=med["sku"]
        ).first()
        if product is None:
            product = Product.objects.create(
                tenant=tenant,
                sku=med["sku"],
                name=med["name"],
                category=category,
                unit=unit,
                cost_price=Decimal(med["cost_price"]),
                selling_price=Decimal(med["selling_price"]),
                minimum_stock=20,
                is_active=True,
                requires_prescription=bool(med.get("requires_prescription")),
                created_by=user,
            )
            created_products += 1
        else:
            updates = []
            if product.category_id != category.id:
                product.category = category
                updates.append("category")
            if bool(med.get("requires_prescription")) and not product.requires_prescription:
                product.requires_prescription = True
                updates.append("requires_prescription")
            if updates:
                product.updated_by = user
                product.save(update_fields=[*updates, "updated_by", "updated_at"])
        products_n += 1

        inv = InventoryService.ensure_inventory_record(
            product=product, warehouse=warehouse, user=user
        )
        total_qty = Decimal("0")
        for b in med["batches"]:
            qty = Decimal(b["qty"])
            expiry = today + timedelta(days=int(b["days"]))
            existing = ProductBatch.active_objects().filter(
                tenant=tenant,
                product=product,
                warehouse=warehouse,
                batch_number=b["batch_number"],
            ).first()
            if existing is None:
                BatchService.receive_stock(
                    product=product,
                    warehouse=warehouse,
                    quantity=qty,
                    batch_number=b["batch_number"],
                    expiry_date=expiry,
                    cost_price=Decimal(med["cost_price"]),
                    user=user,
                    notes="Demo seed batch",
                )
                created_batches += 1
            batches_n += 1
            total_qty += Decimal(str(existing.quantity if existing else qty))

        # Align on-hand with sum of batch qtys when we just created or batches exist
        batch_sum = (
            ProductBatch.active_objects()
            .filter(product=product, warehouse=warehouse, is_active=True)
            .values_list("quantity", flat=True)
        )
        aligned = sum((Decimal(str(q)) for q in batch_sum), Decimal("0"))
        if aligned > 0:
            inv.quantity = aligned
            inv.updated_by = user
            inv.save(update_fields=["quantity", "updated_by", "updated_at"])
        elif total_qty > 0:
            inv.quantity = total_qty
            inv.updated_by = user
            inv.save(update_fields=["quantity", "updated_by", "updated_at"])

    return {
        "products": products_n,
        "batches": batches_n,
        "created_products": created_products,
        "created_batches": created_batches,
    }


def _seed_prescriptions(*, tenant, user) -> dict:
    created = 0
    for row in DEMO_PRESCRIPTIONS:
        rx_number = row["rx_number"]
        if (
            Prescription.active_objects()
            .filter(tenant=tenant, rx_number=rx_number)
            .exists()
        ):
            continue

        lines = []
        for line in row["lines"]:
            payload = {
                "drug_name": line.get("drug_name") or "",
                "dosage": line.get("dosage") or "",
                "frequency": line.get("frequency") or "",
                "quantity": line.get("quantity") or 1,
                "instructions": line.get("instructions") or "",
            }
            sku = line.get("sku")
            if sku:
                product = Product.active_objects().filter(tenant=tenant, sku=sku).first()
                if product is not None:
                    payload["product_id"] = str(product.id)
                    if not payload["drug_name"]:
                        payload["drug_name"] = product.name
            if not payload["drug_name"]:
                continue
            lines.append(payload)

        if not lines:
            continue

        PrescriptionService.create(
            data={
                "tenant_id": tenant.id,
                "rx_number": rx_number,
                "patient_name": row["patient_name"],
                "patient_phone": row.get("patient_phone") or "",
                "prescribed_by": row.get("prescribed_by") or "",
                "prescribed_at": timezone.localdate().isoformat(),
                "status": Prescription.STATUS_ACTIVE,
                "notes": "Demo seed prescription",
                "lines": lines,
            },
            user=user,
        )
        created += 1

    total = Prescription.active_objects().filter(
        tenant=tenant, rx_number__startswith=DEMO_RX_NUMBER_PREFIX
    ).count()
    return {"prescriptions": total, "created_prescriptions": created}


def seed(*, tenant, user=None) -> dict:
    """Create sample pharmacy products, batches, and Rx. Idempotent on DEMO keys."""
    with tenant_context(tenant, enforce=True):
        warehouse = (
            Warehouse.active_objects()
            .filter(tenant=tenant, is_default=True)
            .first()
            or Warehouse.active_objects().filter(tenant=tenant).first()
        )
        if warehouse is None:
            return {
                "pharmacy": {
                    "seeded": False,
                    "reason": "no warehouse — provision shop first",
                }
            }

        meds = _seed_medicines(tenant=tenant, user=user, warehouse=warehouse)
        rxs = _seed_prescriptions(tenant=tenant, user=user)
        summary = BatchService.summary(user=user)

        fully_present = (
            meds["products"] >= len(DEMO_MEDS)
            and meds["created_products"] == 0
            and meds["created_batches"] == 0
            and rxs["created_prescriptions"] == 0
            and rxs["prescriptions"] >= len(DEMO_PRESCRIPTIONS)
        )

        return {
            "pharmacy": {
                "seeded": True,
                "idempotent": fully_present,
                "products": meds["products"],
                "batches": meds["batches"],
                "prescriptions": rxs["prescriptions"],
                "created_products": meds["created_products"],
                "created_batches": meds["created_batches"],
                "created_prescriptions": rxs["created_prescriptions"],
                "batch_count": summary.get("batch_count"),
                "expiring_count": summary.get("expiring_count"),
                "expired_count": summary.get("expired_count"),
                "prescriptions_active": summary.get("prescriptions_active"),
            }
        }
