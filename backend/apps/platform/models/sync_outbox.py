"""Shop-side sync outbox queue (STEP 29)."""

import uuid

from django.db import models
from django.utils import timezone


class SyncOutboxEntry(models.Model):
    """Pending cloud upload for offline POS operations."""

    STATUS_PENDING = "pending"
    STATUS_SYNCED = "synced"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SYNCED, "Synced"),
        (STATUS_FAILED, "Failed"),
    ]

    RESOURCE_INVOICE = "invoice"
    RESOURCE_CUSTOMER = "customer"
    RESOURCE_INVENTORY = "inventory"
    RESOURCE_CHOICES = [
        (RESOURCE_INVOICE, "Invoice"),
        (RESOURCE_CUSTOMER, "Customer"),
        (RESOURCE_INVENTORY, "Inventory"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resource_type = models.CharField(max_length=30, choices=RESOURCE_CHOICES, db_index=True)
    resource_id = models.CharField(max_length=64, db_index=True)
    idempotency_key = models.CharField(max_length=64, blank=True, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sync_outbox_entries"
        indexes = [
            models.Index(fields=["status", "created_at"], name="idx_sync_outbox_status_created"),
        ]

    def mark_synced(self):
        self.status = self.STATUS_SYNCED
        self.synced_at = timezone.now()
        self.last_error = ""
        self.save(update_fields=["status", "synced_at", "last_error", "updated_at"])

    def mark_failed(self, message: str):
        self.status = self.STATUS_FAILED
        self.attempts += 1
        self.last_error = (message or "")[:500]
        self.save(update_fields=["status", "attempts", "last_error", "updated_at"])

    def __str__(self):
        return f"{self.resource_type}:{self.resource_id} ({self.status})"
