"""STEP 32 — critical gym membership check-in via HTTP API."""

import pytest

from apps.gym.models import Attendance
from apps.gym.services.member_service import MemberService
from apps.gym.services.subscription_service import PlanService, SubscriptionService


pytestmark = [pytest.mark.integration, pytest.mark.critical]


@pytest.mark.django_db
def test_gym_check_in_api(api_client, gym_shop, auth_client):
    shop = gym_shop
    client = auth_client(shop.user)

    member = MemberService.create(
        data={
            "full_name": "API Member",
            "membership_number": "MEM-API-1",
            "phone": "555",
            "tenant": shop.tenant,
        }
    )
    plan = PlanService.create(
        data={
            "code": "month",
            "name": "Monthly",
            "duration_days": 30,
            "price": "30",
            "visit_limit": 10,
            "tenant": shop.tenant,
        }
    )
    SubscriptionService.subscribe(member_id=member.id, plan_id=plan.id, activate=True)

    response = client.post(
        "/api/v1/gym/attendance/check-in/",
        {"membership_number": "MEM-API-1"},
        format="json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["member_id"] == str(member.id)
    assert Attendance.active_objects().filter(member=member, check_out_at__isnull=True).exists()


@pytest.mark.django_db
def test_gym_duplicate_check_in_rejected(api_client, gym_shop, auth_client):
    shop = gym_shop
    client = auth_client(shop.user)

    member = MemberService.create(
        data={
            "full_name": "Dup Member",
            "membership_number": "MEM-DUP-1",
            "tenant": shop.tenant,
        }
    )
    plan = PlanService.create(
        data={
            "code": "day",
            "name": "Day",
            "duration_days": 1,
            "price": "5",
            "tenant": shop.tenant,
        }
    )
    SubscriptionService.subscribe(member_id=member.id, plan_id=plan.id, activate=True)

    ok = client.post(
        "/api/v1/gym/attendance/check-in/",
        {"member_id": str(member.id)},
        format="json",
    )
    assert ok.status_code == 201

    dup = client.post(
        "/api/v1/gym/attendance/check-in/",
        {"member_id": str(member.id)},
        format="json",
    )
    assert dup.status_code == 400
    assert dup.json()["success"] is False
