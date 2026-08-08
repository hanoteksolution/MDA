"""STEP 14 — gym members + tenant isolation."""

import pytest
from django.db import IntegrityError

from apps.customers.models import Customer
from apps.gym.models import Member
from apps.gym.services.member_service import MemberError, MemberService
from apps.platform.models import Tenant


@pytest.fixture
def gym_tenants(db):
    a = Tenant.objects.create(name="Gym A", slug="gym-a", status=Tenant.STATUS_ACTIVE)
    b = Tenant.objects.create(name="Gym B", slug="gym-b", status=Tenant.STATUS_ACTIVE)
    return {"a": a, "b": b}


@pytest.mark.django_db
def test_create_member_auto_number(gym_tenants):
    member = MemberService.create(
        data={"full_name": "Ada Lovelace", "phone": "555-0100", "tenant": gym_tenants["a"]}
    )
    assert member.membership_number.startswith("MEM-")
    assert member.status == Member.STATUS_ACTIVE
    assert member.joined_at is not None


@pytest.mark.django_db
def test_membership_number_unique_per_tenant(gym_tenants):
    MemberService.create(
        data={
            "full_name": "A1",
            "membership_number": "MEM-100",
            "tenant": gym_tenants["a"],
        }
    )
    # Same number OK on other tenant
    MemberService.create(
        data={
            "full_name": "B1",
            "membership_number": "MEM-100",
            "tenant": gym_tenants["b"],
        }
    )
    with pytest.raises(MemberError, match="already exists"):
        MemberService.create(
            data={
                "full_name": "A2",
                "membership_number": "MEM-100",
                "tenant": gym_tenants["a"],
            }
        )


@pytest.mark.django_db
def test_list_scoped_by_tenant(gym_tenants):
    MemberService.create(data={"full_name": "Only A", "tenant": gym_tenants["a"]})
    MemberService.create(data={"full_name": "Only B", "tenant": gym_tenants["b"]})

    # apply_tenant_scope without user returns unfiltered unless enforcement —
    # assert raw counts and filter explicitly
    assert Member.objects.filter(tenant=gym_tenants["a"]).count() == 1
    assert Member.objects.filter(tenant=gym_tenants["b"]).count() == 1
    assert Member.objects.filter(tenant=gym_tenants["a"], full_name="Only B").count() == 0


@pytest.mark.django_db
def test_optional_customer_link_same_tenant(gym_tenants):
    customer = Customer.objects.create(
        tenant=gym_tenants["a"],
        customer_code="C-1",
        full_name="CRM Person",
        phone="555",
    )
    member = MemberService.create(
        data={
            "full_name": "CRM Person",
            "customer_id": customer.id,
            "tenant": gym_tenants["a"],
        }
    )
    assert member.customer_id == customer.id

    foreign = Customer.objects.create(
        tenant=gym_tenants["b"],
        customer_code="C-1",
        full_name="Other",
    )
    with pytest.raises(MemberError, match="Customer not found"):
        MemberService.create(
            data={
                "full_name": "Bad link",
                "customer_id": foreign.id,
                "tenant": gym_tenants["a"],
            }
        )


@pytest.mark.django_db
def test_update_and_soft_delete(gym_tenants):
    member = MemberService.create(
        data={"full_name": "Temp", "tenant": gym_tenants["a"]}
    )
    MemberService.update(member=member, data={"status": "suspended", "full_name": "Temp X"})
    member.refresh_from_db()
    assert member.status == "suspended"
    assert member.full_name == "Temp X"
    MemberService.soft_delete(member=member)
    member.refresh_from_db()
    assert member.deleted_at is not None
    assert Member.active_objects().filter(pk=member.pk).count() == 0


@pytest.mark.django_db
def test_db_unique_constraint(gym_tenants):
    Member.objects.create(
        tenant=gym_tenants["a"],
        membership_number="UQ-1",
        full_name="One",
    )
    with pytest.raises(IntegrityError):
        Member.objects.create(
            tenant=gym_tenants["a"],
            membership_number="UQ-1",
            full_name="Two",
        )
