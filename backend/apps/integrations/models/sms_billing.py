"""SMS reseller billing: platform packages, tenant purchases and an immutable credit ledger.

Safari Technology owns the SMS providers; tenants buy credit packages and spend credits per
message segment. Balance = remaining units in unexpired ``SmsCreditLot`` rows. Every change to a
lot is mirrored by one immutable ``SmsCreditEntry``.
"""

from django.core.exceptions import ValidationError
from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class SmsPackage(BaseModel):
    """A platform-wide SMS credit package sold to tenants (managed by Platform Admin only)."""

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40)
    sms_quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=14, decimal_places=4)
    currency = models.CharField(max_length=3, default="USD")
    validity_days = models.PositiveIntegerField(null=True, blank=True)  # NULL = credits never expire
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "sms_packages"
        ordering = ["price", "name"]
        constraints = [
            models.UniqueConstraint(fields=["code"], condition=models.Q(deleted_at__isnull=True), name="uniq_sms_package_code"),
            models.CheckConstraint(check=models.Q(sms_quantity__gt=0), name="sms_package_quantity_positive"),
            models.CheckConstraint(check=models.Q(price__gte=0), name="sms_package_price_non_negative"),
        ]

    def __str__(self):
        return f"{self.name} ({self.sms_quantity} SMS)"


class SmsBillingSettings(BaseModel):
    """Singleton: the payment provider Safari Technology collects package payments through."""

    payment_provider = models.ForeignKey(
        "integrations.PaymentProviderConfig", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "sms_billing_settings"

    @classmethod
    def load(cls):
        return cls.objects.order_by("created_at").first() or cls.objects.create()


class SmsCreditAccount(TenantScopedModel, BaseModel):
    """One per tenant; its row lock serialises every credit movement for that tenant."""

    class Meta:
        db_table = "sms_credit_accounts"
        constraints = [models.UniqueConstraint(fields=["tenant"], name="uniq_sms_credit_account_tenant")]


class SmsPackagePurchase(TenantScopedModel, BaseModel):
    STATUS_PENDING = "pending"      # awaiting a verified provider confirmation
    STATUS_CREDITED = "credited"    # paid and credited exactly once
    STATUS_FAILED = "failed"        # provider refused / reported failure
    STATUS_EXPIRED = "expired"      # never confirmed in time
    STATUS_REVIEW = "review"        # money/amount does not add up: a human decides (manual adjustment)
    STATUS_CHOICES = [(s, s) for s in (STATUS_PENDING, STATUS_CREDITED, STATUS_FAILED, STATUS_EXPIRED, STATUS_REVIEW)]

    package = models.ForeignKey(SmsPackage, on_delete=models.PROTECT, related_name="purchases")
    # Snapshot at purchase time: later package edits never change what was bought.
    package_name = models.CharField(max_length=120)
    sms_quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=14, decimal_places=4)
    currency = models.CharField(max_length=3)
    validity_days = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    idempotency_key = models.CharField(max_length=64)
    provider = models.ForeignKey(
        "integrations.PaymentProviderConfig", on_delete=models.PROTECT, null=True, blank=True, related_name="+",
    )
    provider_reference = models.CharField(max_length=190, blank=True)
    failure_reason = models.CharField(max_length=300, blank=True)
    credited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "sms_package_purchases"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "idempotency_key"], name="uniq_sms_purchase_key"),
            models.UniqueConstraint(
                fields=["provider", "provider_reference"], condition=~models.Q(provider_reference=""),
                name="uniq_sms_purchase_provider_ref",
            ),
        ]


class SmsCreditLot(TenantScopedModel, BaseModel):
    """Units granted together (a purchase or a manual credit) with one expiry."""

    purchase = models.OneToOneField(  # DB-level guarantee: a purchase is credited at most once
        SmsPackagePurchase, on_delete=models.PROTECT, null=True, blank=True, related_name="lot",
    )
    units_total = models.PositiveIntegerField()
    units_remaining = models.PositiveIntegerField()
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "sms_credit_lots"
        ordering = ["expires_at", "created_at"]
        constraints = [
            models.CheckConstraint(check=models.Q(units_remaining__lte=models.F("units_total")), name="sms_lot_remaining_le_total"),
        ]


class SmsCreditEntry(TenantScopedModel, BaseModel):
    """Immutable credit ledger row. Never updated or deleted — corrections are new entries."""

    KIND_PURCHASE = "purchase"
    KIND_ADJUST_CREDIT = "adjust_credit"
    KIND_ADJUST_DEBIT = "adjust_debit"
    KIND_RESERVE = "reserve"   # message accepted for sending (debit)
    KIND_RELEASE = "release"   # message failed / not chargeable (credit back)
    KIND_EXPIRE = "expire"
    KIND_CHOICES = [(k, k) for k in (KIND_PURCHASE, KIND_ADJUST_CREDIT, KIND_ADJUST_DEBIT, KIND_RESERVE, KIND_RELEASE, KIND_EXPIRE)]

    kind = models.CharField(max_length=15, choices=KIND_CHOICES, db_index=True)
    units = models.IntegerField()  # signed: + credit, − debit
    balance_after = models.IntegerField()
    purchase = models.ForeignKey(SmsPackagePurchase, on_delete=models.PROTECT, null=True, blank=True, related_name="entries")
    lot = models.ForeignKey(SmsCreditLot, on_delete=models.PROTECT, null=True, blank=True, related_name="entries")
    sms_log = models.ForeignKey("integrations.SmsLog", on_delete=models.PROTECT, null=True, blank=True, related_name="credit_entries")
    allocations = models.JSONField(default=dict, blank=True)  # {lot_id: units} drawn/returned
    reason = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "sms_credit_entries"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["purchase"], condition=models.Q(kind="purchase"), name="uniq_sms_credit_per_purchase"),
            models.UniqueConstraint(fields=["sms_log", "kind"], condition=models.Q(kind__in=["reserve", "release"]), name="uniq_sms_credit_per_log_kind"),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("SMS credit ledger entries are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("SMS credit ledger entries are immutable.")
