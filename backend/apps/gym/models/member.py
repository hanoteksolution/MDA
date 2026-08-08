from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class Member(TenantScopedModel, BaseModel):
    """Gym member profile — optional link to CRM Customer."""

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_SUSPENDED = "suspended"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
        (STATUS_SUSPENDED, "Suspended"),
    ]

    GENDER_MALE = "male"
    GENDER_FEMALE = "female"
    GENDER_OTHER = "other"
    GENDER_CHOICES = [
        (GENDER_MALE, "Male"),
        (GENDER_FEMALE, "Female"),
        (GENDER_OTHER, "Other"),
    ]

    membership_number = models.CharField(max_length=50, db_index=True)
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gym_members",
    )
    full_name = models.CharField(max_length=255, db_index=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True, db_index=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    address = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_phone = models.CharField(max_length=50, blank=True)
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gym_members",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True
    )
    joined_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    photo_url = models.CharField(max_length=500, blank=True)
    user = models.OneToOneField(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gym_member_profile",
    )

    class Meta:
        db_table = "gym_members"
        ordering = ["full_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "membership_number"],
                condition=models.Q(deleted_at__isnull=True, tenant__isnull=False),
                name="uniq_gym_member_tenant_number",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "status"], name="idx_gym_member_tenant_status"),
        ]

    def __str__(self):
        return f"{self.membership_number} — {self.full_name}"
