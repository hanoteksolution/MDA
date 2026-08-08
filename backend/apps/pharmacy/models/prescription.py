from django.conf import settings
from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class Prescription(TenantScopedModel, BaseModel):
    """Pharmacy Rx header — thin MVP (list/create/dispense status)."""

    STATUS_DRAFT = "draft"
    STATUS_ACTIVE = "active"
    STATUS_DISPENSED = "dispensed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_DISPENSED, "Dispensed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    rx_number = models.CharField(max_length=40, db_index=True)
    patient_name = models.CharField(max_length=200)
    patient_phone = models.CharField(max_length=40, blank=True)
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prescriptions",
    )
    prescribed_by = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True
    )
    prescribed_at = models.DateField(db_index=True)
    dispensed_at = models.DateTimeField(null=True, blank=True)
    dispensed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pharmacy_prescriptions_dispensed",
    )
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pharmacy_prescriptions",
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "pharmacy_prescriptions"
        ordering = ["-prescribed_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "rx_number"],
                condition=models.Q(deleted_at__isnull=True, tenant__isnull=False),
                name="uniq_pharm_rx_tenant_number",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "status", "prescribed_at"],
                name="idx_pharm_rx_tenant_status",
            ),
        ]

    def __str__(self):
        return f"{self.rx_number} — {self.patient_name}"


class PrescriptionLine(BaseModel):
    """Drug line on a prescription (product optional for free-text MVP)."""

    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prescription_lines",
    )
    drug_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100, blank=True)
    frequency = models.CharField(max_length=100, blank=True)
    duration_days = models.PositiveIntegerField(null=True, blank=True)
    quantity = models.DecimalField(max_digits=18, decimal_places=4, default=1)
    quantity_dispensed = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    instructions = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "pharmacy_prescription_lines"
        ordering = ["sort_order", "created_at"]

    @property
    def quantity_remaining(self):
        from decimal import Decimal

        return max(Decimal("0"), Decimal(str(self.quantity or 0)) - Decimal(str(self.quantity_dispensed or 0)))

    def __str__(self):
        return f"{self.drug_name} x {self.quantity}"
