from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class ProjectMilestone(TenantScopedModel, BaseModel):
    """A significant project checkpoint."""

    STATUS_PENDING = "pending"
    STATUS_ACHIEVED = "achieved"
    STATUS_MISSED = "missed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACHIEVED, "Achieved"),
        (STATUS_MISSED, "Missed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    project = models.ForeignKey(
        "project_management.Project", on_delete=models.CASCADE, related_name="milestones"
    )
    wbs_node = models.ForeignKey(
        "project_management.WbsNode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="milestones",
    )
    code = models.CharField(max_length=40, db_index=True)
    name = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    is_critical = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "project_management_milestones"
        ordering = ["sort_order", "due_date", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "code"], name="uniq_project_milestone_code"
            ),
        ]
        indexes = [
            models.Index(fields=["project", "status", "sort_order"], name="idx_milestone_proj_status_sort"),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"
