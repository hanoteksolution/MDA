from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class SmsProvider(TenantScopedModel, BaseModel):
    """An SMS gateway configuration. Only ``MOCK`` and generic ``CUSTOM_HTTP`` exist (D7)."""

    TYPE_MOCK = "MOCK"
    TYPE_CUSTOM_HTTP = "CUSTOM_HTTP"
    TYPE_CHOICES = [(TYPE_MOCK, "Mock (testing)"), (TYPE_CUSTOM_HTTP, "Custom HTTP")]

    name = models.CharField(max_length=120)
    provider_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    # NULL branch = tenant-wide; a branch row overrides it for that branch.
    branch = models.ForeignKey(
        "settings_app.Branch", on_delete=models.CASCADE, null=True, blank=True,
        related_name="sms_providers",
    )
    sender_id = models.CharField(max_length=32, blank=True)
    credential = models.ForeignKey(
        "integrations.IntegrationCredential", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sms_providers",
    )
    # Non-secret adapter settings (url, method, header/body templates, ...). The secret is
    # referenced as the {secret} placeholder and injected at send time only.
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = "sms_providers"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "branch"], condition=models.Q(is_default=True, deleted_at__isnull=True),
                name="uniq_sms_default_per_scope",
            ),
            # NULLs are distinct in a unique index, so the tenant-wide default needs its own.
            models.UniqueConstraint(
                fields=["tenant"],
                condition=models.Q(is_default=True, branch__isnull=True, deleted_at__isnull=True),
                name="uniq_sms_default_tenant_wide",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.provider_type})"


class SmsTemplate(TenantScopedModel, BaseModel):
    code = models.CharField(max_length=60)
    name = models.CharField(max_length=120)
    body = models.TextField()  # "Hi {customer}, your total is {amount}."
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "sms_templates"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], condition=models.Q(deleted_at__isnull=True),
                name="uniq_sms_template_code",
            )
        ]

    def __str__(self):
        return self.code


class SmsLog(TenantScopedModel, BaseModel):
    STATUS_QUEUED = "QUEUED"
    STATUS_RETRYING = "RETRYING"
    STATUS_SENT = "SENT"
    STATUS_FAILED = "FAILED"  # terminal: permanent error or retries exhausted
    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_RETRYING, "Retrying"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
    ]
    TERMINAL = (STATUS_SENT, STATUS_FAILED)

    branch = models.ForeignKey(
        "settings_app.Branch", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sms_logs",
    )
    provider = models.ForeignKey(
        SmsProvider, on_delete=models.SET_NULL, null=True, blank=True, related_name="logs"
    )
    template = models.ForeignKey(
        SmsTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name="logs"
    )
    to_number = models.CharField(max_length=32)
    sender_id = models.CharField(max_length=32, blank=True)
    body = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True)
    provider_reference = models.CharField(max_length=190, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_retry_at = models.DateTimeField(null=True, blank=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error = models.CharField(max_length=300, blank=True)  # sanitised: never contains a secret
    entity_type = models.CharField(max_length=60, blank=True)
    entity_id = models.CharField(max_length=64, blank=True)
    # Reseller credits: units reserved at acceptance, charged on SENT, released on FAILED.
    CREDIT_NONE, CREDIT_RESERVED, CREDIT_CHARGED, CREDIT_RELEASED = "", "reserved", "charged", "released"
    credit_units = models.PositiveSmallIntegerField(default=0)
    credit_state = models.CharField(max_length=10, blank=True, default="")

    class Meta:
        db_table = "sms_logs"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "next_retry_at"], name="idx_sms_retry")]

    def __str__(self):
        return f"{self.to_number} {self.status}"
