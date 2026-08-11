from decimal import Decimal

from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class Boq(TenantScopedModel, BaseModel):
    STATUS_CHOICES = [("draft", "Draft"), ("submitted", "Submitted"), ("approved", "Approved"), ("locked", "Locked")]
    project = models.ForeignKey("project_management.Project", on_delete=models.CASCADE, related_name="boqs")
    version = models.PositiveIntegerField(default=1)
    name = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    currency = models.CharField(max_length=8, default="USD")
    total_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        db_table = "project_management_boqs"
        constraints = [models.UniqueConstraint(fields=["project", "version"], name="uniq_boq_project_version")]
    def recalc_total(self):
        self.total_amount = Decimal(str(self.lines.aggregate(total=models.Sum("amount"))["total"] or 0))
        return self.total_amount


class BoqLine(TenantScopedModel, BaseModel):
    CATEGORY_CHOICES = [("labor", "Labor"), ("materials", "Materials"), ("equipment", "Equipment"), ("subcontract", "Subcontract"), ("other", "Other")]
    boq = models.ForeignKey(Boq, on_delete=models.CASCADE, related_name="lines")
    wbs_node = models.ForeignKey("project_management.WbsNode", on_delete=models.SET_NULL, null=True, blank=True, related_name="boq_lines")
    unit = models.ForeignKey("project_management.ProjectUnit", on_delete=models.SET_NULL, null=True, blank=True, related_name="boq_lines")
    item_code = models.CharField(max_length=40)
    description = models.TextField()
    unit_of_measure = models.CharField(max_length=30, default="unit")
    quantity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    unit_rate = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other")
    sort_order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    class Meta:
        db_table = "project_management_boq_lines"
        ordering = ["sort_order", "item_code"]
