"""Property management shared kernel (PHASE 18).

PropertyAsset → Building → Unit
Owner, MaintenanceRequest, PropertyDocument
Leases live in housing_rental / office_rental (later).
"""

from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class Owner(TenantScopedModel, BaseModel):
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="property_owners",
        null=True,
        blank=True,
    )
    full_name = models.CharField(max_length=200, db_index=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "property_owners"
        ordering = ["full_name"]
        indexes = [
            models.Index(
                fields=["tenant", "is_active", "full_name"],
                name="idx_prop_owner_tenant",
            ),
        ]

    def __str__(self):
        return self.full_name


class PropertyAsset(TenantScopedModel, BaseModel):
    """Portfolio property (building complex / land parcel)."""

    KIND_RESIDENTIAL = "residential"
    KIND_COMMERCIAL = "commercial"
    KIND_MIXED = "mixed"
    KIND_CHOICES = [
        (KIND_RESIDENTIAL, "Residential"),
        (KIND_COMMERCIAL, "Commercial"),
        (KIND_MIXED, "Mixed"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="property_assets",
    )
    owner = models.ForeignKey(
        Owner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="properties",
    )
    name = models.CharField(max_length=200, db_index=True)
    code = models.CharField(max_length=40, blank=True, db_index=True)
    kind = models.CharField(
        max_length=20, choices=KIND_CHOICES, default=KIND_MIXED, db_index=True
    )
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "property_assets"
        ordering = ["name"]
        indexes = [
            models.Index(
                fields=["tenant", "is_active", "name"],
                name="idx_prop_asset_tenant",
            ),
        ]

    def __str__(self):
        return self.name


class Building(TenantScopedModel, BaseModel):
    property_asset = models.ForeignKey(
        PropertyAsset, on_delete=models.CASCADE, related_name="buildings"
    )
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="property_buildings",
    )
    name = models.CharField(max_length=120, db_index=True)
    code = models.CharField(max_length=40, blank=True, db_index=True)
    floors = models.PositiveSmallIntegerField(default=1)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "property_buildings"
        ordering = ["name"]
        indexes = [
            models.Index(
                fields=["tenant", "is_active", "name"],
                name="idx_prop_bldg_tenant",
            ),
        ]

    def __str__(self):
        return self.name


class PropertyUnit(TenantScopedModel, BaseModel):
    STATUS_VACANT = "vacant"
    STATUS_OCCUPIED = "occupied"
    STATUS_MAINTENANCE = "maintenance"
    STATUS_RESERVED = "reserved"
    STATUS_CHOICES = [
        (STATUS_VACANT, "Vacant"),
        (STATUS_OCCUPIED, "Occupied"),
        (STATUS_MAINTENANCE, "Maintenance"),
        (STATUS_RESERVED, "Reserved"),
    ]

    KIND_RESIDENTIAL = "residential"
    KIND_OFFICE = "office"
    KIND_RETAIL = "retail"
    KIND_OTHER = "other"
    KIND_CHOICES = [
        (KIND_RESIDENTIAL, "Residential"),
        (KIND_OFFICE, "Office"),
        (KIND_RETAIL, "Retail"),
        (KIND_OTHER, "Other"),
    ]

    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="units")
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="property_units",
    )
    code = models.CharField(max_length=40, db_index=True)
    label = models.CharField(max_length=120, blank=True)
    floor = models.CharField(max_length=20, blank=True)
    kind = models.CharField(
        max_length=20, choices=KIND_CHOICES, default=KIND_RESIDENTIAL, db_index=True
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_VACANT, db_index=True
    )
    bedrooms = models.PositiveSmallIntegerField(default=0)
    bathrooms = models.PositiveSmallIntegerField(default=0)
    area_sqm = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    rent_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    deposit_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "property_units"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "building", "code"],
                name="uniq_prop_unit_tenant_building_code",
            ),
        ]

    def __str__(self):
        return self.label or self.code


class MaintenanceRequest(TenantScopedModel, BaseModel):
    STATUS_OPEN = "open"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_DONE = "done"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_DONE, "Done"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    PRIORITY_LOW = "low"
    PRIORITY_NORMAL = "normal"
    PRIORITY_HIGH = "high"
    PRIORITY_URGENT = "urgent"
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, "Low"),
        (PRIORITY_NORMAL, "Normal"),
        (PRIORITY_HIGH, "High"),
        (PRIORITY_URGENT, "Urgent"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="property_maintenance",
    )
    unit = models.ForeignKey(
        PropertyUnit, on_delete=models.CASCADE, related_name="maintenance_requests"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True
    )
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_NORMAL
    )
    reported_by = models.CharField(max_length=120, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "property_maintenance_requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant", "status", "created_at"],
                name="idx_prop_maint_tenant",
            ),
        ]

    def __str__(self):
        return self.title


class PropertyDocument(TenantScopedModel, BaseModel):
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="property_documents",
    )
    property_asset = models.ForeignKey(
        PropertyAsset,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="documents",
    )
    unit = models.ForeignKey(
        PropertyUnit,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="documents",
    )
    title = models.CharField(max_length=200)
    doc_type = models.CharField(max_length=60, blank=True, default="other")
    file_url = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "property_documents"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
