from django.conf import settings
from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class Notification(TenantScopedModel, BaseModel):
    """In-app notification for a tenant user."""

    TYPE_LOW_STOCK = "low_stock"
    TYPE_GYM_EXPIRY = "gym_membership_expiry"
    TYPE_PHARMACY_EXPIRY = "pharmacy_batch_expiry"
    TYPE_ACCOUNTING_HEALTH = "accounting_health"
    TYPE_SYSTEM = "system"
    TYPE_CHOICES = [
        (TYPE_LOW_STOCK, "Low stock"),
        (TYPE_GYM_EXPIRY, "Gym membership expiry"),
        (TYPE_PHARMACY_EXPIRY, "Pharmacy batch expiry"),
        (TYPE_ACCOUNTING_HEALTH, "Accounting health"),
        (TYPE_SYSTEM, "System"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES, db_index=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"], name="idx_notif_user_read"),
            models.Index(
                fields=["tenant", "notification_type", "-created_at"],
                name="idx_notif_tenant_type",
            ),
        ]

    def __str__(self):
        return f"{self.notification_type}: {self.title}"
