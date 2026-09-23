"""Physical structure below the branch: locations, registers, terminals.

    Tenant / Company -> Branch -> Warehouse -> StockLocation -> PosTerminal -> CashRegister

These are distinct concepts and are never collapsed: a Branch is not a Warehouse,
a Warehouse is not a StockLocation, a PosTerminal is not a CashRegister.

Per decision D2 the authoritative inventory balance stays at (product, warehouse).
`StockLocation` carries movement-level granularity only; it deliberately supports a
`parent` hierarchy (zone -> aisle -> shelf -> bin) so per-bin balances can be added
later as a *new* balance table keyed (product, location) without re-keying
`inventory.Inventory` or rewriting the domain.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class OrgStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"
    ARCHIVED = "ARCHIVED", "Archived"


class StockLocation(TenantScopedModel, BaseModel):
    """A place inside a warehouse. Movement granularity, not a balance key (D2)."""

    TYPE_STORAGE = "STORAGE"
    TYPE_SHOP_FLOOR = "SHOP_FLOOR"
    TYPE_RECEIVING = "RECEIVING"
    TYPE_DISPATCH = "DISPATCH"
    TYPE_TRANSIT = "TRANSIT"
    TYPE_DAMAGED = "DAMAGED"
    TYPE_RETURN = "RETURN"
    TYPE_OTHER = "OTHER"
    TYPE_CHOICES = [
        (TYPE_STORAGE, "Storage"),
        (TYPE_SHOP_FLOOR, "Shop Floor"),
        (TYPE_RECEIVING, "Receiving"),
        (TYPE_DISPATCH, "Dispatch"),
        (TYPE_TRANSIT, "In Transit"),
        (TYPE_DAMAGED, "Damaged Goods"),
        (TYPE_RETURN, "Returns"),
        (TYPE_OTHER, "Other"),
    ]

    warehouse = models.ForeignKey(
        "inventory.Warehouse", on_delete=models.CASCADE, related_name="locations"
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        help_text="Optional hierarchy (zone -> aisle -> shelf -> bin) for future per-bin stock.",
    )
    code = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=150)
    location_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_STORAGE)
    status = models.CharField(max_length=16, choices=OrgStatus.choices, default=OrgStatus.ACTIVE)
    is_sellable = models.BooleanField(
        default=True, help_text="Stock here may be sold/picked (damaged and transit are not)."
    )
    is_default = models.BooleanField(
        default=False, help_text="Used when a movement does not name a location."
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "stock_locations"
        ordering = ["warehouse__code", "sort_order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["warehouse", "code"],
                condition=models.Q(deleted_at__isnull=True),
                name="stock_location_warehouse_code_unique",
            )
        ]
        indexes = [models.Index(fields=["tenant", "warehouse", "status"])]

    def __str__(self):
        return f"{self.warehouse_id}/{self.code}"

    @property
    def branch_id(self):
        return self.warehouse.branch_id

    def clean(self):
        super().clean()
        if self.parent_id and self.parent.warehouse_id != self.warehouse_id:
            raise ValidationError({"parent": "Parent location must belong to the same warehouse."})
        if self.parent_id == self.pk and self.pk is not None:
            raise ValidationError({"parent": "A location cannot be its own parent."})


class CashRegister(TenantScopedModel, BaseModel):
    """A cash drawer belonging to a branch. Not the same thing as a POS terminal."""

    branch = models.ForeignKey(
        "settings_app.Branch", on_delete=models.CASCADE, related_name="cash_registers"
    )
    code = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=150)
    cash_account = models.ForeignKey(
        "finance.Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cash_registers",
        help_text="Set by finance; never guessed during migration.",
    )
    status = models.CharField(max_length=16, choices=OrgStatus.choices, default=OrgStatus.ACTIVE)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "cash_registers"
        ordering = ["branch__name", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "code"],
                condition=models.Q(deleted_at__isnull=True),
                name="cash_register_branch_code_unique",
            )
        ]
        indexes = [models.Index(fields=["tenant", "branch", "status"])]

    def __str__(self):
        return f"{self.branch_id}/{self.code}"


class PosTerminal(TenantScopedModel, BaseModel):
    """A till/checkout point in a branch. Sells from one warehouse + location."""

    branch = models.ForeignKey(
        "settings_app.Branch", on_delete=models.CASCADE, related_name="pos_terminals"
    )
    code = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=150)
    default_warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pos_terminals",
    )
    default_location = models.ForeignKey(
        StockLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pos_terminals",
    )
    default_cash_register = models.ForeignKey(
        CashRegister,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pos_terminals",
    )
    status = models.CharField(max_length=16, choices=OrgStatus.choices, default=OrgStatus.ACTIVE)
    device_identifier = models.CharField(max_length=190, blank=True)

    class Meta:
        db_table = "pos_terminals"
        ordering = ["branch__name", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "code"],
                condition=models.Q(deleted_at__isnull=True),
                name="pos_terminal_branch_code_unique",
            )
        ]
        indexes = [models.Index(fields=["tenant", "branch", "status"])]

    def __str__(self):
        return f"{self.branch_id}/{self.code}"

    def clean(self):
        super().clean()
        if self.default_warehouse_id and self.default_warehouse.branch_id != self.branch_id:
            raise ValidationError(
                {"default_warehouse": "Warehouse must belong to the terminal's branch."}
            )
        if self.default_location_id and self.default_location.warehouse_id != self.default_warehouse_id:
            raise ValidationError(
                {"default_location": "Location must belong to the terminal's default warehouse."}
            )
        if self.default_cash_register_id and self.default_cash_register.branch_id != self.branch_id:
            raise ValidationError(
                {"default_cash_register": "Cash register must belong to the terminal's branch."}
            )
