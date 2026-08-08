"""Celery jobs for Central Accounting Engine health / dual-run alerts."""

from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.services.notification_service import NotificationService
from apps.platform.models import Tenant
from apps.platform.services.module_service import enabled_module_codes
from core.tenancy import tenant_context

logger = logging.getLogger(__name__)


def _active_tenants():
    return Tenant.active_objects().filter(is_active=True)


@shared_task(name="finance.scan_accounting_health")
def scan_accounting_health():
    """Run ledger health checks per tenant; notify finance users on failures."""
    from apps.finance.services.health_service import AccountingHealthService

    tenants_scanned = 0
    tenants_with_issues = 0
    notifications_created = 0
    critical_tenants = []

    for tenant in _active_tenants():
        codes = enabled_module_codes(tenant=tenant)
        if "finance" not in codes and "accounting" not in codes:
            # Still scan if finance permission users exist — finance is core infra
            pass

        with tenant_context(tenant, enforce=True):
            tenants_scanned += 1
            report = AccountingHealthService.check()
            issues = [c for c in report.get("checks", []) if not c.get("ok")]
            if not issues:
                continue

            tenants_with_issues += 1
            critical = [c for c in issues if c.get("severity")]
            if critical:
                critical_tenants.append(str(tenant.slug or tenant.id))

            status = report.get("status", "degraded")
            summary_bits = [
                f"{c['id']}: {c['message']}" for c in issues[:5]
            ]
            title = (
                f"Accounting {status}: {len(issues)} issue(s)"
                if status != "healthy"
                else "Accounting health warning"
            )
            message = (
                f"Ledger health for {tenant.name} is {status}. "
                + " | ".join(summary_bits)
            )
            if len(issues) > 5:
                message += f" (+{len(issues) - 5} more)"

            today = timezone.localdate().isoformat()
            created = NotificationService.notify_tenant_permission(
                tenant=tenant,
                permission_codename="finance.view",
                notification_type=Notification.TYPE_ACCOUNTING_HEALTH,
                title=title[:200],
                message=message,
                link="/finance",
                metadata={
                    "entity_type": "accounting_health",
                    "status": status,
                    "issue_ids": [c["id"] for c in issues],
                    "summary": report.get("summary"),
                    "as_of": today,
                },
                dedupe_key=f"accounting_health:{tenant.id}:{today}",
                dedupe_hours=20,
            )
            notifications_created += created
            logger.info(
                "accounting_health tenant=%s status=%s issues=%s notifications=%s",
                tenant.slug,
                status,
                len(issues),
                created,
            )

    result = {
        "tenants_scanned": tenants_scanned,
        "tenants_with_issues": tenants_with_issues,
        "notifications_created": notifications_created,
        "critical_tenants": critical_tenants,
    }
    logger.info("accounting_health scan complete: %s", result)
    return result
