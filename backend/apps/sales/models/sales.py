from decimal import Decimal

from django.db import models
from django.utils import timezone

from core.models.base import BaseModel


class Quotation(BaseModel):
    STATUS_DRAFT = "draft"
    STATUS_SENT = "sent"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"
    STATUS_EXPIRED = "expired"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SENT, "Sent"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    quotation_number = models.CharField(max_length=50, db_index=True)
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="quotations")
    branch = models.ForeignKey("settings_app.Branch", on_delete=models.PROTECT, related_name="quotations")
    created_by_user = models.ForeignKey(
        "authentication.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="quotations"
    )
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    valid_until = models.DateField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    discount_amount = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    tax_amount = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    total_amount = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "quotations"
        ordering = ["-created_at"]
        unique_together = [["branch", "quotation_number"]]

    def __str__(self):
        return self.quotation_number


class QuotationItem(BaseModel):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="quotation_items")
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    unit_price = models.DecimalField(max_digits=18, decimal_places=4)
    line_total = models.DecimalField(max_digits=18, decimal_places=4, default=0)

    class Meta:
        db_table = "quotation_items"

    def save(self, *args, **kwargs):
        self.line_total = Decimal(str(self.quantity)) * Decimal(str(self.unit_price))
        super().save(*args, **kwargs)


class Invoice(BaseModel):
    STATUS_DRAFT = "draft"
    STATUS_SENT = "sent"
    STATUS_PAID = "paid"
    STATUS_OVERDUE = "overdue"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SENT, "Sent"),
        (STATUS_PAID, "Paid"),
        (STATUS_OVERDUE, "Overdue"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    invoice_number = models.CharField(max_length=50, db_index=True)
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="invoices")
    branch = models.ForeignKey("settings_app.Branch", on_delete=models.PROTECT, related_name="invoices")
    quotation = models.ForeignKey(
        Quotation, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices"
    )
    created_by_user = models.ForeignKey(
        "authentication.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices"
    )
    served_by_user = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="served_invoices",
    )
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    issue_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    discount_amount = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    tax_amount = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    total_amount = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    amount_paid = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "invoices"
        ordering = ["-issue_date", "-created_at"]
        unique_together = [["branch", "invoice_number"]]

    def __str__(self):
        return self.invoice_number


class InvoiceItem(BaseModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="invoice_items")
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    unit_price = models.DecimalField(max_digits=18, decimal_places=4)
    line_total = models.DecimalField(max_digits=18, decimal_places=4, default=0)

    class Meta:
        db_table = "invoice_items"

    def save(self, *args, **kwargs):
        self.line_total = Decimal(str(self.quantity)) * Decimal(str(self.unit_price))
        super().save(*args, **kwargs)


class DocumentSequence(BaseModel):
    """Per-branch serial counters for accountable receipt / document numbers."""

    KIND_ORDER_SLIP = "order_slip"
    KIND_HOLD_SLIP = "hold_slip"
    KIND_INVOICE = "invoice"
    KIND_QUOTATION = "quotation"

    KIND_CHOICES = [
        (KIND_ORDER_SLIP, "Order slip"),
        (KIND_HOLD_SLIP, "Hold slip"),
        (KIND_INVOICE, "Invoice"),
        (KIND_QUOTATION, "Quotation"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="document_sequences",
    )
    kind = models.CharField(max_length=32, choices=KIND_CHOICES, db_index=True)
    last_value = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "document_sequences"
        unique_together = [["branch", "kind"]]

    def __str__(self):
        return f"{self.branch_id}:{self.kind}={self.last_value}"


class Expense(BaseModel):
    """Daily operating expense (rent, utilities, supplies, etc.)."""

    CATEGORY_CHOICES = [
        ("utilities", "Utilities"),
        ("rent", "Rent"),
        ("supplies", "Supplies"),
        ("salaries", "Salaries"),
        ("transport", "Transport"),
        ("food", "Food & Beverage"),
        ("maintenance", "Maintenance"),
        ("other", "Other"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch", on_delete=models.PROTECT, related_name="expenses"
    )
    expense_date = models.DateField(default=timezone.localdate, db_index=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="other")
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=18, decimal_places=4)
    notes = models.TextField(blank=True)
    created_by_user = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses_created",
    )

    class Meta:
        db_table = "expenses"
        ordering = ["-expense_date", "-created_at"]

    def __str__(self):
        return f"{self.description} ({self.amount})"
