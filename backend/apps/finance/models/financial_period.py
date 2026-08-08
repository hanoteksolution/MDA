from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class FiscalYear(TenantScopedModel, BaseModel):
    name = models.CharField(max_length=50)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    is_closed = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "finance_fiscal_years"
        ordering = ["-start_date"]

    def __str__(self):
        return self.name


class FinancialPeriod(TenantScopedModel, BaseModel):
    STATUS_OPEN = "open"
    STATUS_SOFT_CLOSED = "soft_closed"
    STATUS_CLOSED = "closed"
    STATUS_LOCKED = "locked"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_SOFT_CLOSED, "Soft closed"),
        (STATUS_CLOSED, "Closed"),
        (STATUS_LOCKED, "Locked"),
    ]

    fiscal_year = models.ForeignKey(
        FiscalYear,
        on_delete=models.CASCADE,
        related_name="periods",
    )
    name = models.CharField(max_length=50)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
        db_index=True,
    )
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "finance_periods"
        ordering = ["-start_date"]

    def __str__(self):
        return self.name
