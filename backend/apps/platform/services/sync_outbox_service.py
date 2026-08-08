"""Local sync outbox queue for offline POS (STEP 29)."""

from __future__ import annotations

from django.utils import timezone

from apps.platform.models import SyncOutboxEntry


class SyncOutboxService:
    @staticmethod
    def enqueue_invoice(*, invoice, idempotency_key: str | None = None) -> SyncOutboxEntry:
        key = (idempotency_key or getattr(invoice, "idempotency_key", None) or "").strip()
        resource_id = str(invoice.pk)
        existing = (
            SyncOutboxEntry.objects.filter(
                resource_type=SyncOutboxEntry.RESOURCE_INVOICE,
                resource_id=resource_id,
            )
            .exclude(status=SyncOutboxEntry.STATUS_SYNCED)
            .first()
        )
        if existing:
            if key and not existing.idempotency_key:
                existing.idempotency_key = key
                existing.save(update_fields=["idempotency_key", "updated_at"])
            return existing

        return SyncOutboxEntry.objects.create(
            resource_type=SyncOutboxEntry.RESOURCE_INVOICE,
            resource_id=resource_id,
            idempotency_key=key,
            payload={
                "invoice_number": getattr(invoice, "invoice_number", ""),
                "total_amount": float(getattr(invoice, "total_amount", 0) or 0),
            },
        )

    @staticmethod
    def summary() -> dict:
        qs = SyncOutboxEntry.objects.all()
        pending = qs.filter(status=SyncOutboxEntry.STATUS_PENDING).count()
        failed = qs.filter(status=SyncOutboxEntry.STATUS_FAILED).count()
        synced = qs.filter(status=SyncOutboxEntry.STATUS_SYNCED).count()
        last = qs.order_by("-updated_at").first()
        return {
            "pending": pending,
            "failed": failed,
            "synced": synced,
            "total": qs.count(),
            "last_updated_at": last.updated_at.isoformat() if last else None,
        }

    @staticmethod
    def list_pending(*, limit: int = 50):
        return SyncOutboxEntry.objects.filter(
            status=SyncOutboxEntry.STATUS_PENDING
        ).order_by("created_at")[:limit]

    @staticmethod
    def mark_invoices_synced(*, invoice_ids: list[str]) -> int:
        if not invoice_ids:
            return 0
        now = timezone.now()
        updated = SyncOutboxEntry.objects.filter(
            resource_type=SyncOutboxEntry.RESOURCE_INVOICE,
            resource_id__in=invoice_ids,
            status__in=[SyncOutboxEntry.STATUS_PENDING, SyncOutboxEntry.STATUS_FAILED],
        ).update(status=SyncOutboxEntry.STATUS_SYNCED, synced_at=now, last_error="")
        return updated

    @staticmethod
    def mark_push_failed(*, message: str) -> int:
        pending = SyncOutboxEntry.objects.filter(status=SyncOutboxEntry.STATUS_PENDING)
        count = 0
        for row in pending:
            row.mark_failed(message)
            count += 1
        return count
