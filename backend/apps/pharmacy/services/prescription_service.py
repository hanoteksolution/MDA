"""Pharmacy prescription service — thin Rx MVP (PHASE 16)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Prefetch, Q
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.customers.models import Customer
from apps.pharmacy.models import Prescription, PrescriptionLine
from apps.products.models import Product
from apps.settings_app.models import Branch
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class PrescriptionError(ValueError):
    pass


class PrescriptionService:
    @staticmethod
    def list(*, status=None, search=None, category_id=None, user=None, request=None):
        qs = Prescription.active_objects().prefetch_related(
            Prefetch(
                "lines",
                queryset=PrescriptionLine.active_objects().select_related(
                    "product", "product__category"
                ),
            )
        )
        qs = apply_tenant_scope(qs, user=user, request=request)
        if status:
            qs = qs.filter(status=status)
        if category_id:
            qs = qs.filter(lines__product__category_id=category_id).distinct()
        if search:
            qs = qs.filter(
                Q(rx_number__icontains=search)
                | Q(patient_name__icontains=search)
                | Q(patient_phone__icontains=search)
                | Q(prescribed_by__icontains=search)
                | Q(lines__drug_name__icontains=search)
                | Q(lines__product__category__name__icontains=search)
            ).distinct()
        return qs.order_by("-prescribed_at", "-created_at")

    @staticmethod
    def serialize(rx: Prescription) -> dict:
        lines = [
            {
                "id": str(line.id),
                "product_id": str(line.product_id) if line.product_id else None,
                "category_id": str(line.product.category_id)
                if line.product_id and getattr(line.product, "category_id", None)
                else None,
                "category_name": (
                    line.product.category.name
                    if line.product_id and getattr(line.product, "category_id", None)
                    else ""
                ),
                "drug_name": line.drug_name,
                "dosage": line.dosage or "",
                "frequency": line.frequency or "",
                "duration_days": line.duration_days,
                "quantity": float(line.quantity or 0),
                "quantity_dispensed": float(line.quantity_dispensed or 0),
                "quantity_remaining": float(line.quantity_remaining),
                "instructions": line.instructions or "",
                "sort_order": line.sort_order,
            }
            for line in rx.lines.filter(deleted_at__isnull=True)
            .select_related("product", "product__category")
            .order_by("sort_order", "created_at")
        ]
        return {
            "id": str(rx.id),
            "rx_number": rx.rx_number,
            "patient_name": rx.patient_name,
            "patient_phone": rx.patient_phone or "",
            "customer_id": str(rx.customer_id) if rx.customer_id else None,
            "prescribed_by": rx.prescribed_by or "",
            "status": rx.status,
            "prescribed_at": rx.prescribed_at.isoformat() if rx.prescribed_at else None,
            "dispensed_at": rx.dispensed_at.isoformat() if rx.dispensed_at else None,
            "dispensed_by_id": str(rx.dispensed_by_id) if rx.dispensed_by_id else None,
            "branch_id": str(rx.branch_id) if rx.branch_id else None,
            "notes": rx.notes or "",
            "line_count": len(lines),
            "lines": lines,
        }

    @staticmethod
    def _next_rx_number(*, tenant_id) -> str:
        today = timezone.localdate()
        prefix = f"RX-{today.strftime('%Y%m%d')}-"
        existing = (
            Prescription.active_objects()
            .filter(tenant_id=tenant_id, rx_number__startswith=prefix)
            .count()
        )
        return f"{prefix}{existing + 1:04d}"

    @staticmethod
    @transaction.atomic
    def create(*, data, user=None, request=None) -> Prescription:
        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id") or data.get("tenant_id")
        if data.get("tenant"):
            tenant_id = getattr(data["tenant"], "pk", None) or tenant_id
        if not tenant_id:
            raise PrescriptionError("Tenant required.")

        patient_name = (data.get("patient_name") or "").strip()
        if not patient_name:
            raise PrescriptionError("patient_name is required.")

        prescribed_at = data.get("prescribed_at") or timezone.localdate()
        if isinstance(prescribed_at, str):
            prescribed_at = parse_date(prescribed_at) or timezone.localdate()
        if not isinstance(prescribed_at, date):
            prescribed_at = timezone.localdate()

        rx_number = (data.get("rx_number") or "").strip().upper()
        if not rx_number:
            rx_number = PrescriptionService._next_rx_number(tenant_id=tenant_id)
        if (
            Prescription.active_objects()
            .filter(tenant_id=tenant_id, rx_number=rx_number)
            .exists()
        ):
            raise PrescriptionError(f"Rx number '{rx_number}' already exists.")

        status = (data.get("status") or Prescription.STATUS_ACTIVE).strip().lower()
        valid = {c[0] for c in Prescription.STATUS_CHOICES}
        if status not in valid:
            raise PrescriptionError(f"Invalid status: {status}")

        customer = None
        if data.get("customer_id"):
            customer = apply_tenant_scope(
                Customer.active_objects(), user=user, request=request
            ).filter(pk=data["customer_id"]).first()
            if customer is None:
                raise PrescriptionError("Customer not found.")

        branch = None
        if data.get("branch_id"):
            branch = apply_tenant_scope(
                Branch.active_objects(), user=user, request=request
            ).filter(pk=data["branch_id"]).first()

        rx = Prescription.objects.create(
            tenant_id=tenant_id,
            rx_number=rx_number,
            patient_name=patient_name,
            patient_phone=(data.get("patient_phone") or "").strip(),
            customer=customer,
            prescribed_by=(data.get("prescribed_by") or "").strip(),
            status=status,
            prescribed_at=prescribed_at,
            branch=branch,
            notes=data.get("notes") or "",
            created_by=user,
        )

        lines_data = data.get("lines") or []
        if not lines_data:
            # Allow single free-text drug shortcut
            if data.get("drug_name") or data.get("product_id"):
                lines_data = [
                    {
                        "drug_name": data.get("drug_name"),
                        "product_id": data.get("product_id"),
                        "dosage": data.get("dosage") or "",
                        "frequency": data.get("frequency") or "",
                        "quantity": data.get("quantity") or 1,
                        "instructions": data.get("instructions") or "",
                    }
                ]
        if not lines_data:
            raise PrescriptionError("At least one prescription line is required.")

        for idx, row in enumerate(lines_data):
            drug_name = (row.get("drug_name") or "").strip()
            product = None
            if row.get("product_id"):
                product = apply_tenant_scope(
                    Product.active_objects(), user=user, request=request
                ).filter(pk=row["product_id"]).first()
                if product is None:
                    raise PrescriptionError("Product not found on line.")
                if not drug_name:
                    drug_name = product.name
            if not drug_name:
                raise PrescriptionError("drug_name is required on each line.")
            PrescriptionLine.objects.create(
                prescription=rx,
                product=product,
                drug_name=drug_name,
                dosage=(row.get("dosage") or "").strip(),
                frequency=(row.get("frequency") or "").strip(),
                duration_days=row.get("duration_days") or None,
                quantity=Decimal(str(row.get("quantity") or 1)),
                instructions=(row.get("instructions") or "").strip(),
                sort_order=int(row.get("sort_order") or idx),
                created_by=user,
            )

        return rx

    @staticmethod
    def _resolve_warehouse(*, warehouse_id=None, user=None, request=None, branch=None):
        from apps.inventory.models import Warehouse

        qs = apply_tenant_scope(Warehouse.active_objects(), user=user, request=request)
        if warehouse_id:
            wh = qs.filter(pk=warehouse_id).first()
            if wh is None:
                raise PrescriptionError("Warehouse not found.")
            return wh
        branch_id = getattr(branch, "id", None) or getattr(user, "branch_id", None)
        if branch_id:
            wh = (
                qs.filter(branch_id=branch_id, is_default=True).first()
                or qs.filter(branch_id=branch_id).first()
            )
            if wh:
                return wh
        return qs.filter(is_default=True).first() or qs.first()

    @staticmethod
    @transaction.atomic
    def dispense(
        *,
        prescription_id,
        user=None,
        request=None,
        notes="",
        deduct_stock=True,
        fill_quantities=None,
        fill_lines=None,
        warehouse_id=None,
    ) -> Prescription:
        """Mark Rx dispensed; optionally FEFO/inventory-deduct product lines.

        fill_quantities: optional {product_id: qty} (POS cart).
        fill_lines: optional {line_id: qty} (partial-fill UI; preferred when set).
        When both omitted, remaining qty on each line is filled.
        deduct_stock=False when POS/sale already reduced inventory+FEFO.
        """
        from apps.inventory.services.inventory_service import InventoryService
        from apps.pharmacy.services.batch_service import BatchError

        rx = (
            PrescriptionService.list(user=user, request=request)
            .filter(pk=prescription_id)
            .prefetch_related("lines")
            .first()
        )
        if rx is None:
            raise PrescriptionError("Prescription not found.")
        if rx.status == Prescription.STATUS_CANCELLED:
            raise PrescriptionError("Cannot dispense a cancelled prescription.")
        if rx.status == Prescription.STATUS_DISPENSED:
            return rx

        lines = list(rx.lines.filter(deleted_at__isnull=True).order_by("sort_order", "created_at"))
        fills: dict[str, Decimal] = {}
        if fill_quantities:
            for pid, qty in fill_quantities.items():
                if pid:
                    fills[str(pid)] = fills.get(str(pid), Decimal("0")) + Decimal(str(qty))

        line_fills: dict[str, Decimal] = {}
        if fill_lines:
            for lid, qty in fill_lines.items():
                if lid is None:
                    continue
                q = Decimal(str(qty))
                if q < 0:
                    raise PrescriptionError("Fill quantity cannot be negative.")
                line_fills[str(lid)] = q

        use_line_fills = bool(line_fills)
        use_product_fills = bool(fills) and not use_line_fills

        warehouse = None
        if deduct_stock:
            warehouse = PrescriptionService._resolve_warehouse(
                warehouse_id=warehouse_id,
                user=user,
                request=request,
                branch=rx.branch,
            )
            if warehouse is None and any(line.product_id for line in lines):
                raise PrescriptionError("No warehouse available to dispense stock.")

        for line in lines:
            remaining = line.quantity_remaining
            if remaining <= 0:
                continue

            if use_line_fills:
                take = min(remaining, line_fills.get(str(line.id), Decimal("0")))
            elif use_product_fills:
                if line.product_id:
                    pid = str(line.product_id)
                    take = min(remaining, fills.get(pid, Decimal("0")))
                    fills[pid] = fills.get(pid, Decimal("0")) - take
                else:
                    take = Decimal("0")
            else:
                take = remaining

            if take <= 0:
                continue

            if deduct_stock and line.product_id and line.product is not None:
                try:
                    InventoryService.apply_sale_delta(
                        product=line.product,
                        warehouse=warehouse,
                        quantity_delta=-take,
                        reference_type="prescription",
                        reference_id=rx.id,
                        user=user,
                        notes=notes or f"Rx dispense {rx.rx_number}",
                    )
                except BatchError as exc:
                    raise PrescriptionError(str(exc)) from exc
                except ValueError as exc:
                    raise PrescriptionError(str(exc)) from exc

            line.quantity_dispensed = Decimal(str(line.quantity_dispensed or 0)) + take
            line.updated_by = user
            line.save(update_fields=["quantity_dispensed", "updated_by", "updated_at"])

        for line in lines:
            line.refresh_from_db(fields=["quantity_dispensed", "quantity"])
        still_open = any(line.quantity_remaining > 0 for line in lines)

        if still_open:
            rx.status = Prescription.STATUS_ACTIVE
        else:
            rx.status = Prescription.STATUS_DISPENSED
            rx.dispensed_at = timezone.now()
            rx.dispensed_by = user

        if notes:
            rx.notes = (rx.notes or "") + f"\nDispensed: {notes}"
        rx.updated_by = user
        rx.save(
            update_fields=[
                "status",
                "dispensed_at",
                "dispensed_by",
                "notes",
                "updated_by",
                "updated_at",
            ]
        )
        return rx

    @staticmethod
    def summary_counts(*, user=None, request=None) -> dict:
        qs = apply_tenant_scope(
            Prescription.active_objects(), user=user, request=request
        )
        return {
            "prescriptions_active": qs.filter(status=Prescription.STATUS_ACTIVE).count(),
            "prescriptions_dispensed": qs.filter(
                status=Prescription.STATUS_DISPENSED
            ).count(),
            "prescriptions_total": qs.count(),
        }
