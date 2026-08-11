from django.conf import settings
from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class ProjectTask(TenantScopedModel, BaseModel):
    """A schedulable unit of work belonging to a project."""

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

    STATUS_TODO = "todo"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_BLOCKED = "blocked"
    STATUS_REVIEW = "review"
    STATUS_DONE = "done"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_TODO, "To Do"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_BLOCKED, "Blocked"),
        (STATUS_REVIEW, "Review"),
        (STATUS_DONE, "Done"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    project = models.ForeignKey(
        "project_management.Project", on_delete=models.CASCADE, related_name="tasks"
    )
    wbs_node = models.ForeignKey(
        "project_management.WbsNode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_tasks",
    )
    task_code = models.CharField(max_length=40, db_index=True)
    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM, db_index=True
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_TODO, db_index=True
    )
    planned_start = models.DateField(null=True, blank=True)
    planned_end = models.DateField(null=True, blank=True)
    actual_start = models.DateField(null=True, blank=True)
    actual_end = models.DateField(null=True, blank=True)
    progress_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    estimated_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    actual_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "project_management_tasks"
        ordering = ["sort_order", "task_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "task_code"], name="uniq_project_task_code"
            ),
        ]
        indexes = [
            models.Index(fields=["project", "status", "sort_order"], name="idx_task_proj_status_sort"),
        ]

    def __str__(self):
        return f"{self.task_code} — {self.title}"
