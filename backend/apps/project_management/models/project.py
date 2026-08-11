from decimal import Decimal

from django.conf import settings
from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class Project(TenantScopedModel, BaseModel):
    """Core project record — budgets, WBS, workforce attach in later phases."""

    TYPE_GENERAL = "general"
    TYPE_CONSTRUCTION = "construction"
    TYPE_REAL_ESTATE = "real_estate"
    TYPE_INFRASTRUCTURE = "infrastructure"
    TYPE_IT = "it"
    TYPE_PROFESSIONAL = "professional"
    TYPE_CHOICES = [
        (TYPE_GENERAL, "General"),
        (TYPE_CONSTRUCTION, "Construction"),
        (TYPE_REAL_ESTATE, "Real Estate Development"),
        (TYPE_INFRASTRUCTURE, "Infrastructure"),
        (TYPE_IT, "IT"),
        (TYPE_PROFESSIONAL, "Professional Services"),
    ]

    STATUS_DRAFT = "draft"
    STATUS_PLANNING = "planning"
    STATUS_APPROVED = "approved"
    STATUS_ACTIVE = "active"
    STATUS_ON_HOLD = "on_hold"
    STATUS_AT_RISK = "at_risk"
    STATUS_DELAYED = "delayed"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PLANNING, "Planning"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_ON_HOLD, "On Hold"),
        (STATUS_AT_RISK, "At Risk"),
        (STATUS_DELAYED, "Delayed"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_CLOSED, "Closed"),
    ]

    PRIORITY_LOW = "low"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_HIGH = "high"
    PRIORITY_CRITICAL = "critical"
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, "Low"),
        (PRIORITY_MEDIUM, "Medium"),
        (PRIORITY_HIGH, "High"),
        (PRIORITY_CRITICAL, "Critical"),
    ]

    HEALTH_ON_TRACK = "on_track"
    HEALTH_AT_RISK = "at_risk"
    HEALTH_CRITICAL = "critical"
    HEALTH_UNKNOWN = "unknown"
    HEALTH_CHOICES = [
        (HEALTH_ON_TRACK, "On Track"),
        (HEALTH_AT_RISK, "At Risk"),
        (HEALTH_CRITICAL, "Critical"),
        (HEALTH_UNKNOWN, "Unknown"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="projects",
    )
    client = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )
    project_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_projects",
    )
    cost_center = models.ForeignKey(
        "finance.CostCenter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )

    project_code = models.CharField(max_length=40, db_index=True)
    name = models.CharField(max_length=200, db_index=True)
    project_type = models.CharField(
        max_length=30, choices=TYPE_CHOICES, default=TYPE_GENERAL, db_index=True
    )
    owner_name = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    start_date = models.DateField(null=True, blank=True)
    planned_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True
    )
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM, db_index=True
    )
    health = models.CharField(
        max_length=20, choices=HEALTH_CHOICES, default=HEALTH_UNKNOWN, db_index=True
    )
    progress_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    budget = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    contract_value = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    expected_revenue = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    cost_estimate = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    profit_estimate = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="USD")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    payment_terms = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "project_management_projects"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status", "project_type"], name="idx_proj_tenant_status"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "branch", "project_code"],
                name="uniq_proj_tenant_branch_code",
            ),
        ]

    def __str__(self):
        return f"{self.project_code} — {self.name}"

    def recalc_profit_estimate(self):
        revenue = Decimal(str(self.expected_revenue or 0))
        cost = Decimal(str(self.cost_estimate or 0))
        self.profit_estimate = revenue - cost
