"""Financial period resolution, close, and reopen."""

from __future__ import annotations

from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from apps.finance.models import FinancialPeriod, FiscalYear
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class PeriodError(ValueError):
    pass


CLOSED_STATUSES = frozenset(
    {FinancialPeriod.STATUS_CLOSED, FinancialPeriod.STATUS_LOCKED}
)


class PeriodService:
    @staticmethod
    def serialize(period: FinancialPeriod) -> dict:
        return {
            "id": str(period.id),
            "name": period.name,
            "start_date": period.start_date.isoformat(),
            "end_date": period.end_date.isoformat(),
            "status": period.status,
            "fiscal_year_id": str(period.fiscal_year_id),
            "fiscal_year_name": period.fiscal_year.name if period.fiscal_year_id else "",
            "closed_at": period.closed_at.isoformat() if period.closed_at else None,
        }

    @staticmethod
    def list(*, user=None, request=None, status=None):
        qs = FinancialPeriod.active_objects().select_related("fiscal_year")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-start_date")

    @staticmethod
    def ensure_open_period(*, tenant_id, user=None, on_date=None) -> FinancialPeriod:
        on_date = PeriodService._as_date(on_date)

        period = (
            FinancialPeriod.active_objects()
            .filter(
                tenant_id=tenant_id,
                start_date__lte=on_date,
                end_date__gte=on_date,
            )
            .select_related("fiscal_year")
            .first()
        )
        if period:
            return period

        year = on_date.year
        fy, _ = FiscalYear.objects.get_or_create(
            tenant_id=tenant_id,
            start_date=date(year, 1, 1),
            defaults={
                "name": f"FY {year}",
                "end_date": date(year, 12, 31),
                "is_closed": False,
                "created_by": user,
            },
        )
        period = FinancialPeriod.objects.create(
            tenant_id=tenant_id,
            fiscal_year=fy,
            name=f"{year}-{on_date.month:02d}",
            start_date=date(year, on_date.month, 1),
            end_date=PeriodService._month_end(year, on_date.month),
            status=FinancialPeriod.STATUS_OPEN,
            created_by=user,
        )
        return period

    @staticmethod
    def resolve(*, tenant_id, on_date=None, user=None) -> FinancialPeriod:
        period = PeriodService.ensure_open_period(tenant_id=tenant_id, user=user, on_date=on_date)
        if period.status in CLOSED_STATUSES:
            raise PeriodError(f"Financial period '{period.name}' is closed.")
        return period

    @staticmethod
    def get(*, period_id, user=None, request=None) -> FinancialPeriod:
        qs = apply_tenant_scope(
            FinancialPeriod.active_objects().select_related("fiscal_year"),
            user=user,
            request=request,
        )
        period = qs.filter(pk=period_id).first()
        if period is None:
            raise PeriodError("Financial period not found.")
        return period

    @staticmethod
    @transaction.atomic
    def soft_close(*, period_id, user=None, request=None) -> FinancialPeriod:
        period = PeriodService.get(period_id=period_id, user=user, request=request)
        if period.status != FinancialPeriod.STATUS_OPEN:
            raise PeriodError("Only open periods can be soft-closed.")
        period.status = FinancialPeriod.STATUS_SOFT_CLOSED
        period.updated_by = user
        period.save(update_fields=["status", "updated_by", "updated_at"])
        return period

    @staticmethod
    @transaction.atomic
    def close(*, period_id, user=None, request=None) -> FinancialPeriod:
        period = PeriodService.get(period_id=period_id, user=user, request=request)
        if period.status not in (
            FinancialPeriod.STATUS_OPEN,
            FinancialPeriod.STATUS_SOFT_CLOSED,
        ):
            raise PeriodError("Period is already closed or locked.")
        period.status = FinancialPeriod.STATUS_CLOSED
        period.closed_at = timezone.now()
        period.updated_by = user
        period.save(update_fields=["status", "closed_at", "updated_by", "updated_at"])
        return period

    @staticmethod
    @transaction.atomic
    def reopen(*, period_id, user=None, request=None) -> FinancialPeriod:
        period = PeriodService.get(period_id=period_id, user=user, request=request)
        if period.status == FinancialPeriod.STATUS_LOCKED:
            raise PeriodError("Locked periods cannot be reopened.")
        if period.status == FinancialPeriod.STATUS_OPEN:
            raise PeriodError("Period is already open.")
        period.status = FinancialPeriod.STATUS_OPEN
        period.closed_at = None
        period.updated_by = user
        period.save(update_fields=["status", "closed_at", "updated_by", "updated_at"])
        return period

    @staticmethod
    @transaction.atomic
    def lock(*, period_id, user=None, request=None) -> FinancialPeriod:
        period = PeriodService.get(period_id=period_id, user=user, request=request)
        if period.status != FinancialPeriod.STATUS_CLOSED:
            raise PeriodError("Only closed periods can be locked.")
        period.status = FinancialPeriod.STATUS_LOCKED
        period.updated_by = user
        period.save(update_fields=["status", "updated_by", "updated_at"])
        return period

    @staticmethod
    def ensure_current(*, user=None, request=None) -> FinancialPeriod:
        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            raise PeriodError("Tenant could not be resolved.")
        return PeriodService.ensure_open_period(tenant_id=tenant_id, user=user)

    @staticmethod
    def _as_date(value):
        if value is None:
            return timezone.localdate()
        if isinstance(value, str):
            from django.utils.dateparse import parse_date

            return parse_date(value) or timezone.localdate()
        if hasattr(value, "date"):
            return value.date()
        return value

    @staticmethod
    def _month_end(year: int, month: int) -> date:
        if month == 12:
            return date(year, 12, 31)
        return date(year, month + 1, 1) - timedelta(days=1)
