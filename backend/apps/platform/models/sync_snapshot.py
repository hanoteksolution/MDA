import uuid

from django.db import models
from django.utils import timezone


class ShopSyncSnapshot(models.Model):
    """Latest operational snapshot pushed from a shop PC while online."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "platform.Tenant",
        on_delete=models.CASCADE,
        related_name="sync_snapshots",
    )
    device_id = models.CharField(max_length=64, blank=True)
    synced_at = models.DateTimeField(db_index=True, default=timezone.now)
    kpis = models.JSONField(default=dict)
    invoices = models.JSONField(default=list)
    company_name = models.CharField(max_length=255, blank=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "shop_sync_snapshots"
        ordering = ["-synced_at"]

    def __str__(self):
        return f"{self.tenant.name} @ {self.synced_at}"
