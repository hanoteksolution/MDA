from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class WasteRecord(TenantScopedModel, BaseModel):
    """Spoilage / spillage log — posts stock adjustments once approved."""

    TYPE_EXPIRED = "expired"
    TYPE_SPOILED = "spoiled"
    TYPE_PREP = "prep"
    TYPE_SPILLAGE = "spillage"
    TYPE_BURNED = "burned"
    TYPE_DAMAGED = "damaged"
    TYPE_EMPLOYEE_MEAL = "employee_meal"
    TYPE_SAMPLE = "sample"
    TYPE_OTHER = "other"
    TYPE_CHOICES = [
        (TYPE_EXPIRED, "Expired"),
        (TYPE_SPOILED, "Spoiled"),
        (TYPE_PREP, "Prep loss"),
        (TYPE_SPILLAGE, "Spillage"),
        (TYPE_BURNED, "Burned"),
        (TYPE_DAMAGED, "Damaged"),
        (TYPE_EMPLOYEE_MEAL, "Employee meal"),
        (TYPE_SAMPLE, "Sample / tasting"),
        (TYPE_OTHER, "Other"),
    ]

    APPROVAL_DRAFT = "draft"
    APPROVAL_APPROVED = "approved"
    APPROVAL_REJECTED = "rejected"
    APPROVAL_CHOICES = [
        (APPROVAL_DRAFT, "Draft"),
        (APPROVAL_APPROVED, "Approved"),
        (APPROVAL_REJECTED, "Rejected"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_waste_records",
    )
    waste_date = models.DateField(default=timezone.localdate, db_index=True)
    ingredient = models.ForeignKey(
        "restaurant.Ingredient",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="waste_records",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restaurant_waste_records",
    )
    menu_item = models.ForeignKey(
        "restaurant.MenuItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="waste_records",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    unit = models.CharField(max_length=30, default="unit")
    unit_cost = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    total_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    waste_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default=TYPE_OTHER, db_index=True
    )
    employee_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restaurant_waste_records",
    )
    reason = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    approval_status = models.CharField(
        max_length=20, choices=APPROVAL_CHOICES, default=APPROVAL_DRAFT, db_index=True
    )
    inventory_adjustment_id = models.UUIDField(null=True, blank=True)
    photo_url = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "restaurant_waste_records"
        ordering = ["-waste_date", "-created_at"]
        indexes = [
            models.Index(
                fields=["tenant", "branch", "waste_type", "waste_date"],
                name="idx_rest_waste_tenant",
            ),
        ]

    def __str__(self):
        return f"{self.waste_type} {self.quantity}{self.unit}"
