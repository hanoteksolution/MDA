"""Cashier session open/close and shift totals."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import F, Sum
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.audit.services.audit_write import write_audit
from apps.organization.models import CashRegister, PosTerminal, StockLocation
from apps.sales.models import CashierSession, Invoice, Payment, SaleRefund
from apps.sales.services.sales_service import _resolve_branch
from core.branching import has_branch_permission, is_branch_manager, resolve_branch_scope
from core.tenancy import apply_tenant_scope, resolve_acting_tenant, stamp_tenant_id


MONEY = Decimal("0.01")


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(MONEY)


MODULE = "pos"


class CashierSessionError(ValueError):
    pass


class CashierSessionService:
    @staticmethod
    def serialize(session: CashierSession) -> dict:
        return {
            "id": str(session.id),
            "branch_id": str(session.branch_id),
            "cashier_id": str(session.cashier_id),
            "cashier_name": session.cashier.get_full_name() or session.cashier.username,
            "opened_at": session.opened_at.isoformat(),
            "closed_at": session.closed_at.isoformat() if session.closed_at else None,
            "opening_float": float(session.opening_float),
            "closing_cash_counted": float(session.closing_cash_counted)
            if session.closing_cash_counted is not None
            else None,
            "expected_cash": float(session.expected_cash) if session.expected_cash is not None else None,
            "cash_variance": float(session.cash_variance) if session.cash_variance is not None else None,
            "total_sales": float(session.total_sales),
            "total_refunds": float(session.total_refunds),
            "status": session.status,
            "notes": session.notes,
            "terminal_id": str(session.terminal_id) if session.terminal_id else None,
            "register_id": str(session.register_id) if session.register_id else None,
            "warehouse_id": str(session.warehouse_id) if session.warehouse_id else None,
            "location_id": str(session.location_id) if session.location_id else None,
            "cash_in": float(session.cash_in),
            "cash_out": float(session.cash_out),
            "variance_reason": session.variance_reason,
            "variance_approved_by_id": (
                str(session.variance_approved_by_id) if session.variance_approved_by_id else None
            ),
            "variance_approved_at": (
                session.variance_approved_at.isoformat() if session.variance_approved_at else None
            ),
        }

    @staticmethod
    def list(*, user=None, request=None, branch_id=None, status=None):
        qs = CashierSession.active_objects().select_related("branch", "cashier")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if user is not None:
            # Tenant scope alone would show every branch's shifts; a forged branch selector is a 403.
            scope = resolve_branch_scope(request=request, user=user, permission="pos.access")
            qs = scope.filter(qs)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-opened_at")

    @staticmethod
    def get_open(*, user, branch_id=None):
        qs = CashierSession.active_objects().filter(
            cashier=user, status=CashierSession.STATUS_OPEN
        )
        qs = apply_tenant_scope(qs, user=user)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs.select_related("branch", "cashier").first()

    # ------------------------------------------------------------------ #
    # Terminal / register resolution (Phase 5)
    # ------------------------------------------------------------------ #

    @staticmethod
    def terminal_required(branch) -> bool:
        """True once a branch has an active terminal: POS is then terminal-enforced.

        Branches that never configured a terminal keep the legacy behaviour (a session
        is optional and stock comes from the branch's default warehouse), so this is
        additive and fail-closed only where an operator has opted in by creating one.
        """
        return PosTerminal.active_objects().filter(branch=branch, status="ACTIVE").exists()

    @staticmethod
    def _find_terminal(*, terminal_id, user):
        try:
            qs = PosTerminal.active_objects().select_related(
                "branch", "default_warehouse", "default_location", "default_cash_register"
            )
            tenant = resolve_acting_tenant(user=user)
            if tenant is not None:
                qs = qs.filter(tenant_id=tenant.pk)
            return qs.filter(pk=terminal_id).first()
        except (ValueError, DjangoValidationError):
            return None

    @staticmethod
    def _resolve_shift_context(*, branch, terminal, register_id):
        """(terminal, register, warehouse, location) for a new shift, or raise."""
        from apps.inventory.models import Warehouse

        if terminal.status != "ACTIVE":
            raise CashierSessionError("This terminal is not active.")

        register = terminal.default_cash_register
        if register_id:
            register = CashRegister.active_objects().filter(pk=register_id).first()
            if register is None or register.tenant_id != terminal.tenant_id:
                raise CashierSessionError("Cash register not found.")
        if register is None:
            raise CashierSessionError(
                "This terminal has no cash register. Assign one before opening a shift."
            )
        if register.branch_id != branch.pk:
            raise CashierSessionError("Cash register does not belong to this branch.")
        if register.status != "ACTIVE":
            raise CashierSessionError("This cash register is not active.")

        warehouse = terminal.default_warehouse
        if warehouse is None:
            warehouse = (
                Warehouse.active_objects().filter(branch=branch, is_default=True).first()
                or Warehouse.active_objects().filter(branch=branch).first()
            )
        if warehouse is None:
            raise CashierSessionError("This terminal has no warehouse to sell from.")

        location = terminal.default_location
        if location is None:
            location = StockLocation.active_objects().filter(
                warehouse=warehouse, is_default=True
            ).first()
        return terminal, register, warehouse, location

    @staticmethod
    @transaction.atomic
    def open_session(
        *,
        user,
        branch_id=None,
        opening_float=0,
        notes="",
        terminal_id=None,
        register_id=None,
        request=None,
    ):
        terminal = None
        if terminal_id:
            terminal = CashierSessionService._find_terminal(terminal_id=terminal_id, user=user)
            if terminal is None:
                raise CashierSessionError("Terminal not found.")
            branch = terminal.branch
            if branch_id and str(branch_id) != str(branch.pk):
                raise CashierSessionError("Terminal does not belong to the selected branch.")
        else:
            branch = _resolve_branch(branch_id, user=user)

        # Untrusted input: the terminal (or branch) may belong to a branch this user
        # cannot act in. Never open a shift there.
        if not has_branch_permission(user, "pos.access", branch):
            raise PermissionDenied("You do not have POS access in this branch.")

        existing = CashierSessionService.get_open(user=user, branch_id=branch.id)
        if existing is not None:
            raise CashierSessionError("Cashier session is already open for this branch.")

        if terminal is None:
            active = list(
                PosTerminal.active_objects().filter(branch=branch, status="ACTIVE")[:2]
            )
            if len(active) > 1:
                raise CashierSessionError("Select a terminal to open the shift on.")
            terminal = active[0] if active else None

        fields = {}
        if terminal is not None:
            terminal, register, warehouse, location = CashierSessionService._resolve_shift_context(
                branch=branch, terminal=terminal, register_id=register_id
            )
            fields = {
                "terminal": terminal,
                "register": register,
                "warehouse": warehouse,
                "location": location,
            }

        payload = stamp_tenant_id(
            {
                "branch": branch,
                "cashier": user,
                "opening_float": _money(opening_float or 0),
                "notes": notes or "",
                "status": CashierSession.STATUS_OPEN,
                **fields,
            },
            user=user,
        )
        try:
            with transaction.atomic():
                session = CashierSession.objects.create(**payload, created_by=user)
        except IntegrityError as exc:
            # uniq_open_session_per_terminal / _per_register: a concurrent open won.
            raise CashierSessionError(
                "This terminal or cash register already has an open shift."
            ) from exc
        write_audit(
            action="create",
            module=MODULE,
            entity=session,
            user=user,
            request=request,
            branch=branch,
            new_values={
                "event": "shift_opened",
                "terminal": str(terminal.pk) if terminal else None,
                "register": str(session.register_id) if session.register_id else None,
                "opening_float": str(session.opening_float),
            },
        )
        return session

    @staticmethod
    def _session_cash_totals(session: CashierSession) -> tuple[Decimal, Decimal, Decimal]:
        invoices = Invoice.active_objects().filter(cashier_session=session)
        sales_total = invoices.aggregate(t=Sum("total_amount"))["t"] or Decimal("0")
        cash_payments = Payment.active_objects().filter(
            invoice__in=invoices, method=Payment.METHOD_CASH
        ).aggregate(t=Sum("amount"))["t"] or Decimal("0")
        refunds = SaleRefund.active_objects().filter(cashier_session=session)
        refund_total = refunds.aggregate(t=Sum("total_amount"))["t"] or Decimal("0")
        return _money(sales_total), _money(cash_payments), _money(refund_total)

    @staticmethod
    def _locked_session(*, session_id, user):
        return (
            CashierSessionService.list(user=user)
            .select_for_update(of=("self",))
            .filter(pk=session_id)
            .first()
        )

    @staticmethod
    @transaction.atomic
    def close_session(*, session_id, user, closing_cash_counted=None, notes="", request=None):
        session = CashierSessionService._locked_session(session_id=session_id, user=user)
        if session is None:
            raise CashierSessionError("Open cashier session not found.")
        if session.status == CashierSession.STATUS_CLOSED:
            raise CashierSessionError("Cashier session is already closed.")
        if session.cashier_id != user.id and not user.has_permission("sales.update"):
            raise CashierSessionError("Only the session cashier or a manager can close this shift.")
        if session.terminal_id and closing_cash_counted is None:
            raise CashierSessionError("Count the drawer: closing cash is required to end a shift.")

        sales_total, cash_payments, refund_total = CashierSessionService._session_cash_totals(session)
        expected = _money(
            session.opening_float
            + cash_payments
            + session.cash_in
            - session.cash_out
            - refund_total
        )
        counted = (
            _money(closing_cash_counted)
            if closing_cash_counted is not None
            else None
        )
        variance = _money(counted - expected) if counted is not None else None

        session.total_sales = sales_total
        session.total_refunds = refund_total
        session.expected_cash = expected
        session.closing_cash_counted = counted
        session.cash_variance = variance
        session.closed_at = timezone.now()
        session.status = CashierSession.STATUS_CLOSED
        if notes:
            session.notes = notes
            if variance:
                session.variance_reason = notes[:255]
        session.updated_by = user
        session.save(
            update_fields=[
                "total_sales",
                "total_refunds",
                "expected_cash",
                "closing_cash_counted",
                "cash_variance",
                "variance_reason",
                "closed_at",
                "status",
                "notes",
                "updated_by",
                "updated_at",
            ]
        )
        write_audit(
            action="update",
            module=MODULE,
            entity=session,
            user=user,
            request=request,
            branch=session.branch,
            new_values={
                "event": "shift_closed",
                "expected_cash": str(expected),
                "counted": str(counted) if counted is not None else None,
                "variance": str(variance) if variance is not None else None,
            },
        )
        if variance:
            CashierSessionService._alert_variance(session, actor=user)
        return session

    @staticmethod
    def _alert_variance(session, *, actor=None):
        """Tell the branch's managers about a cash variance — once per shift."""
        from apps.notifications.models import Notification
        from apps.notifications.services.notification_service import NotificationService

        variance = session.cash_variance
        NotificationService.notify_branch(
            branch=session.branch,
            managers_only=True,
            exclude=actor,
            notification_type=Notification.TYPE_CASH_VARIANCE,
            title=f"Cash variance on shift: {variance}",
            message=(
                f"{session.cashier.get_full_name() or session.cashier.username} closed a shift "
                f"with expected {session.expected_cash} and counted {session.closing_cash_counted}."
            ),
            severity=(
                Notification.SEVERITY_CRITICAL
                if abs(variance) >= Decimal("50")
                else Notification.SEVERITY_WARNING
            ),
            entity_type="cashier_session",
            entity_id=session.pk,
            action_url="/pos/sessions",
            metadata={"session_id": str(session.pk), "variance": str(variance)},
            dedupe_key=f"cash_variance:{session.pk}",
            dedupe_hours=24 * 365,
        )

    @staticmethod
    @transaction.atomic
    def record_cash_movement(*, session_id, user, kind, amount, reason="", request=None):
        """Paid-in / paid-out on an open shift. Both feed the expected drawer cash."""
        if kind not in ("in", "out"):
            raise CashierSessionError("kind must be 'in' or 'out'.")
        amount = _money(amount or 0)
        if amount <= 0:
            raise CashierSessionError("Amount must be positive.")
        if not (reason or "").strip():
            raise CashierSessionError("A reason is required for cash in/out.")
        session = CashierSessionService._locked_session(session_id=session_id, user=user)
        if session is None or session.status != CashierSession.STATUS_OPEN:
            raise CashierSessionError("Open cashier session not found.")
        if session.cashier_id != user.id and not user.has_permission("sales.update"):
            raise CashierSessionError("Only the session cashier or a manager can adjust this drawer.")
        column = "cash_in" if kind == "in" else "cash_out"
        CashierSession.objects.filter(pk=session.pk).update(**{column: F(column) + amount})
        session.refresh_from_db()
        write_audit(
            action="update",
            module=MODULE,
            entity=session,
            user=user,
            request=request,
            branch=session.branch,
            new_values={"event": f"cash_{kind}", "amount": str(amount), "reason": reason.strip()},
        )
        return session

    @staticmethod
    @transaction.atomic
    def approve_variance(*, session_id, user, reason="", request=None):
        """A manager signs off a non-zero cash variance on a closed shift."""
        session = CashierSessionService._locked_session(session_id=session_id, user=user)
        if session is None:
            raise CashierSessionError("Cashier session not found.")
        if session.status != CashierSession.STATUS_CLOSED:
            raise CashierSessionError("Only a closed shift can have its variance approved.")
        if not session.cash_variance:
            raise CashierSessionError("This shift has no cash variance to approve.")
        if session.variance_approved_at is not None:
            raise CashierSessionError("The variance on this shift is already approved.")
        if session.cashier_id == user.id:
            raise CashierSessionError("A cashier cannot approve their own variance.")
        if not is_branch_manager(user, session.branch):
            raise PermissionDenied("Only a branch manager can approve a cash variance.")
        session.variance_approved_by = user
        session.variance_approved_at = timezone.now()
        if reason:
            session.variance_reason = reason[:255]
        session.updated_by = user
        session.save(
            update_fields=[
                "variance_approved_by",
                "variance_approved_at",
                "variance_reason",
                "updated_by",
                "updated_at",
            ]
        )
        write_audit(
            action="update",
            module=MODULE,
            entity=session,
            user=user,
            request=request,
            branch=session.branch,
            new_values={
                "event": "variance_approved",
                "variance": str(session.cash_variance),
                "reason": session.variance_reason,
            },
        )
        return session

    @staticmethod
    def checkout_context(*, branch, session, terminal_id=None):
        """(terminal, warehouse) a sale must use, or raise ``CashierSessionError``.

        A shift bound to a terminal fixes both. A branch with an active terminal but no
        such shift may not sell (B5-1). A branch without terminals keeps legacy behaviour.
        """
        if session is not None and session.branch_id != branch.pk:
            raise CashierSessionError("Cashier session belongs to another branch.")
        if session is not None and session.terminal_id:
            if terminal_id and str(terminal_id) != str(session.terminal_id):
                raise CashierSessionError("Selected terminal does not match the open shift.")
            if session.register_id is None or session.warehouse_id is None:
                raise CashierSessionError(
                    "This shift has no cash register or warehouse. Close it and open a new shift."
                )
            terminal = session.terminal
            if terminal.status != "ACTIVE":
                raise CashierSessionError("This terminal is not active.")
            return terminal, session.warehouse
        if CashierSessionService.terminal_required(branch):
            raise CashierSessionError(
                "Open a shift on a POS terminal and cash register before selling."
            )
        return None, None

    @staticmethod
    def resolve_for_checkout(*, user, session_id=None, branch_id=None):
        if session_id:
            session = (
                CashierSessionService.list(user=user)
                .filter(pk=session_id, status=CashierSession.STATUS_OPEN)
                .first()
            )
            if session is None:
                raise CashierSessionError("Cashier session not found or already closed.")
            if session.cashier_id != user.id:
                raise CashierSessionError("Cannot checkout on another cashier's session.")
            return session
        return CashierSessionService.get_open(user=user, branch_id=branch_id)
