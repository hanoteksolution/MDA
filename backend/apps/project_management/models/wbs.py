from decimal import Decimal

from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class WbsNode(TenantScopedModel, BaseModel):
    """Work Breakdown Structure node — hierarchical project decomposition."""

    TYPE_PHASE = "phase"
    TYPE_DELIVERABLE = "deliverable"
    TYPE_WORK_PACKAGE = "work_package"
    TYPE_ACTIVITY = "activity"
    TYPE_CHOICES = [
        (TYPE_PHASE, "Phase"),
        (TYPE_DELIVERABLE, "Deliverable"),
        (TYPE_WORK_PACKAGE, "Work Package"),
        (TYPE_ACTIVITY, "Activity"),
    ]

    STATUS_NOT_STARTED = "not_started"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_ON_HOLD = "on_hold"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_NOT_STARTED, "Not Started"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_ON_HOLD, "On Hold"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    project = models.ForeignKey(
        "project_management.Project",
        on_delete=models.CASCADE,
        related_name="wbs_nodes",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    code = models.CharField(max_length=40, db_index=True)
    name = models.CharField(max_length=200, db_index=True)
    node_type = models.CharField(
        max_length=30, choices=TYPE_CHOICES, default=TYPE_WORK_PACKAGE, db_index=True
    )
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    level = models.PositiveSmallIntegerField(default=0)

    planned_start = models.DateField(null=True, blank=True)
    planned_end = models.DateField(null=True, blank=True)
    actual_start = models.DateField(null=True, blank=True)
    actual_end = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_NOT_STARTED, db_index=True
    )
    progress_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    estimated_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estimated_cost = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "project_management_wbs_nodes"
        ordering = ["sort_order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "code"],
                name="uniq_wbs_project_code",
            ),
        ]
        indexes = [
            models.Index(fields=["project", "parent", "sort_order"], name="idx_wbs_proj_parent_sort"),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"

    def recalc_level(self):
        self.level = 0 if not self.parent_id else (self.parent.level + 1)
        return self.level
