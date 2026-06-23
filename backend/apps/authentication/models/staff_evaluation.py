from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models.base import BaseModel


class StaffEvaluation(BaseModel):
    PERIOD_CHOICES = [
        ("today", "Today"),
        ("week", "This Week"),
        ("month", "This Month"),
        ("year", "This Year"),
    ]

    staff = models.ForeignKey(
        "authentication.User",
        on_delete=models.CASCADE,
        related_name="staff_evaluations",
    )
    evaluator = models.ForeignKey(
        "authentication.User",
        on_delete=models.CASCADE,
        related_name="evaluations_given",
    )
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_evaluations",
    )
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES, db_index=True)
    period_start = models.DateField(db_index=True)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "staff_evaluations"
        ordering = ["-updated_at"]
        unique_together = [["staff", "evaluator", "period", "period_start"]]

    def __str__(self):
        return f"{self.staff_id} — {self.rating}/5 ({self.period})"
