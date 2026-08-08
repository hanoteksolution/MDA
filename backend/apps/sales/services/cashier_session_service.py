"""Cashier session open/close and shift totals."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.sales.models import CashierSession, Invoice, Payment, SaleRefund
from apps.sales.services.sales_service import _resolve_branch
from core.tenancy import apply_tenant_scope, stamp_tenant_id


MONEY = Decimal("0.01")


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(MONEY)


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
        }

    @staticmethod
    def list(*, user=None, request=None, branch_id=None, status=None):
        qs = CashierSession.active_objects().select_related("branch", "cashier")
        qs = apply_tenant_scope(qs, user=user, request=request)
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

    @staticmethod
    @transaction.atomic
    def open_session(*, user, branch_id=None, opening_float=0, notes=""):
        branch = _resolve_branch(branch_id, user=user)
        existing = CashierSessionService.get_open(user=user, branch_id=branch.id)
        if existing is not None:
            raise CashierSessionError("Cashier session is already open for this branch.")

        payload = stamp_tenant_id(
            {
                "branch": branch,
                "cashier": user,
                "opening_float": _money(opening_float or 0),
                "notes": notes or "",
                "status": CashierSession.STATUS_OPEN,
            },
            user=user,
        )
        session = CashierSession.objects.create(**payload, created_by=user)
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
    @transaction.atomic
    def close_session(*, session_id, user, closing_cash_counted=None, notes=""):
        session = (
            CashierSessionService.list(user=user)
            .select_for_update()
            .filter(pk=session_id, status=CashierSession.STATUS_OPEN)
            .first()
        )
        if session is None:
            raise CashierSessionError("Open cashier session not found.")
        if session.cashier_id != user.id and not user.has_permission("sales.update"):
            raise CashierSessionError("Only the session cashier or a manager can close this shift.")

        sales_total, cash_payments, refund_total = CashierSessionService._session_cash_totals(session)
        expected = _money(session.opening_float + cash_payments - refund_total)
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
        session.updated_by = user
        session.save(
            update_fields=[
                "total_sales",
                "total_refunds",
                "expected_cash",
                "closing_cash_counted",
                "cash_variance",
                "closed_at",
                "status",
                "notes",
                "updated_by",
                "updated_at",
            ]
        )
        return session

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
