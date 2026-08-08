from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class AccountingEvent(TenantScopedModel, BaseModel):
    """Lifecycle record for business → accounting posting (idempotency + retry)."""

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_POSTED = "posted"
    STATUS_FAILED = "failed"
    STATUS_REVERSED = "reversed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_POSTED, "Posted"),
        (STATUS_FAILED, "Failed"),
        (STATUS_REVERSED, "Reversed"),
    ]

    event_type = models.CharField(max_length=50, db_index=True)
    source_module = models.CharField(max_length=30, db_index=True)
    source_type = models.CharField(max_length=30, db_index=True)
    source_id = models.UUIDField(db_index=True)
    source_reference = models.CharField(max_length=100, blank=True)
    idempotency_key = models.CharField(max_length=150, db_index=True)
    occurred_at = models.DateTimeField(db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    journal_entry = models.ForeignKey(
        "finance.JournalEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accounting_events",
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "finance_accounting_events"
        ordering = ["-occurred_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "idempotency_key"],
                condition=models.Q(deleted_at__isnull=True, tenant__isnull=False),
                name="uniq_fin_event_tenant_idempotency",
            ),
        ]

    def __str__(self):
        return f"{self.event_type} [{self.status}]"
