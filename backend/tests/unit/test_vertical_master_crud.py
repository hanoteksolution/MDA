"""Vertical master-data PATCH/DELETE + journal reverse + CoA write + audit."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models.audit_log import AuditLog
from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Permission, Role, UserPermission
from apps.finance.models import Account, JournalEntry
from apps.finance.services.chart_service import ChartService
from apps.finance.services.journal_service import JournalService
from apps.finance.services.mapping_service import MappingService
from apps.hotel.models import Guest, Reservation, Room, RoomType
from apps.platform.models import Tenant
from apps.platform.services.module_service import sync_tenant_modules
from apps.platform.services.platform_service import PlatformService
from apps.property_management.models import PropertyUnit
from apps.restaurant.models import DiningTable, MenuCategory, MenuItem
from apps.settings_app.models import Branch, Company
from django.utils import timezone


@pytest.fixture
def crud_env(db):
    bootstrap_roles_and_permissions()
    PlatformService.ensure_default_business_types()
    tenant = Tenant.objects.create(name="CRUD Co", slug="crud-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="CRUD Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="HQ", code="HQ", is_default=True
    )
    sync_tenant_modules(
        tenant=tenant,
        enabled_codes=[
            "restaurant",
            "hotel",
            "property_management",
            "housing_rental",
            "office_rental",
            "gym",
            "finance",
        ],
        validate_dependencies=False,
    )
    user = get_user_model().objects.create_user(
        username="crud_admin",
        password="pass12345",
        tenant=tenant,
        branch=branch,
        role=Role.objects.get(slug="super_admin"),
    )
    ChartService.ensure_default_chart(tenant_id=tenant.id, user=user)
    MappingService.seed_defaults(tenant_id=tenant.id, user=user)
    return {"tenant": tenant, "branch": branch, "user": user}


def _client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.mark.django_db
def test_restaurant_menu_and_table_patch_delete(crud_env):
    client = _client(crud_env["user"])
    branch_id = str(crud_env["branch"].id)
    cat = client.post(
        "/api/v1/restaurant/categories/",
        {"name": "Mains", "branch_id": branch_id},
        format="json",
    )
    assert cat.status_code == 201, cat.content
    cat_id = cat.json()["data"]["id"]
    patched = client.patch(
        f"/api/v1/restaurant/categories/{cat_id}/",
        {"name": "Main Courses"},
        format="json",
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["name"] == "Main Courses"

    item = client.post(
        "/api/v1/restaurant/items/",
        {
            "name": "Steak",
            "branch_id": branch_id,
            "category_id": cat_id,
            "unit_price": "12.50",
        },
        format="json",
    )
    assert item.status_code == 201
    item_id = item.json()["data"]["id"]
    assert (
        client.patch(
            f"/api/v1/restaurant/items/{item_id}/",
            {"unit_price": "15.00"},
            format="json",
        ).status_code
        == 200
    )
    assert client.delete(f"/api/v1/restaurant/items/{item_id}/").status_code == 200
    assert MenuItem.active_objects().filter(pk=item_id).exists() is False

    table = client.post(
        "/api/v1/restaurant/tables/",
        {"code": "T9", "branch_id": branch_id, "capacity": 4},
        format="json",
    )
    assert table.status_code == 201
    table_id = table.json()["data"]["id"]
    assert (
        client.patch(
            f"/api/v1/restaurant/tables/{table_id}/",
            {"capacity": 6},
            format="json",
        ).json()["data"]["capacity"]
        == 6
    )
    assert client.delete(f"/api/v1/restaurant/tables/{table_id}/").status_code == 200
    assert DiningTable.active_objects().filter(pk=table_id).exists() is False
    assert MenuCategory.active_objects().filter(pk=cat_id).exists()
    assert AuditLog.objects.filter(module="restaurant", action="create").exists()


@pytest.mark.django_db
def test_hotel_room_guest_reservation_update(crud_env):
    client = _client(crud_env["user"])
    branch_id = str(crud_env["branch"].id)
    rtype = client.post(
        "/api/v1/hotel/room-types/",
        {"name": "Deluxe", "branch_id": branch_id, "base_rate": "80"},
        format="json",
    )
    assert rtype.status_code == 201
    type_id = rtype.json()["data"]["id"]
    room = client.post(
        "/api/v1/hotel/rooms/",
        {"code": "201", "branch_id": branch_id, "room_type_id": type_id},
        format="json",
    )
    assert room.status_code == 201
    room_id = room.json()["data"]["id"]
    guest = client.post(
        "/api/v1/hotel/guests/",
        {"full_name": "Amina", "branch_id": branch_id, "phone": "061"},
        format="json",
    )
    assert guest.status_code == 201
    guest_id = guest.json()["data"]["id"]
    today = timezone.localdate()
    res = client.post(
        "/api/v1/hotel/reservations/",
        {
            "branch_id": branch_id,
            "guest_id": guest_id,
            "room_type_id": type_id,
            "room_id": room_id,
            "check_in_date": today.isoformat(),
            "check_out_date": (today + timedelta(days=2)).isoformat(),
        },
        format="json",
    )
    assert res.status_code == 201, res.content
    res_id = res.json()["data"]["id"]
    updated = client.patch(
        f"/api/v1/hotel/reservations/{res_id}/",
        {"adults": 2, "notes": "Late arrival"},
        format="json",
    )
    assert updated.status_code == 200, updated.content
    assert updated.json()["data"]["adults"] == 2
    assert client.patch(
        f"/api/v1/hotel/guests/{guest_id}/",
        {"phone": "062"},
        format="json",
    ).json()["data"]["phone"] == "062"
    assert client.delete(f"/api/v1/hotel/rooms/{room_id}/").status_code == 200
    assert Room.active_objects().filter(pk=room_id).exists() is False
    assert RoomType.active_objects().filter(pk=type_id).exists()
    assert Guest.active_objects().filter(pk=guest_id).exists()
    assert Reservation.active_objects().filter(pk=res_id).exists()


@pytest.mark.django_db
def test_property_unit_patch_delete(crud_env):
    client = _client(crud_env["user"])
    branch_id = str(crud_env["branch"].id)
    prop = client.post(
        "/api/v1/property/properties/",
        {"name": "Block A", "branch_id": branch_id, "kind": "residential"},
        format="json",
    )
    assert prop.status_code == 201, prop.content
    prop_id = prop.json()["data"]["id"]
    bldg = client.post(
        "/api/v1/property/buildings/",
        {"name": "Tower", "branch_id": branch_id, "property_id": prop_id},
        format="json",
    )
    assert bldg.status_code == 201, bldg.content
    bldg_id = bldg.json()["data"]["id"]
    unit = client.post(
        "/api/v1/property/units/",
        {
            "code": "A-1",
            "branch_id": branch_id,
            "building_id": bldg_id,
            "kind": "residential",
            "rent_amount": "400",
        },
        format="json",
    )
    assert unit.status_code == 201, unit.content
    unit_id = unit.json()["data"]["id"]
    patched = client.patch(
        f"/api/v1/property/units/{unit_id}/",
        {"rent_amount": "450", "bedrooms": 2},
        format="json",
    )
    assert patched.status_code == 200, patched.content
    assert float(patched.json()["data"]["rent_amount"]) == 450
    assert patched.json()["data"]["bedrooms"] == 2
    assert client.delete(f"/api/v1/property/units/{unit_id}/").status_code == 200
    assert PropertyUnit.active_objects().filter(pk=unit_id).exists() is False


@pytest.mark.django_db
def test_coa_write_and_journal_reverse(crud_env):
    client = _client(crud_env["user"])
    created = client.post(
        "/api/v1/finance/accounts/",
        {"code": "6900", "name": "Custom Expense", "type": "expense"},
        format="json",
    )
    assert created.status_code == 201, created.content
    acc_id = created.json()["data"]["id"]
    patched = client.patch(
        f"/api/v1/finance/accounts/{acc_id}/",
        {"name": "Custom Opex"},
        format="json",
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["name"] == "Custom Opex"

    cash = Account.active_objects().get(tenant_id=crud_env["tenant"].id, code="1000")
    rev = Account.active_objects().get(tenant_id=crud_env["tenant"].id, code="4000")
    draft = JournalService.create_entry(
        data={
            "tenant_id": crud_env["tenant"].id,
            "entry_date": timezone.localdate(),
            "description": "Manual cash",
            "status": JournalEntry.STATUS_DRAFT,
            "source_type": JournalEntry.SOURCE_MANUAL,
            "branch_id": crud_env["branch"].id,
            "lines": [
                {"account_id": str(cash.id), "debit": "25", "credit": "0"},
                {"account_id": str(rev.id), "debit": "0", "credit": "25"},
            ],
        },
        user=crud_env["user"],
    )
    posted = JournalService.post_draft(
        entry=draft, user=crud_env["user"], allow_self_approve=True
    )
    reversal = client.post(
        f"/api/v1/finance/journal/{posted.id}/reverse/",
        {"reason": "Correction"},
        format="json",
    )
    assert reversal.status_code == 201, reversal.content
    data = reversal.json()["data"]
    assert data["reverses_entry_id"] == str(posted.id)
    assert abs(data["total_debit"] - data["total_credit"]) < 0.001
    assert AuditLog.objects.filter(module="finance", action="reverse").exists()

    again = client.post(
        f"/api/v1/finance/journal/{posted.id}/reverse/",
        {"reason": "twice"},
        format="json",
    )
    assert again.status_code == 400


@pytest.mark.django_db
def test_gym_members_create_without_manage():
    bootstrap_roles_and_permissions()
    tenant = Tenant.objects.create(name="Gym Fine", slug="gym-fine", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="Gym Fine Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="Main", code="MAIN", is_default=True
    )
    sync_tenant_modules(
        tenant=tenant, enabled_codes=["gym"], validate_dependencies=False
    )
    user = get_user_model().objects.create_user(
        username="recept", password="pass12345", tenant=tenant, branch=branch
    )
    for code in ("gym.view", "gym.members.create"):
        perm = Permission.objects.get(codename=code)
        UserPermission.objects.get_or_create(user=user, permission=perm)
    client = _client(user)
    created = client.post(
        "/api/v1/gym/members/",
        {"full_name": "New Member", "phone": "061"},
        format="json",
    )
    assert created.status_code == 201, created.content
    member_id = created.json()["data"]["id"]
    update = client.patch(
        f"/api/v1/gym/members/{member_id}/",
        {"phone": "062"},
        format="json",
    )
    assert update.status_code == 403
    delete = client.delete(f"/api/v1/gym/members/{member_id}/")
    assert delete.status_code == 403
    assert AuditLog.objects.filter(module="gym", action="create", entity_id=member_id).exists()
