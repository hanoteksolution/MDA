from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class SchoolProfile(TenantScopedModel, BaseModel):
    """School / campus configuration — one row per branch (campus)."""

    CALENDAR_TERMS = "terms"
    CALENDAR_SEMESTERS = "semesters"
    CALENDAR_CUSTOM = "custom"
    CALENDAR_CHOICES = [
        (CALENDAR_TERMS, "Terms"),
        (CALENDAR_SEMESTERS, "Semesters"),
        (CALENDAR_CUSTOM, "Custom"),
    ]

    SCHOOL_PRIMARY = "primary"
    SCHOOL_SECONDARY = "secondary"
    SCHOOL_K12 = "k12"
    SCHOOL_TRAINING = "training"
    SCHOOL_OTHER = "other"
    SCHOOL_TYPE_CHOICES = [
        (SCHOOL_PRIMARY, "Primary"),
        (SCHOOL_SECONDARY, "Secondary"),
        (SCHOOL_K12, "K-12"),
        (SCHOOL_TRAINING, "Training Institution"),
        (SCHOOL_OTHER, "Other"),
    ]

    branch = models.OneToOneField(
        "settings_app.Branch",
        on_delete=models.PROTECT,
        related_name="school_profile",
    )
    display_name = models.CharField(max_length=255, blank=True)
    authority_reference = models.CharField(max_length=100, blank=True)
    grading_scheme = models.CharField(max_length=100, blank=True)
    attendance_mode = models.CharField(max_length=16, choices=[("daily", "Daily"), ("period", "Period"), ("both", "Both")], default="daily")
    status = models.CharField(max_length=16, choices=[("active", "Active"), ("inactive", "Inactive")], default="active")
    allow_term_overlap = models.BooleanField(default=False)
    term_label = models.CharField(max_length=30, default="Term")
    school_name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)
    school_code = models.CharField(max_length=50, blank=True, db_index=True)
    registration_number = models.CharField(max_length=100, blank=True)
    tax_number = models.CharField(max_length=100, blank=True)
    logo_url = models.CharField(max_length=500, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    currency = models.CharField(max_length=8, default="USD")
    language = models.CharField(max_length=16, default="en")
    date_format = models.CharField(max_length=32, default="YYYY-MM-DD")
    academic_calendar_type = models.CharField(
        max_length=20, choices=CALENDAR_CHOICES, default=CALENDAR_TERMS
    )
    school_type = models.CharField(
        max_length=20, choices=SCHOOL_TYPE_CHOICES, default=SCHOOL_K12
    )
    principal_name = models.CharField(max_length=255, blank=True)
    principal_user = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="school_principal_profiles",
    )
    contact_phone = models.CharField(max_length=50, blank=True)
    contact_email = models.EmailField(blank=True)
    settings = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "school_profiles"
        ordering = ["school_name"]
        constraints = [
            models.CheckConstraint(condition=models.Q(tenant__isnull=False), name="school_profile_tenant_required"),
            models.UniqueConstraint(fields=["tenant", "school_code"], condition=~models.Q(school_code=""), name="school_profile_code"),
            models.UniqueConstraint(
                fields=["tenant", "branch"],
                condition=models.Q(deleted_at__isnull=True, tenant__isnull=False),
                name="uniq_school_profile_tenant_branch",
            ),
        ]

    def __str__(self):
        return self.school_name
