from django.db import models
from django.utils import timezone

from core.models.base import BaseModel


class TenantDomain(BaseModel):
    """Hostname mapped to a tenant (subdomain or custom domain)."""

    tenant = models.ForeignKey(
        "platform.Tenant",
        on_delete=models.CASCADE,
        related_name="domains",
    )
    domain = models.CharField(max_length=255, unique=True, db_index=True)
    subdomain = models.SlugField(max_length=100, blank=True, db_index=True)
    is_primary = models.BooleanField(default=False, db_index=True)
    is_custom = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "tenant_domains"
        ordering = ["-is_primary", "domain"]

    def __str__(self):
        return self.domain

    def mark_verified(self):
        self.is_verified = True
        self.verified_at = timezone.now()
        self.save(update_fields=["is_verified", "verified_at", "updated_at"])


class TenantSettings(BaseModel):
    """Per-tenant operational defaults (POS, branding, alerts)."""

    tenant = models.OneToOneField(
        "platform.Tenant",
        on_delete=models.CASCADE,
        related_name="settings",
    )
    date_format = models.CharField(max_length=32, default="YYYY-MM-DD")
    time_format = models.CharField(max_length=32, default="HH:mm")
    fiscal_year_start_month = models.PositiveSmallIntegerField(default=1)
    default_tax_rate = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    invoice_prefix = models.CharField(max_length=20, blank=True)
    receipt_footer = models.TextField(blank=True)
    low_stock_alert_enabled = models.BooleanField(default=True)
    expiry_alert_days = models.PositiveIntegerField(default=30)
    branding = models.JSONField(default=dict, blank=True)
    pos_defaults = models.JSONField(default=dict, blank=True)
    extras = models.JSONField(default=dict, blank=True)
    accounting_cutover_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Ledger-authoritative from this date; earlier docs may be backfilled.",
    )
    accounting_posting_enabled = models.BooleanField(
        default=True,
        db_index=True,
        help_text="When False, CAE posting is skipped for this tenant (pilot rollback).",
    )

    class Meta:
        db_table = "tenant_settings"

    def __str__(self):
        return f"Settings<{self.tenant_id}>"
