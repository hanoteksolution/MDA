"""Scheduled Celery jobs for alerts and lifecycle maintenance."""

from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.gym.models import MembershipSubscription
from apps.gym.services.subscription_service import SubscriptionService
from apps.inventory.models import Inventory
from apps.inventory.services.inventory_service import InventoryService
from apps.notifications.models import Notification
from apps.notifications.services.notification_service import NotificationService
from apps.pharmacy.models import ProductBatch
from apps.platform.models import Tenant
from apps.platform.services.module_service import enabled_module_codes
from core.tenancy import tenant_context


def _active_tenants():
    return Tenant.active_objects().filter(is_active=True)


@shared_task(name="notifications.scan_low_stock")
def scan_low_stock():
    """Notify inventory managers when products are at or below minimum stock."""
    total = 0
    for tenant in _active_tenants():
        codes = enabled_module_codes(tenant=tenant)
        if "inventory" not in codes:
            continue
        with tenant_context(tenant, enforce=True):
            qs = InventoryService.get_reorder_candidates()
            qs = qs.select_related("product", "warehouse")
            for inv in qs[:200]:
                product = inv.product
                dedupe_key = f"low_stock:{inv.id}"
                count = NotificationService.notify_tenant_permission(
                    tenant=tenant,
                    permission_codename="inventory.view",
                    notification_type=Notification.TYPE_LOW_STOCK,
                    title=f"Low stock: {product.name}",
                    message=(
                        f"{product.name} ({product.sku}) is at {inv.quantity} "
                        f"(min {product.minimum_stock}) in {inv.warehouse.name}."
                    ),
                    link="/inventory",
                    metadata={
                        "entity_type": "inventory",
                        "entity_id": str(inv.id),
                        "product_id": str(product.id),
                    },
                    dedupe_key=dedupe_key,
                )
                total += count
    return {"notifications_created": total}


@shared_task(name="notifications.scan_gym_membership_expiry")
def scan_gym_membership_expiry():
    """Expire due subscriptions and warn on memberships ending soon."""
    expired_total = 0
    warned_total = 0
    today = timezone.localdate()
    warn_until = today + timedelta(days=7)

    for tenant in _active_tenants():
        codes = enabled_module_codes(tenant=tenant)
        if "gym" not in codes:
            continue
        with tenant_context(tenant, enforce=True):
            expired_total += SubscriptionService.expire_due(today=today)

            soon_qs = MembershipSubscription.active_objects().filter(
                status__in=[
                    MembershipSubscription.STATUS_ACTIVE,
                    MembershipSubscription.STATUS_FROZEN,
                ],
                end_date__gte=today,
                end_date__lte=warn_until,
            ).select_related("member", "plan")

            for sub in soon_qs[:200]:
                days_left = (sub.end_date - today).days
                dedupe_key = f"gym_sub_expiry:{sub.id}:{sub.end_date.isoformat()}"
                warned_total += NotificationService.notify_tenant_permission(
                    tenant=tenant,
                    permission_codename="gym.manage",
                    notification_type=Notification.TYPE_GYM_EXPIRY,
                    title=f"Membership expiring: {sub.member.full_name}",
                    message=(
                        f"{sub.member.full_name}'s {sub.plan.name} plan expires in "
                        f"{days_left} day(s) on {sub.end_date}."
                    ),
                    link="/gym",
                    metadata={
                        "entity_type": "gym_subscription",
                        "entity_id": str(sub.id),
                        "end_date": sub.end_date.isoformat(),
                    },
                    dedupe_key=dedupe_key,
                    dedupe_hours=168,
                )

    return {"expired": expired_total, "warnings_created": warned_total}


@shared_task(name="notifications.scan_pharmacy_batch_expiry")
def scan_pharmacy_batch_expiry():
    """Warn when pharmacy batches are expiring within 30 days."""
    total = 0
    today = timezone.localdate()
    until = today + timedelta(days=30)

    for tenant in _active_tenants():
        codes = enabled_module_codes(tenant=tenant)
        if "pharmacy" not in codes:
            continue
        with tenant_context(tenant, enforce=True):
            qs = ProductBatch.active_objects().filter(
                is_active=True,
                quantity__gt=0,
                expiry_date__isnull=False,
                expiry_date__gte=today,
                expiry_date__lte=until,
            ).select_related("product", "warehouse")

            for batch in qs[:200]:
                days_left = (batch.expiry_date - today).days
                dedupe_key = f"pharmacy_batch:{batch.id}:{batch.expiry_date.isoformat()}"
                total += NotificationService.notify_tenant_permission(
                    tenant=tenant,
                    permission_codename="pharmacy.view",
                    notification_type=Notification.TYPE_PHARMACY_EXPIRY,
                    title=f"Batch expiring: {batch.product.name}",
                    message=(
                        f"Batch {batch.batch_number} of {batch.product.name} "
                        f"({batch.quantity} units) expires in {days_left} day(s) "
                        f"on {batch.expiry_date}."
                    ),
                    link="/pharmacy",
                    metadata={
                        "entity_type": "product_batch",
                        "entity_id": str(batch.id),
                        "expiry_date": batch.expiry_date.isoformat(),
                    },
                    dedupe_key=dedupe_key,
                    dedupe_hours=168,
                )

    return {"notifications_created": total}


@shared_task(name="notifications.expire_demo_tenants")
def expire_demo_tenants():
    """Mark past-due demo tenants as EXPIRED (checklist demo lifecycle)."""
    from apps.platform.services.demo_tenant_service import DemoTenantService

    due = DemoTenantService.expire_due()
    return {"expired": len(due), "tenant_ids": [str(t.id) for t in due]}


@shared_task(name="notifications.run_all_scheduled_scans")
def run_all_scheduled_scans():
    """Single beat entry that runs all notification scanners."""
    low = scan_low_stock()
    gym = scan_gym_membership_expiry()
    pharmacy = scan_pharmacy_batch_expiry()
    demos = expire_demo_tenants()
    from apps.finance.tasks.accounting_alerts import scan_accounting_health

    accounting = scan_accounting_health()
    return {
        "low_stock": low,
        "gym": gym,
        "pharmacy": pharmacy,
        "demo_tenants": demos,
        "accounting_health": accounting,
    }
