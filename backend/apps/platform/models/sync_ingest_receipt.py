"""Cloud-side idempotent ingest receipts (STEP 29)."""

import uuid

from django.db import models


class SyncIngestReceipt(models.Model):
    """Proof that a shop push operation was applied once (replay-safe)."""

    RESOURCE_INVOICE = "invoice"
    RESOURCE_CUSTOMER = "customer"
    RESOURCE_CHOICES = [
        (RESOURCE_INVOICE, "Invoice"),
        (RESOURCE_CUSTOMER, "Customer"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "platform.Tenant",
        on_delete=models.CASCADE,
        related_name="sync_ingest_receipts",
    )
    device_id = models.CharField(max_length=64, blank=True)
    idempotency_key = models.CharField(max_length=64, db_index=True)
    resource_type = models.CharField(max_length=30, choices=RESOURCE_CHOICES, default=RESOURCE_INVOICE)
    resource_id = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sync_ingest_receipts"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "idempotency_key"],
                name="uniq_sync_ingest_tenant_idempotency",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "created_at"], name="idx_sync_ingest_tenant_created"),
        ]

    def __str__(self):
        return f"{self.tenant_id}:{self.idempotency_key}"
