"""Inter-branch transfer workflow (Phase 4). See BRANCH_INVENTORY.md §2 boundary.

Same-branch moves stay on StockTransfer (stock.py). This model is for transfers
between two different branches, with an explicit lifecycle: nothing is dispatched or
received without an intermediate human decision.
"""

from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class BranchTransferRequest(TenantScopedModel, BaseModel):
    STATUS_REQUESTED = "REQUESTED"
    STATUS_APPROVED = "APPROVED"
    STATUS_RESERVED = "RESERVED"
    STATUS_DISPATCHED = "DISPATCHED"  # transient; dispatch_transfer() writes IN_TRANSIT
    STATUS_IN_TRANSIT = "IN_TRANSIT"
    STATUS_RECEIVED = "RECEIVED"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_REJECTED = "REJECTED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_CHOICES = [
        (STATUS_REQUESTED, "Requested"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_RESERVED, "Reserved"),
        (STATUS_DISPATCHED, "Dispatched"),
        (STATUS_IN_TRANSIT, "In Transit"),
        (STATUS_RECEIVED, "Received"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_CANCELLED, "Cancelled"),
    ]
    OPEN_STATUSES = frozenset(
        {STATUS_REQUESTED, STATUS_APPROVED, STATUS_RESERVED, STATUS_IN_TRANSIT}
    )

    request_number = models.CharField(max_length=50, db_index=True)
    source_branch = models.ForeignKey(
        "settings_app.Branch", on_delete=models.PROTECT, related_name="transfer_requests_out"
    )
    destination_branch = models.ForeignKey(
        "settings_app.Branch", on_delete=models.PROTECT, related_name="transfer_requests_in"
    )
    source_warehouse = models.ForeignKey(
        "inventory.Warehouse", on_delete=models.PROTECT, related_name="transfer_requests_out"
    )
    destination_warehouse = models.ForeignKey(
        "inventory.Warehouse", on_delete=models.PROTECT, related_name="transfer_requests_in"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_REQUESTED, db_index=True)
    notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)

    requested_by = models.ForeignKey(
        "authentication.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="branch_transfers_requested",
    )
    approved_by = models.ForeignKey(
        "authentication.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="branch_transfers_approved",
    )
    dispatched_by = models.ForeignKey(
        "authentication.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="branch_transfers_dispatched",
    )
    received_by = models.ForeignKey(
        "authentication.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="branch_transfers_received",
    )

    approved_at = models.DateTimeField(null=True, blank=True)
    reserved_at = models.DateTimeField(null=True, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Idempotency: a repeated receive call with the same key is a no-op (B4-10).
    last_receipt_idempotency_key = models.CharField(max_length=100, blank=True)

    replenishment_rule = models.ForeignKey(
        "inventory.ReplenishmentRule", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="generated_requests",
    )

    class Meta:
        db_table = "branch_transfer_requests"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "request_number"], name="uniq_branch_transfer_request_number"
            ),
        ]

    def __str__(self):
        return self.request_number


class BranchTransferLine(BaseModel):
    request = models.ForeignKey(BranchTransferRequest, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="branch_transfer_lines")
    quantity_requested = models.DecimalField(max_digits=18, decimal_places=4)
    quantity_reserved = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    quantity_dispatched = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    quantity_received = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    # dispatched - received once received is finalised for the line; shortage only —
    # over-receipt is rejected outright, never recorded as a negative discrepancy.
    discrepancy_quantity = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    # Cost per unit fixed at dispatch (Phase 5) so the in-transit clearing account is
    # credited at exactly the value it was debited, whatever cost_price does meanwhile.
    unit_cost = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "branch_transfer_lines"
        constraints = [
            models.UniqueConstraint(fields=["request", "product"], name="uniq_branch_transfer_line_product"),
        ]

    @property
    def in_transit_quantity(self):
        return self.quantity_dispatched - self.quantity_received


class ReplenishmentRule(TenantScopedModel, BaseModel):
    """Foundation only: suggests/creates REQUESTED transfers. Never auto-approves,
    reserves, dispatches, or receives — every generated request still needs a human
    to move it forward (item 5)."""

    POLICY_MANUAL = "MANUAL"
    POLICY_SUGGEST_ONLY = "SUGGEST_ONLY"
    POLICY_AUTO_CREATE_REQUEST = "AUTO_CREATE_REQUEST"
    POLICY_CHOICES = [
        (POLICY_MANUAL, "Manual"),
        (POLICY_SUGGEST_ONLY, "Suggest Only"),
        (POLICY_AUTO_CREATE_REQUEST, "Auto-create Request"),
    ]

    branch = models.ForeignKey("settings_app.Branch", on_delete=models.CASCADE, related_name="replenishment_rules")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="replenishment_rules")
    minimum_quantity = models.DecimalField(max_digits=18, decimal_places=4)
    target_quantity = models.DecimalField(max_digits=18, decimal_places=4)
    policy = models.CharField(max_length=20, choices=POLICY_CHOICES, default=POLICY_SUGGEST_ONLY)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "replenishment_rules"
        constraints = [
            models.UniqueConstraint(fields=["branch", "product"], name="uniq_replenishment_rule_branch_product"),
        ]
