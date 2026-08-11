from decimal import Decimal

from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class ProjectBudget(TenantScopedModel, BaseModel):
    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted"
    STATUS_APPROVED = "approved"
    STATUS_LOCKED = "locked"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_LOCKED, "Locked"),
    ]

    project = models.ForeignKey(
        "project_management.Project",
        on_delete=models.CASCADE,
        related_name="budgets",
    )
    version = models.PositiveIntegerField(default=1)
    name = models.CharField(max_length=120)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True
    )
    currency = models.CharField(max_length=8, default="USD")
    total_planned = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    total_committed = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    total_actual = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "project_management_budgets"
        ordering = ["-version", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "version"],
                name="uniq_proj_budget_version",
            ),
        ]

    def recalc_totals(self):
        agg = self.lines.aggregate(
            planned=models.Sum("planned_amount"),
        )
        self.total_planned = Decimal(str(agg["planned"] or 0))
        return self.total_planned

    def __str__(self):
        return f"{self.project.project_code} budget v{self.version}"


class ProjectBudgetLine(TenantScopedModel, BaseModel):
    CAT_LABOR = "labor"
    CAT_MATERIALS = "materials"
    CAT_EQUIPMENT = "equipment"
    CAT_SUBCONTRACT = "subcontract"
    CAT_OVERHEAD = "overhead"
    CAT_OTHER = "other"
    CATEGORY_CHOICES = [
        (CAT_LABOR, "Labor"),
        (CAT_MATERIALS, "Materials"),
        (CAT_EQUIPMENT, "Equipment"),
        (CAT_SUBCONTRACT, "Subcontract"),
        (CAT_OVERHEAD, "Overhead"),
        (CAT_OTHER, "Other"),
    ]

    budget = models.ForeignKey(
        ProjectBudget,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default=CAT_OTHER)
    description = models.CharField(max_length=255)
    planned_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    committed_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    actual_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "project_management_budget_lines"
        ordering = ["sort_order", "created_at"]

    def __str__(self):
        return f"{self.description} ({self.planned_amount})"
