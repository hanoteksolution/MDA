from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class PaymentProviderConfig(TenantScopedModel, BaseModel):
    """A payment gateway configuration. Only ``MOCK`` exists (D7: no invented provider endpoints).

    Two separate secrets, both in the encrypted credential store: ``credential`` (outbound
    API key) and ``webhook_credential`` (the HMAC key that signs inbound webhooks).
    """

    TYPE_MOCK = "MOCK"
    TYPE_CHOICES = [(TYPE_MOCK, "Mock (testing)")]

    name = models.CharField(max_length=120)
    provider_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    branch = models.ForeignKey(  # NULL = tenant-wide
        "settings_app.Branch", on_delete=models.CASCADE, null=True, blank=True,
        related_name="payment_providers",
    )
    credential = models.ForeignKey(
        "integrations.IntegrationCredential", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="payment_providers",
    )
    webhook_credential = models.ForeignKey(
        "integrations.IntegrationCredential", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="payment_webhook_providers",
    )
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "payment_provider_configs"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.provider_type})"


class PaymentIntent(TenantScopedModel, BaseModel):
    """One attempt to collect money for an invoice through a provider.

    The invoice is settled only by :class:`PaymentService.settle`, driven by a verified
    provider confirmation. ``status`` moves along ``TRANSITIONS`` and nowhere else.
    """

    STATUS_CREATED = "created"
    STATUS_PENDING = "pending"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = [
        (STATUS_CREATED, "Created"),
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCEEDED, "Succeeded"),
        (STATUS_FAILED, "Failed"),
        (STATUS_EXPIRED, "Expired"),
    ]
    TRANSITIONS = {
        STATUS_CREATED: {STATUS_PENDING, STATUS_FAILED, STATUS_EXPIRED},
        STATUS_PENDING: {STATUS_SUCCEEDED, STATUS_FAILED, STATUS_EXPIRED},
        STATUS_SUCCEEDED: set(),
        STATUS_FAILED: set(),
        STATUS_EXPIRED: set(),
    }

    invoice = models.ForeignKey("sales.Invoice", on_delete=models.PROTECT, related_name="payment_intents")
    branch = models.ForeignKey(  # stamped from the invoice, never from the caller
        "settings_app.Branch", on_delete=models.PROTECT, related_name="payment_intents"
    )
    provider = models.ForeignKey(
        PaymentProviderConfig, on_delete=models.PROTECT, related_name="intents"
    )
    idempotency_key = models.CharField(max_length=64)
    amount = models.DecimalField(max_digits=18, decimal_places=4)
    currency = models.CharField(max_length=3, default="USD")
    method = models.CharField(max_length=30, default="mobile")  # a sales.Payment method
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_CREATED, db_index=True)
    provider_reference = models.CharField(max_length=190, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    failure_reason = models.CharField(max_length=300, blank=True)
    payment = models.OneToOneField(
        "sales.Payment", on_delete=models.SET_NULL, null=True, blank=True, related_name="payment_intent"
    )
    settled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payment_intents"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "idempotency_key"], name="uniq_payment_intent_key"),
            models.UniqueConstraint(
                fields=["provider", "provider_reference"],
                condition=~models.Q(provider_reference=""),
                name="uniq_payment_intent_provider_ref",
            ),
        ]

    def __str__(self):
        return f"{self.invoice_id}:{self.amount}:{self.status}"


class PaymentWebhookEvent(TenantScopedModel, BaseModel):
    """Every inbound webhook, verified or not, stored raw before anything acts on it."""

    STATUS_RECEIVED = "received"  # verified, not yet processed (or processing failed: retriable)
    STATUS_PROCESSED = "processed"
    STATUS_IGNORED = "ignored"  # verified but nothing to do (unknown intent, other event type)
    STATUS_REJECTED = "rejected"  # signature / timestamp check failed — never acted on
    STATUS_INVALID = "invalid"  # signature fine but body unusable
    STATUS_ERROR = "error"
    STATUS_CHOICES = [(s, s.title()) for s in (
        STATUS_RECEIVED, STATUS_PROCESSED, STATUS_IGNORED, STATUS_REJECTED, STATUS_INVALID, STATUS_ERROR
    )]
    RETRIABLE = (STATUS_RECEIVED, STATUS_ERROR)

    provider = models.ForeignKey(PaymentProviderConfig, on_delete=models.CASCADE, related_name="webhook_events")
    # Only ever set for signature-verified events, so a forger cannot burn a real event id.
    event_id = models.CharField(max_length=190, blank=True)
    signature_valid = models.BooleanField(default=False)
    raw_body = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_RECEIVED, db_index=True)
    reason = models.CharField(max_length=300, blank=True)
    intent = models.ForeignKey(
        PaymentIntent, on_delete=models.SET_NULL, null=True, blank=True, related_name="webhook_events"
    )
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payment_webhook_events"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "event_id"], condition=~models.Q(event_id=""),
                name="uniq_payment_webhook_event",
            )
        ]


class ReconciliationRecord(TenantScopedModel, BaseModel):
    """A provider-vs-ledger discrepancy, recorded for a human. Nothing here fixes itself."""

    KIND_STATUS = "status_mismatch"
    KIND_AMOUNT = "amount_mismatch"
    KIND_MISSING_PAYMENT = "missing_payment"
    KIND_MISSING_JOURNAL = "missing_journal"
    KIND_LATE_SUCCESS = "late_success"  # provider took money after the intent expired/failed
    KIND_UNAPPLIED = "unapplied_payment"  # provider took money the invoice could not absorb
    KIND_CHOICES = [
        (KIND_STATUS, "Status mismatch"),
        (KIND_AMOUNT, "Amount mismatch"),
        (KIND_MISSING_PAYMENT, "Succeeded without a payment"),
        (KIND_MISSING_JOURNAL, "Payment without a journal entry"),
        (KIND_LATE_SUCCESS, "Success after expiry/failure"),
        (KIND_UNAPPLIED, "Money taken but not applied"),
    ]
    STATUS_OPEN = "open"
    STATUS_RESOLVED = "resolved"

    branch = models.ForeignKey(
        "settings_app.Branch", on_delete=models.PROTECT, related_name="payment_reconciliations"
    )
    provider = models.ForeignKey(PaymentProviderConfig, on_delete=models.CASCADE, related_name="reconciliations")
    intent = models.ForeignKey(PaymentIntent, on_delete=models.CASCADE, related_name="reconciliations")
    kind = models.CharField(max_length=24, choices=KIND_CHOICES)
    status = models.CharField(max_length=10, default=STATUS_OPEN, db_index=True)
    provider_status = models.CharField(max_length=20, blank=True)
    provider_amount = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    ledger_status = models.CharField(max_length=20, blank=True)
    ledger_amount = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    detail = models.CharField(max_length=300, blank=True)
    resolved_by = models.ForeignKey(
        "authentication.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "payment_reconciliation_records"
        ordering = ["-created_at"]
        constraints = [
            # One open row per (intent, kind): re-running reconciliation does not pile up duplicates.
            models.UniqueConstraint(
                fields=["intent", "kind"], condition=models.Q(status="open"),
                name="uniq_open_reconciliation",
            )
        ]
