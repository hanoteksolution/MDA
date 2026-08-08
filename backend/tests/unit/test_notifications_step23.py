"""STEP 23 — notifications app, Celery tasks, API feed."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Role
from apps.gym.models import Member, MembershipPlan, MembershipSubscription
from apps.gym.services.member_service import MemberService
from apps.gym.services.subscription_service import PlanService
from apps.inventory.models import Inventory, Warehouse
from apps.notifications.models import Notification
from apps.notifications.services.notification_service import NotificationService
from apps.notifications.tasks.scheduled import scan_gym_membership_expiry, scan_low_stock
from apps.pharmacy.models import ProductBatch
from apps.platform.models import Tenant
from apps.platform.services.module_service import ensure_default_modules, sync_tenant_modules
from apps.products.models import Category, Product, Unit
from apps.settings_app.models import Branch, Company
from core.tenancy import tenant_context

User = get_user_model()


@pytest.fixture
def notif_env(db):
    ensure_default_modules()
    bootstrap_roles_and_permissions()
    tenant = Tenant.objects.create(
        name="Notif Co", slug="notif-co", status=Tenant.STATUS_ACTIVE
    )
    sync_tenant_modules(tenant=tenant, enabled_codes=["inventory", "gym", "pharmacy"])
    company = Company.objects.create(name="Notif Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="Main", code="MAIN", is_default=True
    )
    admin_role = Role.objects.get(slug="admin")
    user = User.objects.create_user(
        username="notif_admin",
        password="pass-123",
        tenant=tenant,
        branch=branch,
        role=admin_role,
    )
    wh = Warehouse.objects.create(
        branch=branch, tenant=tenant, name="WH", code="WH1", is_default=True
    )
    cat = Category.objects.create(name="General", tenant=tenant)
    unit = Unit.objects.create(name="Piece", abbreviation="pc", tenant=tenant)
    product = Product.objects.create(
        tenant=tenant,
        sku="SKU-LOW",
        name="Low Item",
        category=cat,
        unit=unit,
        cost_price=1,
        selling_price=5,
        minimum_stock=10,
    )
    Inventory.objects.create(
        tenant=tenant,
        product=product,
        warehouse=wh,
        quantity=2,
    )
    member = MemberService.create(data={"full_name": "Exp Member", "tenant": tenant})
    plan = PlanService.create(
        data={"code": "monthly", "name": "Monthly", "duration_days": 30, "price": "50", "tenant": tenant}
    )
    sub = MembershipSubscription.objects.create(
        member=member,
        plan=plan,
        tenant_id=tenant.id,
        status=MembershipSubscription.STATUS_ACTIVE,
        start_date=timezone.localdate(),
        end_date=timezone.localdate() + timedelta(days=3),
        price_paid=50,
    )
    batch_product = Product.objects.create(
        tenant=tenant,
        sku="MED-X",
        name="Med X",
        category=cat,
        unit=unit,
        cost_price=1,
        selling_price=8,
    )
    ProductBatch.objects.create(
        tenant_id=tenant.id,
        product=batch_product,
        warehouse=wh,
        batch_number="LOT-A",
        quantity=5,
        expiry_date=timezone.localdate() + timedelta(days=14),
    )
    return {"tenant": tenant, "user": user, "product": product, "sub": sub}


@pytest.mark.django_db
def test_notification_service_create_and_read(notif_env):
    tenant = notif_env["tenant"]
    user = notif_env["user"]
    with tenant_context(tenant, enforce=True):
        n = NotificationService.notify_user(
            tenant=tenant,
            user=user,
            notification_type=Notification.TYPE_SYSTEM,
            title="Hello",
            message="Test message",
        )
        assert n is not None
        assert NotificationService.unread_count(user=user) == 1
        NotificationService.mark_read(user=user, notification_id=n.id)
        assert NotificationService.unread_count(user=user) == 0


@pytest.mark.django_db
def test_low_stock_task_creates_notification(notif_env):
    tenant = notif_env["tenant"]
    user = notif_env["user"]
    with tenant_context(tenant, enforce=True):
        result = scan_low_stock()
    assert result["notifications_created"] >= 1
    assert Notification.active_objects().filter(
        user=user, notification_type=Notification.TYPE_LOW_STOCK
    ).exists()


@pytest.mark.django_db
def test_gym_expiry_task_warns(notif_env):
    tenant = notif_env["tenant"]
    user = notif_env["user"]
    with tenant_context(tenant, enforce=True):
        result = scan_gym_membership_expiry()
    assert result["warnings_created"] >= 1
    assert Notification.active_objects().filter(
        user=user, notification_type=Notification.TYPE_GYM_EXPIRY
    ).exists()


@pytest.mark.django_db
def test_notification_dedupe(notif_env):
    tenant = notif_env["tenant"]
    user = notif_env["user"]
    with tenant_context(tenant, enforce=True):
        first = NotificationService.notify_user(
            tenant=tenant,
            user=user,
            notification_type=Notification.TYPE_SYSTEM,
            title="Once",
            message="First",
            dedupe_key="test:1",
        )
        second = NotificationService.notify_user(
            tenant=tenant,
            user=user,
            notification_type=Notification.TYPE_SYSTEM,
            title="Once",
            message="Second",
            dedupe_key="test:1",
        )
    assert first is not None
    assert second is None


@pytest.mark.django_db
def test_notifications_api(api_client, notif_env):
    user = notif_env["user"]
    tenant = notif_env["tenant"]
    with tenant_context(tenant, enforce=True):
        NotificationService.notify_user(
            tenant=tenant,
            user=user,
            notification_type=Notification.TYPE_SYSTEM,
            title="API test",
            message="From test",
        )
    api_client.force_authenticate(user=user)
    list_resp = api_client.get("/api/v1/notifications/")
    assert list_resp.status_code == 200
    assert list_resp.data["data"]["count"] >= 1

    count_resp = api_client.get("/api/v1/notifications/unread-count/")
    assert count_resp.status_code == 200
    assert count_resp.data["data"]["count"] >= 1

    notif_id = list_resp.data["data"]["results"][0]["id"]
    read_resp = api_client.post(f"/api/v1/notifications/{notif_id}/read/")
    assert read_resp.status_code == 200
    assert read_resp.data["data"]["is_read"] is True
