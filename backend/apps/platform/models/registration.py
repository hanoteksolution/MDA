"""Durable public registration and provisioning workflow state."""

from django.db import models

from core.models.base import BaseModel


class RegistrationRequest(BaseModel):
    STATUS_PENDING_EMAIL = "pending_email"
    STATUS_VERIFIED = "verified"
    STATUS_PROVISIONING = "provisioning"
    STATUS_READY = "ready"
    STATUS_FAILED_RETRYABLE = "failed_retryable"
    STATUS_FAILED_FINAL = "failed_final"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING_EMAIL, "Pending email verification"),
        (STATUS_VERIFIED, "Verified"),
        (STATUS_PROVISIONING, "Provisioning"),
        (STATUS_READY, "Ready"),
        (STATUS_FAILED_RETRYABLE, "Failed — retryable"),
        (STATUS_FAILED_FINAL, "Failed — final"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    MODE_TRIAL = "trial"
    MODE_PRODUCTION = "production"
    MODE_DEMO = "demo"
    MODE_INTERNAL = "internal"
    MODE_CHOICES = [
        (MODE_TRIAL, "Trial"),
        (MODE_PRODUCTION, "Production"),
        (MODE_DEMO, "Demo"),
        (MODE_INTERNAL, "Internal"),
    ]

    status = models.CharField(max_length=32, choices=STATUS_CHOICES, db_index=True)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default=MODE_TRIAL)
    email = models.EmailField(db_index=True)
    subdomain = models.SlugField(max_length=63, db_index=True)
    payload = models.JSONField(default=dict)
    payload_fingerprint = models.CharField(max_length=64)
    idempotency_key_hash = models.CharField(max_length=64, unique=True)
    owner_password_hash = models.CharField(max_length=256)
    tenant = models.OneToOneField(
        "platform.Tenant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registration_request",
    )
    failure_category = models.CharField(max_length=64, blank=True)
    failure_message = models.CharField(max_length=500, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    verified_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "registration_requests"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["subdomain"],
                condition=models.Q(
                    deleted_at__isnull=True,
                    status__in=[
                        "pending_email",
                        "verified",
                        "provisioning",
                        "ready",
                    ],
                ),
                name="uniq_live_registration_subdomain",
            )
        ]


class EmailVerification(BaseModel):
    registration = models.ForeignKey(
        RegistrationRequest, on_delete=models.CASCADE, related_name="verifications"
    )
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "registration_email_verifications"
        ordering = ["-created_at"]


class AgreementAcceptance(BaseModel):
    registration = models.ForeignKey(
        RegistrationRequest, on_delete=models.CASCADE, related_name="agreements"
    )
    tenant = models.ForeignKey(
        "platform.Tenant", on_delete=models.SET_NULL, null=True, blank=True
    )
    user = models.ForeignKey(
        "authentication.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    document_type = models.CharField(max_length=32)
    document_version = models.CharField(max_length=64)
    accepted_at = models.DateTimeField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "agreement_acceptances"
        constraints = [
            models.UniqueConstraint(
                fields=["registration", "document_type", "document_version"],
                name="uniq_registration_agreement_version",
            )
        ]


class ProvisioningJob(BaseModel):
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCEEDED, "Succeeded"),
        (STATUS_FAILED, "Failed"),
    ]

    registration = models.ForeignKey(
        RegistrationRequest, on_delete=models.CASCADE, related_name="jobs"
    )
    tenant = models.ForeignKey(
        "platform.Tenant", on_delete=models.SET_NULL, null=True, blank=True
    )
    stage = models.CharField(max_length=64, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, db_index=True)
    attempt = models.PositiveSmallIntegerField(default=1)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failure_category = models.CharField(max_length=64, blank=True)
    safe_message = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "provisioning_jobs"
        ordering = ["created_at"]

