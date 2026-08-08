from django.db import models
from django.utils import timezone

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class BankReconciliation(TenantScopedModel, BaseModel):
    """Bank / cash account reconciliation against a statement ending balance."""

    STATUS_DRAFT = "draft"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_COMPLETED, "Completed"),
    ]

    account = models.ForeignKey(
        "finance.Account",
        on_delete=models.PROTECT,
        related_name="bank_reconciliations",
    )
    statement_date = models.DateField(db_index=True)
    statement_balance = models.DecimalField(max_digits=18, decimal_places=4)
    book_balance = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True
    )
    notes = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bank_reconciliations_completed",
    )

    class Meta:
        db_table = "finance_bank_reconciliations"
        ordering = ["-statement_date", "-created_at"]

    def __str__(self):
        return f"Rec {self.account_id} @ {self.statement_date}"


class BankStatementLine(BaseModel):
    """A single line from a bank/cash statement within a reconciliation."""

    reconciliation = models.ForeignKey(
        BankReconciliation,
        on_delete=models.CASCADE,
        related_name="statement_lines",
    )
    line_date = models.DateField(db_index=True)
    description = models.CharField(max_length=255, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    # Positive = deposit / money in; negative = withdrawal / money out.
    amount = models.DecimalField(max_digits=18, decimal_places=4)
    matched_journal_line = models.ForeignKey(
        "finance.JournalLine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bank_statement_matches",
    )
    matched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "finance_bank_statement_lines"
        ordering = ["line_date", "created_at"]

    def __str__(self):
        return f"{self.line_date} {self.amount}"

    @property
    def is_matched(self) -> bool:
        return self.matched_journal_line_id is not None
