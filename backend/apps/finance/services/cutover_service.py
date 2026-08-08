"""Per-tenant accounting cutover prepare / activate / status."""

from __future__ import annotations

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.finance.services.backfill_service import AccountingBackfillService
from apps.finance.services.chart_service import ChartService
from apps.finance.services.health_service import AccountingHealthService
from apps.finance.services.mapping_service import MappingService
from apps.finance.services.period_service import PeriodError, PeriodService
from apps.platform.models import Tenant, TenantSettings
from core.tenancy import tenant_context


class CutoverError(ValueError):
    pass


class AccountingCutoverService:
    @staticmethod
    def _settings(tenant_id) -> TenantSettings:
        row, _ = TenantSettings.objects.get_or_create(tenant_id=tenant_id, defaults={})
        return row

    @staticmethod
    def is_engine_enabled_globally() -> bool:
        return bool(getattr(settings, "ACCOUNTING_ENGINE_ENABLED", True))

    @staticmethod
    def is_posting_enabled(*, tenant_id) -> bool:
        if not AccountingCutoverService.is_engine_enabled_globally():
            return False
        row = TenantSettings.objects.filter(tenant_id=tenant_id, deleted_at__isnull=True).first()
        if row is None:
            return True
        return bool(row.accounting_posting_enabled)

    @staticmethod
    def is_strict_after_cutover(*, tenant_id, on_date=None) -> bool:
        """True when journals are mandatory for this tenant on/after cutover."""
        if not getattr(settings, "ACCOUNTING_STRICT_AFTER_CUTOVER", True):
            return False
        if not AccountingCutoverService.is_posting_enabled(tenant_id=tenant_id):
            return False
        row = TenantSettings.objects.filter(tenant_id=tenant_id, deleted_at__isnull=True).first()
        if not row or not row.accounting_cutover_date:
            return False
        on_date = on_date or timezone.localdate()
        if isinstance(on_date, str):
            on_date = parse_date(on_date) or timezone.localdate()
        return on_date >= row.accounting_cutover_date

    @staticmethod
    def status(*, tenant_id) -> dict:
        tenant = Tenant.objects.filter(pk=tenant_id, deleted_at__isnull=True).first()
        if not tenant:
            raise CutoverError("Tenant not found.")

        row = AccountingCutoverService._settings(tenant_id)
        today = timezone.localdate()
        cutover = row.accounting_cutover_date
        phase = "pre_cutover"
        if cutover:
            phase = "live" if today >= cutover else "scheduled"

        with tenant_context(tenant, enforce=True):
            ChartService.ensure_default_chart(tenant_id=tenant_id)
            MappingService.seed_defaults(tenant_id=tenant_id)
            try:
                PeriodService.ensure_current(user=None)
            except PeriodError:
                pass
            health = AccountingHealthService.check()
            backfill = AccountingBackfillService.preview(tenant_id=tenant_id)

        return {
            "tenant_id": str(tenant_id),
            "tenant_slug": tenant.slug,
            "tenant_name": tenant.name,
            "phase": phase,
            "global_engine_enabled": AccountingCutoverService.is_engine_enabled_globally(),
            "posting_enabled": bool(row.accounting_posting_enabled),
            "cutover_date": cutover.isoformat() if cutover else None,
            "strict_after_cutover": AccountingCutoverService.is_strict_after_cutover(
                tenant_id=tenant_id
            ),
            "health_status": health.get("status"),
            "health_summary": health.get("summary"),
            "backfill_pending": backfill.get("counts"),
            "ready": (
                AccountingCutoverService.is_engine_enabled_globally()
                and bool(row.accounting_posting_enabled)
                and health.get("status") in ("healthy", "degraded")
                and health.get("summary", {}).get("errors", 1) == 0
            ),
        }

    @staticmethod
    @transaction.atomic
    def prepare(*, tenant_id, user=None) -> dict:
        """Seed CoA/mappings/periods and return readiness (no cutover date change)."""
        tenant = Tenant.objects.filter(pk=tenant_id, deleted_at__isnull=True).first()
        if not tenant:
            raise CutoverError("Tenant not found.")

        with tenant_context(tenant, enforce=True):
            ChartService.ensure_default_chart(tenant_id=tenant_id, user=user)
            MappingService.seed_defaults(tenant_id=tenant_id, user=user)
            try:
                PeriodService.ensure_current(user=user)
            except PeriodError as exc:
                raise CutoverError(f"Could not ensure financial period: {exc}") from exc

        row = AccountingCutoverService._settings(tenant_id)
        if not row.accounting_posting_enabled:
            row.accounting_posting_enabled = True
            row.updated_by = user
            row.save(update_fields=["accounting_posting_enabled", "updated_by", "updated_at"])

        status = AccountingCutoverService.status(tenant_id=tenant_id)
        status["prepared"] = True
        return status

    @staticmethod
    @transaction.atomic
    def activate(*, tenant_id, cutover_date=None, user=None) -> dict:
        """Set cutover date (default today) and ensure posting is enabled."""
        tenant = Tenant.objects.filter(pk=tenant_id, deleted_at__isnull=True).first()
        if not tenant:
            raise CutoverError("Tenant not found.")

        prepared = AccountingCutoverService.prepare(tenant_id=tenant_id, user=user)
        if prepared.get("health_summary", {}).get("errors", 0):
            raise CutoverError(
                "Cannot activate cutover while critical health errors exist. "
                f"Status={prepared.get('health_status')}."
            )

        if cutover_date is None:
            cutover_date = timezone.localdate()
        elif isinstance(cutover_date, str):
            cutover_date = parse_date(cutover_date)
            if cutover_date is None:
                raise CutoverError("cutover_date must be YYYY-MM-DD.")

        row = AccountingCutoverService._settings(tenant_id)
        row.accounting_cutover_date = cutover_date
        row.accounting_posting_enabled = True
        row.updated_by = user
        row.save(
            update_fields=[
                "accounting_cutover_date",
                "accounting_posting_enabled",
                "updated_by",
                "updated_at",
            ]
        )
        status = AccountingCutoverService.status(tenant_id=tenant_id)
        status["activated"] = True
        return status

    @staticmethod
    @transaction.atomic
    def disable_posting(*, tenant_id, user=None) -> dict:
        """Pilot rollback — skip CAE posting for this tenant."""
        row = AccountingCutoverService._settings(tenant_id)
        row.accounting_posting_enabled = False
        row.updated_by = user
        row.save(update_fields=["accounting_posting_enabled", "updated_by", "updated_at"])
        return AccountingCutoverService.status(tenant_id=tenant_id)
