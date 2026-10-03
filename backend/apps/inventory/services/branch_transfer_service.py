"""Inter-branch transfer workflow (Phase 4).

REQUESTED -> APPROVED -> RESERVED -> (DISPATCHED transient) -> IN_TRANSIT -> RECEIVED
-> COMPLETED, plus REJECTED/CANCELLED. See docs/branches/BRANCH_INVENTORY.md §2 for
the Phase 3/4 boundary and docs/branches/STOCK_TRANSFER_WORKFLOW.md for the design.

Reuses InventoryService's existing primitives throughout (reserve_quantity,
unreserve_quantity, dispatch_reserved, receive_transfer_in) rather than duplicating
locking or ledger logic. Same-branch moves are out of scope here — they use
StockTransferService (D4).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.audit.services.audit_write import write_audit
from apps.inventory.models import BranchTransferLine, BranchTransferRequest, Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.products.models import Product
from apps.settings_app.models import Branch
from core.branching import has_branch_permission, resolve_branch_scope
from core.tenancy import apply_tenant_scope, stamp_tenant_id

MODULE = "inventory"
REFERENCE_TYPE = "branch_transfer"


class BranchTransferError(ValueError):
    """Domain validation error for inter-branch transfers."""


@dataclass(frozen=True)
class TransferLineInput:
    product_id: UUID
    quantity: Decimal


def _visible_to(qs, *, user, request=None):
    """Narrow to transfers touching a branch the caller can act in (either end of the move).

    Tenant scoping alone would let a HODAN-only user read a BAKAARO -> MAIN transfer. A forged
    ``branch_id`` selector raises 403 here. Internal callers passing no user are not narrowed.
    """
    if user is None:
        return qs
    scope = resolve_branch_scope(request=request, user=user, permission="inventory.transfer")
    if scope.unscoped:
        return qs
    ids = list(scope.branch_ids)
    return qs.filter(Q(source_branch_id__in=ids) | Q(destination_branch_id__in=ids))


CANCELLABLE_STATUSES = (
    BranchTransferRequest.STATUS_REQUESTED,
    BranchTransferRequest.STATUS_APPROVED,
    BranchTransferRequest.STATUS_RESERVED,
)


def _require_permission(user, codename, branch, action):
    if user is not None and not has_branch_permission(user, codename, branch):
        raise PermissionDenied(f"You cannot {action} for this branch.")



def _unit_cost(product) -> Decimal:
    return Decimal(str(getattr(product, "cost_price", None) or 0))


def _post_transfer_accounting(req, *, event, branch, value, stage_key, user=None):
    """Balance-sheet-only ledger entry for one transfer stage (D8: no revenue, no P&L).

    Runs in the caller's transaction, like purchase receiving: if the ledger refuses
    the entry (e.g. a closed period) the stock movement rolls back with it, so stock
    and ledger cannot drift apart.
    """
    from apps.finance.events import event_types
    from apps.finance.services.posting_service import AccountingPostingService

    AccountingPostingService.post_branch_transfer(
        transfer=req,
        event_type=(
            event_types.TRANSFER_DISPATCHED if event == "dispatched" else event_types.TRANSFER_RECEIVED
        ),
        total=value,
        branch=branch,
        stage_key=stage_key,
        user=user,
    )


def _notify_transfer_event(request_obj, *, event: str, actor=None):
    """Branch-aware notification: only users with access to the relevant branch(es)
    and inventory.transfer are notified — never a tenant-wide broadcast."""
    from apps.notifications.services.notification_service import NotificationService

    branch_map = {
        "requested": [request_obj.source_branch],
        "approved": [request_obj.destination_branch],
        "rejected": [request_obj.destination_branch],
        "reserved": [request_obj.destination_branch],
        "dispatched": [request_obj.destination_branch],
        "received": [request_obj.source_branch],
        "completed": [request_obj.source_branch, request_obj.destination_branch],
        "cancelled": [request_obj.source_branch, request_obj.destination_branch],
    }
    branches = branch_map.get(event, [])
    severity = "WARNING" if event in ("rejected", "cancelled") else "INFO"
    for branch in branches:
        # Once per (request, event) per recipient: the key is not branch-specific, so a user
        # who can act in both branches gets a single alert for "completed"/"cancelled".
        NotificationService.notify_branch(
            branch=branch,
            permission="inventory.transfer",
            exclude=actor,
            notification_type="branch_transfer",
            title=f"Transfer {request_obj.request_number} {event}",
            message=f"{request_obj.source_branch.name} -> {request_obj.destination_branch.name}: {event}.",
            severity=severity,
            entity_type="branch_transfer",
            entity_id=request_obj.pk,
            link=f"/inventory/branch-transfers/{request_obj.pk}/",
            metadata={"request_id": str(request_obj.pk), "event": event},
            dedupe_key=f"branch_transfer:{request_obj.pk}:{event}",
            dedupe_hours=24 * 365,
        )


def tenant_obj_or_id(request_obj):
    from apps.platform.models import Tenant

    return Tenant.objects.filter(pk=request_obj.tenant_id).first()


class BranchTransferService:
    @staticmethod
    def list(*, status=None, branch_id=None, user=None, request=None):
        qs = (
            BranchTransferRequest.active_objects()
            .select_related(
                "source_branch", "destination_branch", "source_warehouse", "destination_warehouse",
                "requested_by", "approved_by", "dispatched_by", "received_by",
            )
            .prefetch_related("lines__product")
        )
        qs = apply_tenant_scope(qs, user=user, request=request)
        qs = _visible_to(qs, user=user, request=request)
        if status:
            qs = qs.filter(status=status)
        if branch_id:
            qs = qs.filter(Q(source_branch_id=branch_id) | Q(destination_branch_id=branch_id))
        return qs.order_by("-created_at")

    @staticmethod
    def _warehouse_for(branch, warehouse_id):
        if warehouse_id:
            return Warehouse.active_objects().get(pk=warehouse_id)
        qs = Warehouse.active_objects().filter(branch_id=branch.pk)
        warehouse = qs.filter(is_default=True).first() or qs.order_by("created_at").first()
        if warehouse is None:
            raise BranchTransferError(f"{branch.name} has no warehouse.")
        return warehouse

    @staticmethod
    def _next_number(*, tenant_id) -> str:
        count = BranchTransferRequest.objects.filter(tenant_id=tenant_id).count() + 1
        return f"BTR-{count:06d}"

    @staticmethod
    @transaction.atomic
    def request_transfer(
        *, source_branch_id, destination_branch_id, source_warehouse_id, destination_warehouse_id,
        lines: Sequence[TransferLineInput], user=None, notes="", approve=False,
    ):
        if str(source_branch_id) == str(destination_branch_id):
            raise BranchTransferError(
                "Source and destination branches must differ; use the same-branch transfer for one branch."
            )
        source_branch = Branch.active_objects().get(pk=source_branch_id)
        destination_branch = Branch.active_objects().get(pk=destination_branch_id)
        if source_branch.tenant_id != destination_branch.tenant_id:
            raise BranchTransferError("Branches must belong to the same tenant.")
        # A warehouse left blank means that branch's default warehouse (a requesting branch
        # does not need to know the other branch's warehouse ids).
        source_wh = BranchTransferService._warehouse_for(source_branch, source_warehouse_id)
        destination_wh = BranchTransferService._warehouse_for(destination_branch, destination_warehouse_id)
        if source_wh.branch_id != source_branch.pk:
            raise BranchTransferError("Source warehouse does not belong to the source branch.")
        if destination_wh.branch_id != destination_branch.pk:
            raise BranchTransferError("Destination warehouse does not belong to the destination branch.")
        # Either end may raise the request: the destination pulls ("Hodan asks Bakaaro") or the
        # source pushes. A request moves no stock; approval and reservation stay with the source.
        if user is not None and not (
            has_branch_permission(user, "inventory.transfer", source_branch)
            or has_branch_permission(user, "inventory.transfer", destination_branch)
        ):
            raise PermissionDenied("You cannot request a transfer for these branches.")
        if not lines:
            raise BranchTransferError("At least one transfer line is required.")

        payload = stamp_tenant_id({}, user=user)
        tenant_id = payload.get("tenant_id") or source_branch.tenant_id

        req = BranchTransferRequest.objects.create(
            tenant_id=tenant_id,
            request_number=BranchTransferService._next_number(tenant_id=tenant_id),
            source_branch=source_branch,
            destination_branch=destination_branch,
            source_warehouse=source_wh,
            destination_warehouse=destination_wh,
            status=BranchTransferRequest.STATUS_REQUESTED,
            notes=notes,
            requested_by=user,
            created_by=user,
        )
        for line in lines:
            qty = Decimal(str(line.quantity))
            if qty <= 0:
                raise BranchTransferError("Transfer quantity must be positive.")
            product = Product.active_objects().get(pk=line.product_id)
            if product.tenant_id and product.tenant_id != source_branch.tenant_id:
                raise BranchTransferError("Product not found.")
            BranchTransferLine.objects.create(
                request=req, product=product, quantity_requested=qty, created_by=user,
            )
        write_audit(action="create", module=MODULE, entity=req, branch=source_branch, user=user,
                    new_values={"request_number": req.request_number, "lines": len(lines)})
        _notify_transfer_event(req, event="requested", actor=user)
        if approve:
            # Push ("send stock to a branch"): the source approves its own outgoing transfer in the
            # same step. Same state machine and the same approve() rule (source permission); stock
            # still moves only at reserve/dispatch, and the destination still receives.
            BranchTransferService.approve(request_id=req.pk, user=user)
        return BranchTransferService.list(user=user).get(pk=req.pk)

    @staticmethod
    @transaction.atomic
    def approve(*, request_id, user=None):
        req = BranchTransferService._locked(request_id, user)
        if req.status in (BranchTransferRequest.STATUS_APPROVED,):
            return req  # idempotent
        if req.status != BranchTransferRequest.STATUS_REQUESTED:
            raise BranchTransferError("Only requested transfers can be approved.")
        _require_permission(user, "inventory.transfer", req.source_branch, "approve this transfer")
        req.status = BranchTransferRequest.STATUS_APPROVED
        req.approved_by = user
        req.approved_at = timezone.now()
        req.updated_by = user
        req.save(update_fields=["status", "approved_by", "approved_at", "updated_by", "updated_at"])
        write_audit(action="update", module=MODULE, entity=req, branch=req.source_branch, user=user,
                    new_values={"status": req.status})
        _notify_transfer_event(req, event="approved", actor=user)
        return req

    @staticmethod
    @transaction.atomic
    def reject(*, request_id, reason="", user=None):
        req = BranchTransferService._locked(request_id, user)
        if req.status == BranchTransferRequest.STATUS_REJECTED:
            return req
        if req.status not in (BranchTransferRequest.STATUS_REQUESTED, BranchTransferRequest.STATUS_APPROVED):
            raise BranchTransferError("Only a requested or approved transfer can be rejected.")
        _require_permission(user, "inventory.transfer", req.source_branch, "reject this transfer")
        req.status = BranchTransferRequest.STATUS_REJECTED
        req.rejection_reason = reason
        req.updated_by = user
        req.save(update_fields=["status", "rejection_reason", "updated_by", "updated_at"])
        write_audit(action="update", module=MODULE, entity=req, branch=req.source_branch, user=user,
                    new_values={"status": req.status, "reason": reason})
        _notify_transfer_event(req, event="rejected", actor=user)
        return req

    @staticmethod
    @transaction.atomic
    def reserve(*, request_id, user=None, allow_negative_available=False):
        req = BranchTransferService._locked(request_id, user)
        if req.status == BranchTransferRequest.STATUS_RESERVED:
            return req  # idempotent
        if req.status != BranchTransferRequest.STATUS_APPROVED:
            raise BranchTransferError("Only an approved transfer can be reserved.")
        _require_permission(user, "inventory.transfer", req.source_branch, "reserve stock for this transfer")

        lines = list(req.lines.select_related("product").order_by("product_id"))
        for line in lines:
            InventoryService.reserve_quantity(
                product=line.product, warehouse=req.source_warehouse, quantity=line.quantity_requested,
                reference_type=REFERENCE_TYPE, reference_id=req.id, user=user,
                allow_negative_available=allow_negative_available,
            )
            line.quantity_reserved = line.quantity_requested
            line.save(update_fields=["quantity_reserved", "updated_at"])

        req.status = BranchTransferRequest.STATUS_RESERVED
        req.reserved_at = timezone.now()
        req.updated_by = user
        req.save(update_fields=["status", "reserved_at", "updated_by", "updated_at"])
        write_audit(action="update", module=MODULE, entity=req, branch=req.source_branch, user=user,
                    new_values={"status": req.status})
        _notify_transfer_event(req, event="reserved", actor=user)
        return req

    @staticmethod
    @transaction.atomic
    def dispatch(*, request_id, user=None):
        """RESERVED -> IN_TRANSIT (DISPATCHED is transient — see model docstring)."""
        req = BranchTransferService._locked(request_id, user)
        if req.status in (BranchTransferRequest.STATUS_IN_TRANSIT, BranchTransferRequest.STATUS_RECEIVED,
                          BranchTransferRequest.STATUS_COMPLETED):
            return req  # idempotent: already dispatched or further along
        if req.status != BranchTransferRequest.STATUS_RESERVED:
            raise BranchTransferError("Only a reserved transfer can be dispatched.")
        _require_permission(user, "inventory.transfer", req.source_branch, "dispatch this transfer")

        lines = list(req.lines.select_related("product").order_by("product_id"))
        for line in lines:
            InventoryService.dispatch_reserved(
                product=line.product, warehouse=req.source_warehouse, quantity=line.quantity_reserved,
                reference_type=REFERENCE_TYPE, reference_id=req.id, user=user,
                notes=f"Dispatch {req.request_number}",
            )
            line.quantity_dispatched = line.quantity_reserved
            line.unit_cost = _unit_cost(line.product)
            line.save(update_fields=["quantity_dispatched", "unit_cost", "updated_at"])

        req.status = BranchTransferRequest.STATUS_IN_TRANSIT
        req.dispatched_by = user
        req.dispatched_at = timezone.now()
        req.updated_by = user
        req.save(update_fields=["status", "dispatched_by", "dispatched_at", "updated_by", "updated_at"])
        write_audit(action="update", module=MODULE, entity=req, branch=req.source_branch, user=user,
                    new_values={"status": req.status})
        _post_transfer_accounting(
            req, event="dispatched", branch=req.source_branch, stage_key="dispatch",
            value=sum((l.quantity_dispatched * (l.unit_cost or 0) for l in lines), Decimal("0")),
            user=user,
        )
        _notify_transfer_event(req, event="dispatched", actor=user)
        return req

    @staticmethod
    @transaction.atomic
    def receive(*, request_id, lines: Sequence[TransferLineInput] | None = None, user=None,
                idempotency_key: str = ""):
        """IN_TRANSIT -> RECEIVED once every line's dispatched quantity is received.
        Partial receipt: pass a subset/partial quantity; the request stays IN_TRANSIT
        and the next call continues. Over-receipt (more than what remains in transit
        for a line) is rejected outright."""
        req = BranchTransferService._locked(request_id, user)
        if req.status in (BranchTransferRequest.STATUS_RECEIVED, BranchTransferRequest.STATUS_COMPLETED):
            return req
        if req.status != BranchTransferRequest.STATUS_IN_TRANSIT:
            raise BranchTransferError("Only an in-transit transfer can be received.")
        if idempotency_key and req.last_receipt_idempotency_key == idempotency_key:
            return req  # B4-10: exact retry, already applied
        _require_permission(user, "inventory.transfer", req.destination_branch, "receive this transfer")

        by_product = {}
        if lines:
            for line in lines:
                qty = Decimal(str(line.quantity))
                if qty <= 0:
                    raise BranchTransferError("Receive quantity must be positive.")
                by_product[str(line.product_id)] = qty

        transfer_lines = list(req.lines.select_related("product").order_by("product_id"))
        received_value = Decimal("0")
        for line in transfer_lines:
            remaining = line.quantity_dispatched - line.quantity_received
            qty = by_product.get(str(line.product_id), remaining) if lines else remaining
            if qty <= 0:
                continue
            if qty > remaining:
                raise BranchTransferError(
                    f"Cannot receive {qty} of {line.product.sku}; only {remaining} in transit."
                )
            InventoryService.receive_transfer_in(
                product=line.product, warehouse=req.destination_warehouse, quantity=qty,
                reference_type=REFERENCE_TYPE, reference_id=req.id, user=user,
                notes=f"Receive {req.request_number}",
            )
            received_value += qty * (line.unit_cost or 0)
            line.quantity_received = line.quantity_received + qty
            line.discrepancy_quantity = line.quantity_dispatched - line.quantity_received
            line.save(update_fields=["quantity_received", "discrepancy_quantity", "updated_at"])

        req.received_by = user
        if idempotency_key:
            req.last_receipt_idempotency_key = idempotency_key
        # Use the just-mutated `transfer_lines`, not req.lines.all() — _locked()'s
        # prefetch_related("lines") cache would return stale (pre-update) rows here.
        fully_received = all(l.quantity_received >= l.quantity_dispatched for l in transfer_lines)
        update_fields = ["received_by", "updated_by", "updated_at"]
        req.updated_by = user
        if idempotency_key:
            update_fields.append("last_receipt_idempotency_key")
        if fully_received:
            req.status = BranchTransferRequest.STATUS_RECEIVED
            req.received_at = timezone.now()
            update_fields += ["status", "received_at"]
        req.save(update_fields=update_fields)
        write_audit(action="update", module=MODULE, entity=req, branch=req.destination_branch, user=user,
                    new_values={"status": req.status})
        _post_transfer_accounting(
            req, event="received", branch=req.destination_branch, value=received_value, user=user,
            stage_key=f"receive:{sum((l.quantity_received for l in transfer_lines), Decimal('0'))}",
        )
        if fully_received:
            _notify_transfer_event(req, event="received", actor=user)
        return req

    @staticmethod
    @transaction.atomic
    def complete(*, request_id, user=None):
        req = BranchTransferService._locked(request_id, user)
        if req.status == BranchTransferRequest.STATUS_COMPLETED:
            return req
        if req.status != BranchTransferRequest.STATUS_RECEIVED:
            raise BranchTransferError("Only a fully received transfer can be completed.")
        _require_permission(user, "inventory.transfer", req.destination_branch, "complete this transfer")
        req.status = BranchTransferRequest.STATUS_COMPLETED
        req.completed_at = timezone.now()
        req.updated_by = user
        req.save(update_fields=["status", "completed_at", "updated_by", "updated_at"])
        write_audit(action="update", module=MODULE, entity=req, branch=req.destination_branch, user=user,
                    new_values={"status": req.status})
        _notify_transfer_event(req, event="completed", actor=user)
        return req

    @staticmethod
    @transaction.atomic
    def cancel(*, request_id, user=None, reason=""):
        """Cancels an open (not yet dispatched) transfer, releasing any reservation.

        Cancellable states are the pre-dispatch ones (``CANCELLABLE_STATUSES``): nothing has left
        the source warehouse, so only a reservation (if any) needs releasing. Either end may
        cancel — the source (it owns the stock) or the requesting destination (it no longer needs
        it). Idempotent: cancelling a cancelled transfer returns it unchanged.
        """
        req = BranchTransferService._locked(request_id, user)
        if req.status == BranchTransferRequest.STATUS_CANCELLED:
            return req
        if req.status not in CANCELLABLE_STATUSES:
            raise BranchTransferError("Only a requested, approved or reserved transfer can be cancelled.")
        if user is not None and not (
            has_branch_permission(user, "inventory.transfer", req.source_branch)
            or has_branch_permission(user, "inventory.transfer", req.destination_branch)
        ):
            raise PermissionDenied("You cannot cancel this transfer.")
        previous_status = req.status

        if req.status == BranchTransferRequest.STATUS_RESERVED:
            for line in req.lines.select_related("product").order_by("product_id"):
                if line.quantity_reserved > 0:
                    InventoryService.unreserve_quantity(
                        product=line.product, warehouse=req.source_warehouse, quantity=line.quantity_reserved,
                        reference_type=REFERENCE_TYPE, reference_id=req.id, user=user,
                    )
                    line.quantity_reserved = Decimal("0")
                    line.save(update_fields=["quantity_reserved", "updated_at"])

        req.status = BranchTransferRequest.STATUS_CANCELLED
        req.updated_by = user
        req.save(update_fields=["status", "updated_by", "updated_at"])
        # The audit row is the cancellation record (who / when / why / from which state): the
        # model has no cancelled_* columns and this deliberately avoids a migration.
        write_audit(action="update", module=MODULE, entity=req, branch=req.source_branch, user=user,
                    old_values={"status": previous_status},
                    new_values={"status": req.status, "event": "transfer_cancelled", "reason": (reason or "")[:250]})
        _notify_transfer_event(req, event="cancelled", actor=user)
        return req

    @staticmethod
    def _locked(request_id, user):
        qs = _visible_to(apply_tenant_scope(BranchTransferRequest.active_objects(), user=user), user=user)
        try:
            return qs.select_for_update().prefetch_related("lines").get(pk=request_id)
        except BranchTransferRequest.DoesNotExist:
            raise NotFound("Transfer not found.")


class ReplenishmentService:
    """Foundation only (item 5): suggests sources and can create a REQUESTED
    transfer, but never approves, reserves, dispatches or receives it — every
    generated request still needs a human to move it forward."""

    @staticmethod
    def suggest_sources(*, rule, exclude_zero=True):
        """Other branches (same tenant) with available stock for the rule's product,
        ranked by available quantity — read-only."""
        from apps.inventory.services.branch_stock_service import aggregate_branch_stock

        candidates = []
        for branch in Branch.active_objects().filter(tenant_id=rule.tenant_id).exclude(pk=rule.branch_id):
            row = aggregate_branch_stock(branch=branch, product=rule.product)
            if not exclude_zero or row["available"] > 0:
                candidates.append(row)
        return sorted(candidates, key=lambda r: r["available"], reverse=True)

    @staticmethod
    @transaction.atomic
    def create_request_from_rule(*, rule, source_branch_id, user=None):
        """Manually (or by an AUTO_CREATE_REQUEST-policy caller) turn a rule into a
        REQUESTED transfer. Quantity = target - current on-hand, capped at what the
        source can supply."""
        from apps.inventory.services.branch_stock_service import aggregate_branch_stock

        destination_stock = aggregate_branch_stock(branch=rule.branch, product=rule.product)
        needed = rule.target_quantity - destination_stock["on_hand"]
        if needed <= 0:
            raise BranchTransferError("Branch is already at or above the target quantity.")
        source_branch = Branch.active_objects().get(pk=source_branch_id)
        source_wh = Warehouse.active_objects().filter(branch=source_branch, is_default=True).first() \
            or Warehouse.active_objects().filter(branch=source_branch).first()
        destination_wh = Warehouse.active_objects().filter(branch=rule.branch, is_default=True).first() \
            or Warehouse.active_objects().filter(branch=rule.branch).first()
        if source_wh is None or destination_wh is None:
            raise BranchTransferError("Source or destination branch has no warehouse.")

        req = BranchTransferService.request_transfer(
            source_branch_id=source_branch.pk,
            destination_branch_id=rule.branch_id,
            source_warehouse_id=source_wh.pk,
            destination_warehouse_id=destination_wh.pk,
            lines=[TransferLineInput(product_id=rule.product_id, quantity=needed)],
            user=user,
            notes=f"Auto-suggested by replenishment rule for {rule.product.sku}",
        )
        BranchTransferRequest.objects.filter(pk=req.pk).update(replenishment_rule=rule)
        return req
