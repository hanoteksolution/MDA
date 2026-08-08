"""Office rental leases on shared PropertyUnit (PHASE 20)."""

from decimal import Decimal

from django.db import models
from django.utils import timezone

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class OfficeTenant(TenantScopedModel, BaseModel):
    """Commercial tenant (company). Optional CRM Customer link."""

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="office_tenants",
        null=True,
        blank=True,
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="office_tenants",
    )
    company_name = models.CharField(max_length=200, db_index=True)
    registration_number = models.CharField(max_length=80, blank=True)
    contact_name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=40, blank=True, db_index=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "office_tenants"
        ordering = ["company_name"]
        indexes = [
            models.Index(
                fields=["tenant", "is_active", "company_name"],
                name="idx_office_tenant_name",
            ),
        ]

    def __str__(self):
        return self.company_name


class OfficeLease(TenantScopedModel, BaseModel):
    STATUS_DRAFT = "draft"
    STATUS_ACTIVE = "active"
    STATUS_EXPIRED = "expired"
    STATUS_TERMINATED = "terminated"
    STATUS_RENEWED = "renewed"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_TERMINATED, "Terminated"),
        (STATUS_RENEWED, "Renewed"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="office_leases",
    )
    unit = models.ForeignKey(
        "property_management.PropertyUnit",
        on_delete=models.PROTECT,
        related_name="office_leases",
    )
    office_tenant = models.ForeignKey(
        OfficeTenant,
        on_delete=models.PROTECT,
        related_name="leases",
    )
    lease_number = models.CharField(max_length=40, db_index=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True
    )
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    rent_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    service_charge = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    deposit_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    deposit_held = models.BooleanField(default=False)
    parking_slots = models.PositiveSmallIntegerField(default=0)
    furnished = models.BooleanField(default=False)
    internet_included = models.BooleanField(default=False)
    electricity_included = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    terminated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "office_leases"
        ordering = ["-start_date", "-created_at"]
        indexes = [
            models.Index(
                fields=["tenant", "status", "start_date"],
                name="idx_office_lease_tenant",
            ),
        ]

    def __str__(self):
        return self.lease_number

    @property
    def monthly_total(self) -> Decimal:
        return Decimal(str(self.rent_amount or 0)) + Decimal(str(self.service_charge or 0))


class OfficeLeaseCharge(TenantScopedModel, BaseModel):
    TYPE_RENT = "rent"
    TYPE_SERVICE = "service"
    TYPE_DEPOSIT = "deposit"
    TYPE_OTHER = "other"
    TYPE_CHOICES = [
        (TYPE_RENT, "Rent"),
        (TYPE_SERVICE, "Service charge"),
        (TYPE_DEPOSIT, "Security deposit"),
        (TYPE_OTHER, "Other"),
    ]

    STATUS_PENDING = "pending"
    STATUS_INVOICED = "invoiced"
    STATUS_PAID = "paid"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_INVOICED, "Invoiced"),
        (STATUS_PAID, "Paid"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    lease = models.ForeignKey(OfficeLease, on_delete=models.CASCADE, related_name="charges")
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="office_lease_charges",
    )
    charge_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default=TYPE_RENT, db_index=True
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True, db_index=True)
    invoice = models.ForeignKey(
        "sales.Invoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="office_lease_charges",
    )
    posted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "office_lease_charges"
        ordering = ["-posted_at", "-created_at"]

    def __str__(self):
        return self.description
