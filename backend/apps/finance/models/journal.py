from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class ImmutableJournalError(ValueError):
    """Raised when mutating a posted journal or its lines."""

    code = "JOURNAL_POSTED_IMMUTABLE"

    def __init__(self, message: str = "Posted journal entries cannot be modified."):
        super().__init__(message)
        self.code = self.__class__.code


class JournalEntry(TenantScopedModel, BaseModel):
    """Posted double-entry journal header."""

    STATUS_DRAFT = "draft"
    STATUS_POSTED = "posted"
    STATUS_VOID = "void"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_POSTED, "Posted"),
        (STATUS_VOID, "Void"),
    ]

    SOURCE_MANUAL = "manual"
    SOURCE_EXPENSE = "expense"
    SOURCE_PAYMENT = "payment"
    SOURCE_INVOICE = "invoice"
    SOURCE_REFUND = "refund"
    SOURCE_PURCHASE = "purchase"
    SOURCE_FUTSAL = "futsal"
    SOURCE_CHOICES = [
        (SOURCE_MANUAL, "Manual"),
        (SOURCE_EXPENSE, "Expense"),
        (SOURCE_PAYMENT, "Payment"),
        (SOURCE_INVOICE, "Invoice"),
        (SOURCE_REFUND, "Refund"),
        (SOURCE_PURCHASE, "Purchase"),
        (SOURCE_FUTSAL, "Futsal"),
    ]

    entry_number = models.CharField(max_length=50, db_index=True)
    entry_date = models.DateField(db_index=True)
    description = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_POSTED, db_index=True
    )
    source_type = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default=SOURCE_MANUAL, db_index=True
    )
    source_module = models.CharField(max_length=30, blank=True, default="", db_index=True)
    source_id = models.UUIDField(null=True, blank=True, db_index=True)
    source_reference = models.CharField(max_length=100, blank=True)
    idempotency_key = models.CharField(max_length=150, blank=True, db_index=True)
    financial_period = models.ForeignKey(
        "finance.FinancialPeriod",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="journal_entries",
    )
    reverses_entry = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reversal_entries",
    )
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="journal_entries",
    )
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_journal_entries",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "finance_journal_entries"
        ordering = ["-entry_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "entry_number"],
                condition=models.Q(deleted_at__isnull=True, tenant__isnull=False),
                name="uniq_fin_je_tenant_number",
            ),
            models.UniqueConstraint(
                fields=["tenant", "idempotency_key"],
                condition=models.Q(
                    deleted_at__isnull=True,
                    tenant__isnull=False,
                    idempotency_key__gt="",
                ),
                name="uniq_fin_je_tenant_idempotency",
            ),
        ]

    def __str__(self):
        return self.entry_number

    def _prior_status(self) -> str | None:
        if not self.pk:
            return None
        return (
            type(self)
            .objects.filter(pk=self.pk)
            .values_list("status", flat=True)
            .first()
        )

    def save(self, *args, **kwargs):
        force = kwargs.pop("force_posted_mutation", False) or getattr(
            self, "_force_posted_mutation", False
        )
        prior = self._prior_status()
        if prior == self.STATUS_POSTED and not force:
            raise ImmutableJournalError(
                "Posted journal entries cannot be modified. Use a reversal."
            )
        super().save(*args, **kwargs)

    def soft_delete(self, user=None):
        if self.status == self.STATUS_POSTED and not getattr(
            self, "_force_posted_mutation", False
        ):
            raise ImmutableJournalError(
                "Posted journal entries cannot be deleted. Use a reversal."
            )
        super().soft_delete(user=user)


class JournalLine(BaseModel):
    """Debit/credit line on a journal entry."""

    entry = models.ForeignKey(
        JournalEntry, on_delete=models.CASCADE, related_name="lines"
    )
    account = models.ForeignKey(
        "finance.Account", on_delete=models.PROTECT, related_name="journal_lines"
    )
    debit = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    credit = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    memo = models.CharField(max_length=255, blank=True)
    cost_center = models.ForeignKey(
        "finance.CostCenter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="journal_lines",
    )
    business_unit = models.ForeignKey(
        "finance.BusinessUnit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="journal_lines",
    )

    class Meta:
        db_table = "finance_journal_lines"
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(debit__gte=0) & models.Q(credit__gte=0),
                name="chk_fin_jl_nonneg",
            ),
            models.CheckConstraint(
                check=~(models.Q(debit__gt=0) & models.Q(credit__gt=0)),
                name="chk_fin_jl_not_both_sides",
            ),
        ]

    def __str__(self):
        return f"{self.entry_id} D{self.debit} C{self.credit}"

    def save(self, *args, **kwargs):
        force = kwargs.pop("force_posted_mutation", False) or getattr(
            self, "_force_posted_mutation", False
        )
        if self.entry_id and not force:
            entry_status = (
                JournalEntry.objects.filter(pk=self.entry_id)
                .values_list("status", flat=True)
                .first()
            )
            if entry_status == JournalEntry.STATUS_POSTED:
                if self.pk:
                    raise ImmutableJournalError(
                        "Posted journal lines cannot be modified. Use a reversal."
                    )
                # Insert into an already-posted entry is also forbidden
                # (create flow attaches lines while entry is still draft).
                raise ImmutableJournalError(
                    "Cannot add lines to a posted journal. Use a reversal."
                )
        super().save(*args, **kwargs)

    def soft_delete(self, user=None):
        if self.entry_id and not getattr(self, "_force_posted_mutation", False):
            entry_status = (
                JournalEntry.objects.filter(pk=self.entry_id)
                .values_list("status", flat=True)
                .first()
            )
            if entry_status == JournalEntry.STATUS_POSTED:
                raise ImmutableJournalError(
                    "Posted journal lines cannot be deleted. Use a reversal."
                )
        super().soft_delete(user=user)
