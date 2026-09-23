from django.conf import settings
from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class BaristaProfile(TenantScopedModel, BaseModel):
    """Barista / F&B staff record layered on an ERP user account."""

    SKILL_TRAINEE = "trainee"
    SKILL_JUNIOR = "junior"
    SKILL_BARISTA = "barista"
    SKILL_SENIOR = "senior"
    SKILL_LEAD = "lead"
    SKILL_SUPERVISOR = "supervisor"
    SKILL_CHOICES = [
        (SKILL_TRAINEE, "Trainee"),
        (SKILL_JUNIOR, "Junior barista"),
        (SKILL_BARISTA, "Barista"),
        (SKILL_SENIOR, "Senior barista"),
        (SKILL_LEAD, "Lead barista"),
        (SKILL_SUPERVISOR, "Supervisor"),
    ]

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="barista_profiles",
    )
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_barista_profiles",
    )
    barista_code = models.CharField(max_length=40, blank=True, db_index=True)
    skill_level = models.CharField(
        max_length=20, choices=SKILL_CHOICES, default=SKILL_BARISTA
    )
    specialization = models.CharField(max_length=120, blank=True)
    default_station = models.ForeignKey(
        "restaurant.KitchenStation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="baristas",
    )
    employment_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True
    )
    start_date = models.DateField(null=True, blank=True)
    certification = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "restaurant_barista_profiles"
        ordering = ["barista_code", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "branch", "user"],
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_rest_barista_tenant_branch_user",
            ),
        ]

    def __str__(self):
        return self.barista_code or str(self.user_id)
