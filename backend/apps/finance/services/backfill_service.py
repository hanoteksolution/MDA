"""Historical GL backfill — post missing journals for operational documents."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils.dateparse import parse_date

from apps.finance.models import AccountingEvent, JournalEntry
from apps.finance.services.chart_service import ChartService
from apps.finance.services.mapping_service import MappingService
from apps.finance.services.posting_service import AccountingPostingService, PostingError
from apps.platform.models import Tenant, TenantSettings
from apps.purchases.models import PurchaseOrder
from apps.sales.models import Expense, Invoice
from core.tenancy import tenant_context


class BackfillError(ValueError):
    pass


class AccountingBackfillService:
    """Backfill SALE_COMPLETED / EXPENSE_APPROVED / PURCHASE_RECEIVED for a tenant."""

    @staticmethod
    def _cutover(tenant_id):
        settings = TenantSettings.objects.filter(tenant_id=tenant_id, deleted_at__isnull=True).first()
        return settings.accounting_cutover_date if settings else None

    @staticmethod
    def _has_event(*, tenant_id, idempotency_key: str) -> bool:
        return AccountingEvent.active_objects().filter(
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            status=AccountingEvent.STATUS_POSTED,
        ).exists() or JournalEntry.active_objects().filter(
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            status=JournalEntry.STATUS_POSTED,
        ).exists()

    @staticmethod
    def _mark_backfill(entry: JournalEntry | None):
        if entry is None:
            return
        note = "historical backfill"
        if note not in (entry.notes or ""):
            entry.notes = f"{entry.notes}\n{note}".strip() if entry.notes else note
            entry.save(update_fields=["notes", "updated_at"])

    @staticmethod
    def preview(*, tenant_id, before_date=None, limit=500) -> dict:
        """Dry-run: count documents missing journals (optionally before cutover/before_date)."""
        tenant = Tenant.objects.filter(pk=tenant_id, deleted_at__isnull=True).first()
        if not tenant:
            raise BackfillError("Tenant not found.")

        ChartService.ensure_default_chart(tenant_id=tenant_id)
        MappingService.seed_defaults(tenant_id=tenant_id)

        before = parse_date(str(before_date)) if before_date and isinstance(before_date, str) else before_date
        if before is None:
            before = AccountingBackfillService._cutover(tenant_id)

        invoices = Invoice.active_objects().filter(
            tenant_id=tenant_id,
            status__in=[Invoice.STATUS_PAID, Invoice.STATUS_SENT, Invoice.STATUS_OVERDUE],
        )
        expenses = Expense.active_objects().filter(tenant_id=tenant_id)
        pos = PurchaseOrder.active_objects().filter(tenant_id=tenant_id).exclude(
            status=PurchaseOrder.STATUS_CANCELLED
        )
        if before:
            invoices = invoices.filter(issue_date__lt=before)
            expenses = expenses.filter(expense_date__lt=before)
            pos = pos.filter(order_date__lt=before)

        missing_invoices = []
        for inv in invoices.select_related("branch")[:limit]:
            key = f"SALE_COMPLETED:sales:invoice:{inv.id}"
            gym_key = f"GYM_MEMBERSHIP_SOLD:sales:invoice:{inv.id}"
            gym_svc_key = f"GYM_SERVICE_SOLD:sales:invoice:{inv.id}"
            pharm_key = f"PHARMACY_SALE_COMPLETED:pharmacy:invoice:{inv.id}"
            if AccountingBackfillService._has_event(tenant_id=tenant_id, idempotency_key=key):
                continue
            if AccountingBackfillService._has_event(tenant_id=tenant_id, idempotency_key=gym_key):
                continue
            if AccountingBackfillService._has_event(
                tenant_id=tenant_id, idempotency_key=gym_svc_key
            ):
                continue
            if AccountingBackfillService._has_event(
                tenant_id=tenant_id, idempotency_key=pharm_key
            ):
                continue
            missing_invoices.append(
                {
                    "id": str(inv.id),
                    "number": inv.invoice_number,
                    "date": inv.issue_date.isoformat() if inv.issue_date else None,
                    "total": float(inv.total_amount),
                    "status": inv.status,
                }
            )

        missing_expenses = []
        for exp in expenses.select_related("branch")[:limit]:
            key = f"EXPENSE_APPROVED:sales:expense:{exp.id}"
            if AccountingBackfillService._has_event(tenant_id=tenant_id, idempotency_key=key):
                continue
            missing_expenses.append(
                {
                    "id": str(exp.id),
                    "description": (exp.description or "")[:80],
                    "date": exp.expense_date.isoformat() if exp.expense_date else None,
                    "amount": float(exp.amount),
                }
            )

        missing_pos = []
        for po in pos.prefetch_related("items")[:limit]:
            received = Decimal("0")
            for item in po.items.all():
                qty = Decimal(str(item.quantity_received or 0))
                if qty > 0:
                    received += qty * Decimal(str(item.unit_cost))
            if received <= Decimal("0.005"):
                continue
            # Any posted purchase event for this PO
            has = AccountingEvent.active_objects().filter(
                tenant_id=tenant_id,
                event_type="PURCHASE_RECEIVED",
                source_id=po.id,
                status=AccountingEvent.STATUS_POSTED,
            ).exists()
            if has:
                continue
            missing_pos.append(
                {
                    "id": str(po.id),
                    "number": po.order_number,
                    "date": po.order_date.isoformat() if po.order_date else None,
                    "received_value": float(received),
                }
            )

        return {
            "tenant_id": str(tenant_id),
            "before_date": before.isoformat() if before else None,
            "dry_run": True,
            "missing": {
                "invoices": missing_invoices,
                "expenses": missing_expenses,
                "purchase_orders": missing_pos,
            },
            "counts": {
                "invoices": len(missing_invoices),
                "expenses": len(missing_expenses),
                "purchase_orders": len(missing_pos),
                "total": len(missing_invoices) + len(missing_expenses) + len(missing_pos),
            },
        }

    @staticmethod
    @transaction.atomic
    def run(
        *,
        tenant_id,
        before_date=None,
        dry_run=True,
        limit=500,
        include_invoices=True,
        include_expenses=True,
        include_purchases=True,
        user=None,
    ) -> dict:
        preview = AccountingBackfillService.preview(
            tenant_id=tenant_id, before_date=before_date, limit=limit
        )
        if dry_run:
            return preview

        posted = {"invoices": 0, "expenses": 0, "purchase_orders": 0, "errors": []}

        with tenant_context(Tenant.objects.get(pk=tenant_id), enforce=True):
            if include_invoices:
                from apps.finance.events import event_types
                from apps.platform.services.module_service import tenant_has_module

                pharmacy_on = tenant_has_module(
                    "pharmacy", tenant=Tenant.objects.filter(pk=tenant_id).first()
                )
                for row in preview["missing"]["invoices"]:
                    inv = Invoice.active_objects().filter(pk=row["id"]).first()
                    if not inv:
                        continue
                    try:
                        sale_kwargs = {}
                        if pharmacy_on:
                            sale_kwargs = {
                                "event_type": event_types.PHARMACY_SALE_COMPLETED,
                                "source_module": "pharmacy",
                                "revenue_mapping_key": "PHARMACY_SALES_REVENUE",
                            }
                        entry = AccountingPostingService.post_sale(
                            invoice=inv, user=user, **sale_kwargs
                        )
                        AccountingBackfillService._mark_backfill(entry)
                        if entry:
                            posted["invoices"] += 1
                    except (PostingError, Exception) as exc:
                        posted["errors"].append({"type": "invoice", "id": row["id"], "error": str(exc)})

            if include_expenses:
                for row in preview["missing"]["expenses"]:
                    exp = Expense.active_objects().filter(pk=row["id"]).first()
                    if not exp:
                        continue
                    try:
                        entry = AccountingPostingService.post_expense(expense=exp, user=user)
                        AccountingBackfillService._mark_backfill(entry)
                        if entry:
                            posted["expenses"] += 1
                    except (PostingError, Exception) as exc:
                        posted["errors"].append({"type": "expense", "id": row["id"], "error": str(exc)})

            if include_purchases:
                for row in preview["missing"]["purchase_orders"]:
                    po = (
                        PurchaseOrder.active_objects()
                        .filter(pk=row["id"])
                        .prefetch_related("items")
                        .first()
                    )
                    if not po:
                        continue
                    lines = [item for item in po.items.all() if Decimal(str(item.quantity_received or 0)) > 0]
                    receive_total = Decimal(str(row["received_value"]))
                    try:
                        entry = AccountingPostingService.post_purchase_received(
                            purchase_order=po,
                            receive_total=receive_total,
                            lines=lines,
                            user=user,
                        )
                        AccountingBackfillService._mark_backfill(entry)
                        if entry:
                            posted["purchase_orders"] += 1
                    except (PostingError, Exception) as exc:
                        posted["errors"].append(
                            {"type": "purchase_order", "id": row["id"], "error": str(exc)}
                        )

        return {
            "tenant_id": str(tenant_id),
            "before_date": preview["before_date"],
            "dry_run": False,
            "posted": posted,
            "preview_counts": preview["counts"],
        }
