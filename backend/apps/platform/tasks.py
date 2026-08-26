"""Platform Celery tasks."""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="platform.seed_demo_tenant")
def seed_demo_tenant(tenant_id: str, user_id: str | None = None) -> dict:
    """Background seed for a demo tenant."""
    from django.contrib.auth import get_user_model

    from apps.platform.models import Tenant
    from apps.platform.services.demo_tenant_service import DemoTenantService

    user = None
    if user_id:
        User = get_user_model()
        user = User.objects.filter(pk=user_id).first()

    tenant = Tenant.objects.filter(pk=tenant_id, deleted_at__isnull=True).first()
    if not tenant:
        logger.warning("seed_demo_tenant: tenant %s not found", tenant_id)
        return {"ok": False, "reason": "not_found"}

    return DemoTenantService.run_seed(tenant=tenant, user=user)
