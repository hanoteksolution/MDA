"""Pharmacy batch / FEFO service (STEP 13)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Sequence
from uuid import UUID

from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from apps.pharmacy.models import BatchDispense, ProductBatch
from core.tenancy import apply_tenant_scope, resolve_acting_tenant


class BatchError(ValueError):
    pass


class BatchService:
    @staticmethod
    def list_batches(
        *,
        user=None,
        request=None,
        product_id=None,
        warehouse_id=None,
        category_id=None,
        expiring_within_days=None,
        include_zero=False,
        search=None,
    ):
        qs = ProductBatch.active_objects().select_related(
            "product", "product__category", "warehouse"
        )
        qs = apply_tenant_scope(qs, user=user, request=request)
        qs = qs.filter(is_active=True)
        if product_id:
            qs = qs.filter(product_id=product_id)
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        if category_id:
            qs = qs.filter(product__category_id=category_id)
        if not include_zero:
            qs = qs.filter(quantity__gt=0)
        if search:
            qs = qs.filter(
                Q(batch_number__icontains=search)
                | Q(product__name__icontains=search)
                | Q(product__sku__icontains=search)
            )
        if expiring_within_days is not None:
            days = int(expiring_within_days)
            today = timezone.localdate()
            qs = qs.filter(
                expiry_date__isnull=False,
                expiry_date__lte=today + timedelta(days=days),
            )
        return qs.order_by(F("expiry_date").asc(nulls_last=True), "batch_number")

    @staticmethod
    def expiring(
        *,
        user=None,
        request=None,
        within_days=None,
        warehouse_id=None,
        category_id=None,
    ):
        tenant = resolve_acting_tenant(user=user, request=request)
        days = within_days
        if days is None and tenant is not None:
            settings = getattr(tenant, "settings", None)
            if settings is not None:
                days = settings.expiry_alert_days
        if days is None:
            days = 30
        return BatchService.list_batches(
            user=user,
            request=request,
            warehouse_id=warehouse_id,
            category_id=category_id,
            expiring_within_days=days,
            include_zero=False,
        )

    @staticmethod
    def list_categories(*, user=None, request=None) -> list[dict]:
        """Distinct inventory categories that appear on pharmacy batches."""
        qs = BatchService.list_batches(user=user, request=request, include_zero=False).order_by()
        rows = (
            qs.exclude(product__category_id=None)
            .values("product__category_id", "product__category__name")
            .annotate(
                batch_count=Count("id"),
                quantity=Sum("quantity"),
                product_count=Count("product_id", distinct=True),
            )
            .order_by("product__category__name")
        )
        return [
            {
                "id": str(row["product__category_id"]),
                "name": row["product__category__name"] or "",
                "batch_count": int(row["batch_count"] or 0),
                "quantity": float(row["quantity"] or 0),
                "product_count": int(row["product_count"] or 0),
            }
            for row in rows
        ]

    @staticmethod
    def summary(*, user=None, request=None, within_days=None):
        qs = BatchService.list_batches(user=user, request=request, include_zero=False)
        today = timezone.localdate()
        tenant = resolve_acting_tenant(user=user, request=request)
        days = within_days
        if days is None and tenant is not None:
            settings = getattr(tenant, "settings", None)
            if settings is not None:
                days = settings.expiry_alert_days
        if days is None:
            days = 30
        horizon = today + timedelta(days=int(days))
        expired = qs.filter(expiry_date__isnull=False, expiry_date__lt=today)
        expiring = qs.filter(
            expiry_date__isnull=False, expiry_date__gte=today, expiry_date__lte=horizon
        )
        from apps.pharmacy.services.prescription_service import PrescriptionService

        rx_counts = PrescriptionService.summary_counts(user=user, request=request)
        return {
            "batch_count": qs.count(),
            "total_quantity": float(qs.aggregate(t=Sum("quantity"))["t"] or 0),
            "expired_count": expired.count(),
            "expiring_count": expiring.count(),
            "expiry_alert_days": int(days),
            "categories": BatchService.list_categories(user=user, request=request),
            **rx_counts,
        }

    @staticmethod
    def serialize(batch: ProductBatch) -> dict:
        today = timezone.localdate()
        days_to_expiry = None
        status = "ok"
        if batch.expiry_date:
            days_to_expiry = (batch.expiry_date - today).days
            if days_to_expiry < 0:
                status = "expired"
            elif days_to_expiry <= 30:
                status = "expiring"
        return {
            "id": str(batch.id),
            "product_id": str(batch.product_id),
            "product_name": batch.product.name if batch.product_id else "",
            "product_sku": batch.product.sku if batch.product_id else "",
            "category_id": str(batch.product.category_id)
            if batch.product_id and getattr(batch.product, "category_id", None)
            else None,
            "category_name": (
                batch.product.category.name
                if batch.product_id and getattr(batch.product, "category_id", None)
                else ""
            ),
            "warehouse_id": str(batch.warehouse_id),
            "warehouse_name": batch.warehouse.name if batch.warehouse_id else "",
            "batch_number": batch.batch_number,
            "manufacturing_date": batch.manufacturing_date.isoformat()
            if batch.manufacturing_date
            else None,
            "expiry_date": batch.expiry_date.isoformat() if batch.expiry_date else None,
            "days_to_expiry": days_to_expiry,
            "status": status,
            "quantity": float(batch.quantity),
            "cost_price": float(batch.cost_price) if batch.cost_price is not None else None,
            "is_active": batch.is_active,
            "notes": batch.notes,
        }

    @staticmethod
    @transaction.atomic
    def receive_stock(
        *,
        product,
        warehouse,
        quantity,
        batch_number: Optional[str] = None,
        expiry_date: Optional[date] = None,
        manufacturing_date: Optional[date] = None,
        cost_price=None,
        user=None,
        notes="",
    ) -> ProductBatch:
        qty = Decimal(str(quantity))
        if qty <= 0:
            raise BatchError("Batch receive quantity must be positive.")
        number = (batch_number or "").strip() or f"AUTO-{timezone.localdate().isoformat()}"
        tenant_id = getattr(warehouse, "tenant_id", None) or getattr(product, "tenant_id", None)

        batch = (
            ProductBatch.objects.select_for_update()
            .filter(
                product=product,
                warehouse=warehouse,
                batch_number=number,
                deleted_at__isnull=True,
            )
            .first()
        )
        if batch is None:
            return ProductBatch.objects.create(
                product=product,
                warehouse=warehouse,
                batch_number=number,
                expiry_date=expiry_date,
                manufacturing_date=manufacturing_date,
                quantity=qty,
                cost_price=cost_price,
                notes=notes,
                tenant_id=tenant_id,
                created_by=user,
            )

        batch.quantity = Decimal(str(batch.quantity)) + qty
        if expiry_date and not batch.expiry_date:
            batch.expiry_date = expiry_date
        if manufacturing_date and not batch.manufacturing_date:
            batch.manufacturing_date = manufacturing_date
        if cost_price is not None:
            batch.cost_price = cost_price
        batch.deleted_at = None
        batch.deleted_by = None
        batch.is_active = True
        batch.updated_by = user
        batch.save()
        return batch

    @staticmethod
    def fefo_candidates(*, product, warehouse):
        """Active batches with qty > 0, earliest expiry first (nulls last)."""
        return list(
            ProductBatch.active_objects()
            .select_for_update()
            .filter(
                product=product,
                warehouse=warehouse,
                is_active=True,
                quantity__gt=0,
            )
            .order_by(F("expiry_date").asc(nulls_last=True), "created_at")
        )

    @staticmethod
    def plan_fefo(*, product, warehouse, quantity) -> list[tuple[ProductBatch, Decimal]]:
        need = Decimal(str(quantity))
        if need <= 0:
            return []
        plan = []
        remaining = need
        for batch in BatchService.fefo_candidates(product=product, warehouse=warehouse):
            available = Decimal(str(batch.quantity))
            if available <= 0:
                continue
            take = min(available, remaining)
            plan.append((batch, take))
            remaining -= take
            if remaining <= 0:
                break
        if remaining > 0:
            raise BatchError(
                f"Insufficient batch stock for {getattr(product, 'sku', product)} "
                f"(need {need}, short {remaining})."
            )
        return plan

    @staticmethod
    @transaction.atomic
    def deduct_fefo(
        *,
        product,
        warehouse,
        quantity,
        reference_type="invoice",
        reference_id=None,
        user=None,
        notes="",
    ) -> list[BatchDispense]:
        """Deduct quantity from batches in FEFO order. No-op if no batches exist."""
        qty = Decimal(str(quantity))
        if qty <= 0:
            return []

        has_any = ProductBatch.active_objects().filter(
            product=product, warehouse=warehouse, is_active=True
        ).exists()
        if not has_any:
            return []

        plan = BatchService.plan_fefo(product=product, warehouse=warehouse, quantity=qty)
        dispenses = []
        for batch, take in plan:
            batch.quantity = Decimal(str(batch.quantity)) - take
            batch.updated_by = user
            batch.save(update_fields=["quantity", "updated_by", "updated_at"])
            dispenses.append(
                BatchDispense.objects.create(
                    batch=batch,
                    quantity=take,
                    reference_type=reference_type,
                    reference_id=reference_id,
                    notes=notes,
                    created_by=user,
                )
            )
        return dispenses

    @staticmethod
    @transaction.atomic
    def restore_for_reference(
        *,
        reference_type="invoice",
        reference_id=None,
        product=None,
        quantity=None,
        user=None,
    ):
        """Restore batch qty for a prior dispense (sale reverse / return).

        If product+quantity given, restores up to that qty from matching dispenses.
        """
        if reference_id is None:
            return Decimal("0")
        qs = BatchDispense.active_objects().filter(
            reference_type=reference_type, reference_id=reference_id
        ).select_related("batch")
        if product is not None:
            qs = qs.filter(batch__product=product)
        restored = Decimal("0")
        target = Decimal(str(quantity)) if quantity is not None else None
        for row in qs.order_by("-created_at"):
            if target is not None and restored >= target:
                break
            take = Decimal(str(row.quantity))
            if target is not None:
                take = min(take, target - restored)
            if take <= 0:
                continue
            batch = ProductBatch.objects.select_for_update().get(pk=row.batch_id)
            batch.quantity = Decimal(str(batch.quantity)) + take
            batch.updated_by = user
            batch.save(update_fields=["quantity", "updated_by", "updated_at"])
            restored += take
            if take >= Decimal(str(row.quantity)):
                row.soft_delete(user=user)
            else:
                row.quantity = Decimal(str(row.quantity)) - take
                row.updated_by = user
                row.save(update_fields=["quantity", "updated_by", "updated_at"])
        return restored
