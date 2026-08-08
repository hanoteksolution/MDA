"""STEP 36 — Futsal tenant isolation (closes STEP 06 deferred gap)."""

from decimal import Decimal

import pytest
from django.core.exceptions import ObjectDoesNotExist

from apps.futsal.models import Court, Team
from apps.futsal.services.futsal_service import FutsalError, FutsalService
from apps.platform.models import Tenant
from apps.settings_app.models import Branch, Company


@pytest.fixture
def two_futsal_tenants(db):
    a = Tenant.objects.create(name="Futsal A", slug="futsal-a", status=Tenant.STATUS_ACTIVE)
    b = Tenant.objects.create(name="Futsal B", slug="futsal-b", status=Tenant.STATUS_ACTIVE)
    ca = Company.objects.create(name="Futsal A Co", tenant=a)
    cb = Company.objects.create(name="Futsal B Co", tenant=b)
    ba = Branch.objects.create(company=ca, tenant=a, name="Pitch A", code="A", is_default=True)
    bb = Branch.objects.create(company=cb, tenant=b, name="Pitch B", code="B", is_default=True)
    from django.contrib.auth import get_user_model

    User = get_user_model()
    ua = User.objects.create_user(
        username="futsal_a", password="pass12345", tenant=a, branch=ba
    )
    ub = User.objects.create_user(
        username="futsal_b", password="pass12345", tenant=b, branch=bb
    )
    court_a = Court.objects.create(
        name="Court A", code="CA", branch=ba, tenant=a, hourly_rate=Decimal("10")
    )
    court_b = Court.objects.create(
        name="Court B", code="CB", branch=bb, tenant=b, hourly_rate=Decimal("12")
    )
    return {
        "a": a,
        "b": b,
        "ba": ba,
        "bb": bb,
        "ua": ua,
        "ub": ub,
        "court_a": court_a,
        "court_b": court_b,
    }


@pytest.mark.django_db
def test_list_courts_is_tenant_scoped(two_futsal_tenants):
    env = two_futsal_tenants
    ids = set(FutsalService.list_courts(user=env["ua"]).values_list("id", flat=True))
    assert env["court_a"].id in ids
    assert env["court_b"].id not in ids


@pytest.mark.django_db
def test_get_court_cross_tenant_raises(two_futsal_tenants):
    env = two_futsal_tenants
    with pytest.raises(ObjectDoesNotExist):
        FutsalService.get_court(pk=env["court_b"].id, user=env["ua"])


@pytest.mark.django_db
def test_create_court_stamps_tenant(two_futsal_tenants):
    env = two_futsal_tenants
    court = FutsalService.create_court(
        data={
            "name": "New Pitch",
            "code": "NP",
            "branch_id": env["ba"].id,
            "hourly_rate": Decimal("15"),
        },
        user=env["ua"],
    )
    assert court.tenant_id == env["a"].id


@pytest.mark.django_db
def test_create_court_rejects_foreign_branch(two_futsal_tenants):
    env = two_futsal_tenants
    with pytest.raises(FutsalError, match="Branch not found"):
        FutsalService.create_court(
            data={
                "name": "Evil",
                "code": "EV",
                "branch_id": env["bb"].id,
                "hourly_rate": Decimal("1"),
            },
            user=env["ua"],
        )


@pytest.mark.django_db
def test_create_team_and_booking_scoped(two_futsal_tenants):
    env = two_futsal_tenants
    team = FutsalService.create_team(
        data={"name": "Tigers", "branch_id": env["ba"].id},
        user=env["ua"],
    )
    assert team.tenant_id == env["a"].id
    assert not FutsalService.list_teams(user=env["ub"]).filter(pk=team.id).exists()

    booking = FutsalService.create_booking(
        data={
            "court_id": env["court_a"].id,
            "start_at": "2026-08-07T10:00:00+00:00",
            "end_at": "2026-08-07T11:00:00+00:00",
            "team_id": team.id,
            "amount_paid": "0",
        },
        user=env["ua"],
    )
    assert booking.tenant_id == env["a"].id
    with pytest.raises(ObjectDoesNotExist):
        FutsalService.get_booking(pk=booking.id, user=env["ub"])


@pytest.mark.django_db
def test_cannot_book_foreign_court(two_futsal_tenants):
    env = two_futsal_tenants
    with pytest.raises(ObjectDoesNotExist):
        FutsalService.create_booking(
            data={
                "court_id": env["court_b"].id,
                "start_at": "2026-08-07T10:00:00+00:00",
                "end_at": "2026-08-07T11:00:00+00:00",
            },
            user=env["ua"],
        )
