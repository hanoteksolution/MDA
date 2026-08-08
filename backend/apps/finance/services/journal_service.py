"""Journal posting — balanced entries, expense bridge (STEP 21)."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.finance.models import JournalEntry, JournalLine
from apps.finance.models.journal import ImmutableJournalError
from apps.finance.services.chart_service import ChartService
from apps.finance.services.journal_validation_service import (
    JournalValidationError,
    JournalValidationService,
)
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class JournalError(ValueError):
    def __init__(self, message: str, *, code: str | None = None, details: dict | None = None):
        super().__init__(message)
        self.code = code or "JOURNAL_ERROR"
        self.details = details or {}


class JournalService:
    @staticmethod
    def assert_mutable(entry: JournalEntry) -> None:
        if entry.status == JournalEntry.STATUS_POSTED:
            raise JournalError(
                "Posted journal entries cannot be modified. Use a reversal.",
                code="JOURNAL_POSTED_IMMUTABLE",
                details={"entry_id": str(entry.id), "entry_number": entry.entry_number},
            )

    @staticmethod
    def list(*, search=None, date_from=None, date_to=None, user=None, request=None):
        qs = JournalEntry.active_objects().select_related("branch").prefetch_related(
            "lines__account"
        )
        qs = apply_tenant_scope(qs, user=user, request=request)
        if date_from:
            qs = qs.filter(entry_date__gte=date_from)
        if date_to:
            qs = qs.filter(entry_date__lte=date_to)
        if search:
            from django.db.models import Q

            qs = qs.filter(
                Q(description__icontains=search) | Q(entry_number__icontains=search)
            )
        return qs.order_by("-entry_date", "-created_at")

    @staticmethod
    def serialize(entry: JournalEntry) -> dict:
        lines = [
            {
                "id": str(line.id),
                "account_id": str(line.account_id),
                "account_code": line.account.code if line.account_id else "",
                "account_name": line.account.name if line.account_id else "",
                "debit": float(line.debit),
                "credit": float(line.credit),
                "memo": line.memo or "",
                "cost_center_id": str(line.cost_center_id) if line.cost_center_id else None,
                "cost_center_code": (
                    line.cost_center.code if getattr(line, "cost_center_id", None) and line.cost_center_id else ""
                ),
                "business_unit_id": str(line.business_unit_id) if line.business_unit_id else None,
                "business_unit_code": (
                    line.business_unit.code
                    if getattr(line, "business_unit_id", None) and line.business_unit_id
                    else ""
                ),
            }
            for line in entry.lines.filter(deleted_at__isnull=True).select_related(
                "account", "cost_center", "business_unit"
            )
        ]
        total_debit = sum(l["debit"] for l in lines)
        total_credit = sum(l["credit"] for l in lines)
        return {
            "id": str(entry.id),
            "entry_number": entry.entry_number,
            "entry_date": entry.entry_date.isoformat() if entry.entry_date else None,
            "description": entry.description,
            "status": entry.status,
            "source_type": entry.source_type,
            "source_id": str(entry.source_id) if entry.source_id else None,
            "branch_id": str(entry.branch_id) if entry.branch_id else None,
            "notes": entry.notes or "",
            "lines": lines,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "is_balanced": abs(total_debit - total_credit) < 0.0001,
            "reverses_entry_id": str(entry.reverses_entry_id) if entry.reverses_entry_id else None,
            "approved_by_id": str(entry.approved_by_id) if entry.approved_by_id else None,
            "approved_at": entry.approved_at.isoformat() if entry.approved_at else None,
            "created_by_id": str(entry.created_by_id) if entry.created_by_id else None,
        }

    @staticmethod
    def _next_number(*, tenant_id) -> str:
        n = JournalEntry.objects.filter(tenant_id=tenant_id).count() + 1
        return f"JE-{n:05d}"

    @staticmethod
    def _validate_lines(lines) -> tuple[Decimal, Decimal]:
        try:
            return JournalValidationService.validate_lines(lines)
        except JournalValidationError as exc:
            raise JournalError(str(exc), code=exc.code, details=exc.details) from exc

    @staticmethod
    @transaction.atomic
    def create_entry(*, data, user=None, request=None) -> JournalEntry:
        lines_data = data.get("lines") or []
        JournalService._validate_lines(lines_data)

        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id") or data.get("tenant_id")
        if data.get("tenant"):
            tenant_id = data["tenant"].pk
        if not tenant_id:
            raise JournalError("Tenant could not be resolved.", code="JOURNAL_NO_TENANT")

        ChartService.ensure_default_chart(tenant_id=tenant_id, user=user, request=request)

        entry_date = data.get("entry_date") or timezone.localdate()
        if isinstance(entry_date, str):
            from django.utils.dateparse import parse_date

            entry_date = parse_date(entry_date) or timezone.localdate()

        period_id = data.get("financial_period_id")
        if period_id is None and data.get("financial_period"):
            period_id = data["financial_period"].pk

        from apps.finance.services.period_service import (
            CLOSED_STATUSES,
            PeriodError,
            PeriodService,
        )

        try:
            period = PeriodService.resolve(
                tenant_id=tenant_id, on_date=entry_date, user=user
            )
            if period_id is None:
                period_id = period.id
            check_period = period
            if data.get("financial_period_id") or data.get("financial_period"):
                from apps.finance.models import FinancialPeriod

                check_period = (
                    FinancialPeriod.active_objects()
                    .filter(pk=period_id, tenant_id=tenant_id)
                    .first()
                    or period
                )
            if check_period.status in CLOSED_STATUSES:
                raise JournalError(
                    "Transactions cannot be posted to this financial period.",
                    code="FINANCIAL_PERIOD_LOCKED",
                    details={
                        "period_id": str(check_period.id),
                        "status": check_period.status,
                    },
                )
        except PeriodError as exc:
            raise JournalError(str(exc), code="FINANCIAL_PERIOD_ERROR") from exc

        source_type = data.get("source_type") or JournalEntry.SOURCE_MANUAL
        allow_control = source_type != JournalEntry.SOURCE_MANUAL
        target_status = data.get("status") or JournalEntry.STATUS_POSTED
        reverses_entry = data.get("reverses_entry")
        reverses_entry_id = data.get("reverses_entry_id")
        if reverses_entry is not None and reverses_entry_id is None:
            reverses_entry_id = getattr(reverses_entry, "pk", reverses_entry)

        # Create as draft so lines can attach; then promote to posted.
        try:
            entry = JournalEntry.objects.create(
                tenant_id=tenant_id,
                entry_number=JournalService._next_number(tenant_id=tenant_id),
                entry_date=entry_date,
                description=(data.get("description") or "Manual entry").strip(),
                status=JournalEntry.STATUS_DRAFT,
                source_type=source_type,
                source_module=data.get("source_module") or "",
                source_id=data.get("source_id"),
                source_reference=data.get("source_reference") or "",
                idempotency_key=data.get("idempotency_key") or "",
                financial_period_id=period_id,
                reverses_entry_id=reverses_entry_id,
                branch_id=data.get("branch_id"),
                notes=data.get("notes") or "",
                created_by=user,
            )

            for row in lines_data:
                try:
                    account = JournalValidationService.resolve_account(
                        row=row,
                        tenant_id=tenant_id,
                        user=user,
                        request=request,
                        allow_control_manual=allow_control,
                    )
                except JournalValidationError as exc:
                    raise JournalError(str(exc), code=exc.code, details=exc.details) from exc
                cost_center = None
                try:
                    from apps.finance.services.cost_center_service import (
                        CostCenterError,
                        CostCenterService,
                    )

                    cost_center = CostCenterService.resolve_for_line(
                        row=row, tenant_id=tenant_id, user=user, request=request
                    )
                except CostCenterError as exc:
                    raise JournalError(str(exc), code=exc.code) from exc

                business_unit = None
                try:
                    from apps.finance.services.business_unit_service import (
                        BusinessUnitError,
                        BusinessUnitService,
                    )

                    business_unit = BusinessUnitService.resolve_for_line(
                        row=row, tenant_id=tenant_id, user=user, request=request
                    )
                    if business_unit is None:
                        business_unit = BusinessUnitService.resolve_for_source_module(
                            source_module=data.get("source_module") or "",
                            tenant_id=tenant_id,
                            user=user,
                        )
                except BusinessUnitError as exc:
                    raise JournalError(str(exc), code=exc.code) from exc

                JournalLine.objects.create(
                    entry=entry,
                    account=account,
                    debit=Decimal(str(row.get("debit") or 0)),
                    credit=Decimal(str(row.get("credit") or 0)),
                    memo=row.get("memo") or "",
                    cost_center=cost_center,
                    business_unit=business_unit,
                    created_by=user,
                )

            if target_status == JournalEntry.STATUS_POSTED:
                entry.status = JournalEntry.STATUS_POSTED
                entry.approved_by = user
                entry.approved_at = timezone.now()
                entry.save(
                    update_fields=["status", "approved_by", "approved_at", "updated_at"]
                )
            elif target_status != JournalEntry.STATUS_DRAFT:
                entry.status = target_status
                entry.save(update_fields=["status", "updated_at"])
        except ImmutableJournalError as exc:
            raise JournalError(str(exc), code=exc.code) from exc
        return entry

    @staticmethod
    def get(*, entry_id, user=None, request=None) -> JournalEntry:
        qs = JournalEntry.active_objects().prefetch_related("lines__account")
        qs = apply_tenant_scope(qs, user=user, request=request)
        entry = qs.filter(pk=entry_id).first()
        if entry is None:
            raise JournalError("Journal entry not found.", code="JOURNAL_NOT_FOUND")
        return entry

    @staticmethod
    @transaction.atomic
    def post_draft(
        *,
        entry: JournalEntry,
        user=None,
        allow_self_approve: bool = False,
    ) -> JournalEntry:
        """Promote a draft manual journal to posted (maker-checker)."""
        if entry.status != JournalEntry.STATUS_DRAFT:
            raise JournalError(
                "Only draft journals can be approved for posting.",
                code="JOURNAL_NOT_DRAFT",
                details={"status": entry.status},
            )
        if entry.created_by_id and user and entry.created_by_id == getattr(user, "id", None):
            if not allow_self_approve:
                raise JournalError(
                    "Maker cannot approve their own journal. Use a second approver "
                    "or pass allow_self_approve for solo-accountant override.",
                    code="JOURNAL_MAKER_CHECKER",
                    details={
                        "entry_id": str(entry.id),
                        "created_by_id": str(entry.created_by_id),
                    },
                )

        lines = list(entry.lines.filter(deleted_at__isnull=True))
        if len(lines) < 2:
            raise JournalError(
                "Draft journal needs at least two lines before posting.",
                code="JOURNAL_TOO_FEW_LINES",
            )
        try:
            JournalValidationService.validate_lines(
                [
                    {"debit": line.debit, "credit": line.credit}
                    for line in lines
                ]
            )
        except JournalValidationError as exc:
            raise JournalError(str(exc), code=exc.code, details=exc.details) from exc

        from apps.finance.services.period_service import CLOSED_STATUSES, PeriodError, PeriodService

        try:
            period = PeriodService.resolve(
                tenant_id=entry.tenant_id, on_date=entry.entry_date, user=user
            )
            check = entry.financial_period or period
            if check.status in CLOSED_STATUSES:
                raise JournalError(
                    "Transactions cannot be posted to this financial period.",
                    code="FINANCIAL_PERIOD_LOCKED",
                    details={"period_id": str(check.id), "status": check.status},
                )
            if entry.financial_period_id is None:
                entry.financial_period_id = period.id
        except PeriodError as exc:
            raise JournalError(str(exc), code="FINANCIAL_PERIOD_ERROR") from exc

        entry.status = JournalEntry.STATUS_POSTED
        entry.approved_by = user
        entry.approved_at = timezone.now()
        try:
            entry.save(
                update_fields=[
                    "status",
                    "approved_by",
                    "approved_at",
                    "financial_period_id",
                    "updated_at",
                ]
            )
        except ImmutableJournalError as exc:
            raise JournalError(str(exc), code=exc.code) from exc
        return entry

    @staticmethod
    @transaction.atomic
    def discard_draft(*, entry: JournalEntry, user=None) -> None:
        if entry.status != JournalEntry.STATUS_DRAFT:
            raise JournalError(
                "Only draft journals can be discarded.",
                code="JOURNAL_NOT_DRAFT",
                details={"status": entry.status},
            )
        for line in entry.lines.filter(deleted_at__isnull=True):
            line.soft_delete(user=user)
        entry.soft_delete(user=user)

    @staticmethod
    @transaction.atomic
    def post_expense(*, expense, user=None, revision=None) -> JournalEntry | None:
        """Post Dr expense / Cr cash via Central Accounting Engine."""
        from apps.finance.services.posting_service import AccountingPostingService

        return AccountingPostingService.post_expense(
            expense=expense, user=user, revision=revision
        )
