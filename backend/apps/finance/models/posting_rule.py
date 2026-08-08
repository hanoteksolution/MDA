from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class PostingRule(TenantScopedModel, BaseModel):
    """Configurable posting rule — maps event_type to debit/credit mapping keys."""

    event_type = models.CharField(max_length=50, db_index=True)
    business_type_code = models.CharField(max_length=50, blank=True, default="", db_index=True)
    name = models.CharField(max_length=100)
    conditions = models.JSONField(default=dict, blank=True)
    priority = models.PositiveSmallIntegerField(default=100, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "finance_posting_rules"
        ordering = ["priority", "name"]

    def __str__(self):
        return f"{self.event_type}: {self.name}"


class PostingRuleLine(BaseModel):
    SIDE_DEBIT = "debit"
    SIDE_CREDIT = "credit"
    SIDE_CHOICES = [
        (SIDE_DEBIT, "Debit"),
        (SIDE_CREDIT, "Credit"),
    ]

    rule = models.ForeignKey(
        PostingRule,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    side = models.CharField(max_length=10, choices=SIDE_CHOICES)
    mapping_key = models.CharField(max_length=50)
    amount_field = models.CharField(max_length=50, default="amount")
    memo = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "finance_posting_rule_lines"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.side} {self.mapping_key}"
