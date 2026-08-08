"""Trash / recycle bin for soft-deleted sales documents and expenses."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Q

from apps.sales.models import Expense, Invoice, Quotation
from apps.sales.serializers.sales_serializers import serialize_invoice, serialize_quotation
from apps.sales.services.sales_service import InvoiceService, _aggregate_item_quantities
from apps.inventory.services.inventory_service import InventoryService
import re


def _trash_sort_key(row: dict) -> tuple:
    """Numeric suffix of reference (INV-…-00060 → 60), then deleted_at."""
    ref = (row.get("number") or row.get("title") or "").strip()
    match = re.search(r"(\d+)\s*$", ref)
    num = int(match.group(1)) if match else -1
    return (num, row.get("deleted_at") or "")


def _infer_invoice_restore_status(invoice: Invoice) -> str:
    """Pick a sensible status after restore when the prior status was overwritten to cancelled."""
    notes = (invoice.notes or "").lower()
    if "payment: hold" in notes:
        return Invoice.STATUS_ON_HOLD
    if invoice.amount_paid and invoice.amount_paid >= invoice.total_amount and invoice.total_amount > 0:
        return Invoice.STATUS_PAID
    return Invoice.STATUS_SENT


def _serialize_expense(e: Expense) -> dict:
    return {
        "id": str(e.id),
        "kind": "expense",
        "number": e.description[:48] or "Expense",
        "title": e.description,
        "category": e.category,
        "amount": float(e.amount),
        "notes": e.notes,
        "date": e.expense_date.isoformat(),
        "branch_id": str(e.branch_id),
        "branch_name": e.branch.name if e.branch_id else "",
        "status": "deleted",
        "deleted_at": e.deleted_at.isoformat() if e.deleted_at else None,
        "deleted_by": (
            (e.deleted_by.get_full_name() or e.deleted_by.username) if e.deleted_by_id else None
        ),
    }


def _serialize_invoice_trash(inv: Invoice) -> dict:
    data = serialize_invoice(inv, include_items=False)
    data["kind"] = "invoice"
    data["title"] = inv.invoice_number
    data["deleted_at"] = inv.deleted_at.isoformat() if inv.deleted_at else None
    data["deleted_by"] = (
        (inv.deleted_by.get_full_name() or inv.deleted_by.username) if inv.deleted_by_id else None
    )
    return data


def _serialize_quotation_trash(q: Quotation) -> dict:
    data = serialize_quotation(q, include_items=False)
    data["kind"] = "quotation"
    data["title"] = q.quotation_number
    data["deleted_at"] = q.deleted_at.isoformat() if q.deleted_at else None
    data["deleted_by"] = (
        (q.deleted_by.get_full_name() or q.deleted_by.username) if q.deleted_by_id else None
    )
    return data


class TrashService:
    @staticmethod
    def list(*, kind: str | None = None, search: str | None = None, branch_id=None):
        items: list[dict] = []
        kind = (kind or "all").strip().lower()
        search = (search or "").strip()

        if kind in ("all", "invoice", "receipt"):
            qs = (
                Invoice.objects.filter(deleted_at__isnull=False)
                .select_related("customer", "branch", "created_by_user", "served_by_user", "deleted_by")
                .order_by("deleted_at")
            )
            if branch_id:
                qs = qs.filter(branch_id=branch_id)
            if search:
                qs = qs.filter(
                    Q(invoice_number__icontains=search)
                    | Q(customer__full_name__icontains=search)
                    | Q(notes__icontains=search)
                )
            items.extend(_serialize_invoice_trash(inv) for inv in qs[:200])

        if kind in ("all", "quotation"):
            qs = (
                Quotation.objects.filter(deleted_at__isnull=False)
                .select_related("customer", "branch", "created_by_user", "deleted_by")
                .order_by("deleted_at")
            )
            if branch_id:
                qs = qs.filter(branch_id=branch_id)
            if search:
                qs = qs.filter(
                    Q(quotation_number__icontains=search)
                    | Q(customer__full_name__icontains=search)
                    | Q(notes__icontains=search)
                )
            items.extend(_serialize_quotation_trash(q) for q in qs[:200])

        if kind in ("all", "expense"):
            qs = (
                Expense.objects.filter(deleted_at__isnull=False)
                .select_related("branch", "created_by_user", "deleted_by")
                .order_by("deleted_at")
            )
            if branch_id:
                qs = qs.filter(branch_id=branch_id)
            if search:
                qs = qs.filter(
                    Q(description__icontains=search)
                    | Q(notes__icontains=search)
                    | Q(category__icontains=search)
                )
            items.extend(_serialize_expense(e) for e in qs[:200])

        # Sequential by receipt/reference number, highest (latest) first
        items.sort(key=_trash_sort_key, reverse=True)
        return items

    @staticmethod
    @transaction.atomic
    def restore_invoice(*, invoice_id, user=None):
        inv = (
            Invoice.objects.select_related("branch", "customer")
            .prefetch_related("items")
            .filter(pk=invoice_id, deleted_at__isnull=False)
            .first()
        )
        if not inv:
            raise ValueError("Deleted receipt not found.")

        # Soft-restore first so inventory helpers see an active invoice id
        inv.restore()
        status = _infer_invoice_restore_status(inv)
        inv.status = status
        inv.updated_by = user
        inv.save(update_fields=["status", "updated_by", "updated_at"])

        # Re-apply stock sale (inverse of delete restore)
        warehouse = InventoryService.resolve_warehouse_for_branch(branch=inv.branch)
        if warehouse:
            sold = _aggregate_item_quantities(list(inv.items.all()))
            deltas = {pid: -qty for pid, qty in sold.items() if qty}
            InventoryService.apply_invoice_quantity_deltas(
                warehouse=warehouse,
                quantity_by_product=deltas,
                reference_id=inv.id,
                user=user,
                notes=f"Sale restored {inv.invoice_number}",
            )

        return InvoiceService.list(user=user).get(pk=inv.pk)

    @staticmethod
    @transaction.atomic
    def restore_quotation(*, quotation_id, user=None):
        q = Quotation.objects.filter(pk=quotation_id, deleted_at__isnull=False).first()
        if not q:
            raise ValueError("Deleted quotation not found.")
        q.restore()
        q.updated_by = user
        q.save(update_fields=["updated_by", "updated_at"])
        return q

    @staticmethod
    @transaction.atomic
    def restore_expense(*, expense_id, user=None):
        e = (
            Expense.objects.select_related("branch", "created_by_user")
            .filter(pk=expense_id, deleted_at__isnull=False)
            .first()
        )
        if not e:
            raise ValueError("Deleted expense not found.")
        e.restore()
        e.updated_by = user
        e.save(update_fields=["updated_by", "updated_at"])
        return e

    @staticmethod
    @transaction.atomic
    def purge(*, kind: str, item_id, user=None):
        """Permanently remove a trash item (hard delete)."""
        kind = (kind or "").strip().lower()
        if kind in ("invoice", "receipt"):
            inv = Invoice.objects.filter(pk=item_id, deleted_at__isnull=False).first()
            if not inv:
                raise ValueError("Deleted receipt not found.")
            inv.items.all().delete()
            inv.delete()
            return True
        if kind == "quotation":
            q = Quotation.objects.filter(pk=item_id, deleted_at__isnull=False).first()
            if not q:
                raise ValueError("Deleted quotation not found.")
            q.items.all().delete()
            q.delete()
            return True
        if kind == "expense":
            e = Expense.objects.filter(pk=item_id, deleted_at__isnull=False).first()
            if not e:
                raise ValueError("Deleted expense not found.")
            e.delete()
            return True
        raise ValueError("Unknown trash kind.")
