"""STEP 25 — self-serve tenant onboarding wizard."""

import pytest

from apps.platform.models import Tenant
from apps.platform.services.onboarding_service import OnboardingError, OnboardingService
from apps.platform.services.platform_service import PlatformService


@pytest.fixture
def onboard_ready(db):
    PlatformService.ensure_default_plans()
    PlatformService.ensure_default_business_types()
    return True


@pytest.mark.django_db
def test_catalog_includes_types_and_plans(onboard_ready):
    catalog = OnboardingService.catalog()
    assert catalog["business_types"]
    assert catalog["plans"]
    assert catalog["base_domain"]
    codes = {p["code"] for p in catalog["plans"]}
    assert "starter" in codes


@pytest.mark.django_db
def test_reserved_slug_rejected(onboard_ready):
    result = OnboardingService.check_slug("api")
    assert result["available"] is False
    assert "reserved" in result["reason"].lower()


@pytest.mark.django_db
def test_provision_creates_tenant_branch_owner(onboard_ready):
    result = OnboardingService.provision(
        data={
            "name": "Fresh Mart",
            "slug": "freshmart",
            "business_type_code": "retail",
            "plan_code": "starter",
            "contact_email": "owner@freshmart.test",
            "branch_name": "Downtown",
            "owner": {
                "username": "fresh_owner",
                "email": "owner@freshmart.test",
                "password": "pass12345",
            },
        }
    )
    assert result["idempotent_replay"] is False
    tenant = Tenant.objects.get(slug="freshmart")
    assert tenant.name == "Fresh Mart"
    assert result["branch"]["name"] == "Downtown"
    assert result["owner"]["username"] == "fresh_owner"
    assert tenant.subscription.plan.code == "starter"


@pytest.mark.django_db
def test_provision_idempotent_replay(onboard_ready):
    payload = {
        "name": "Replay Shop",
        "slug": "replayshop",
        "business_type_code": "retail",
        "plan_code": "starter",
        "contact_email": "a@replay.test",
        "owner": {
            "username": "replay_owner",
            "email": "a@replay.test",
            "password": "pass12345",
        },
    }
    first = OnboardingService.provision(data=payload)
    second = OnboardingService.provision(data=payload)
    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True
    assert Tenant.objects.filter(slug="replayshop").count() == 1


@pytest.mark.django_db
def test_provision_rejects_taken_slug_different_owner(onboard_ready):
    OnboardingService.provision(
        data={
            "name": "Taken Shop",
            "slug": "takenshop",
            "business_type_code": "retail",
            "plan_code": "starter",
            "contact_email": "a@taken.test",
            "owner": {
                "username": "taken_owner",
                "email": "a@taken.test",
                "password": "pass12345",
            },
        }
    )
    with pytest.raises(OnboardingError) as exc:
        OnboardingService.provision(
            data={
                "name": "Other Shop",
                "slug": "takenshop",
                "business_type_code": "retail",
                "plan_code": "starter",
                "contact_email": "b@taken.test",
                "owner": {
                    "username": "other_owner",
                    "email": "b@taken.test",
                    "password": "pass12345",
                },
            }
        )
    assert exc.value.code == "SLUG_TAKEN"


@pytest.mark.django_db
def test_onboarding_api_flow(api_client, onboard_ready):
    catalog = api_client.get("/api/v1/onboarding/catalog/")
    assert catalog.status_code == 200
    assert catalog.data["data"]["plans"]

    reserved = api_client.get("/api/v1/onboarding/slug-check/?slug=www")
    assert reserved.status_code == 200
    assert reserved.data["data"]["available"] is False

    ok_slug = api_client.get("/api/v1/onboarding/slug-check/?slug=newshop25")
    assert ok_slug.data["data"]["available"] is True

    resp = api_client.post(
        "/api/v1/onboarding/provision/",
        data={
            "name": "API Shop",
            "slug": "newshop25",
            "business_type_code": "pharmacy",
            "plan_code": "business",
            "contact_email": "api@shop.test",
            "owner": {
                "username": "api_owner",
                "email": "api@shop.test",
                "password": "pass12345",
            },
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["data"]["access"]
    assert resp.data["data"]["user"]["username"] == "api_owner"

    replay = api_client.post(
        "/api/v1/onboarding/provision/",
        data={
            "name": "API Shop",
            "slug": "newshop25",
            "business_type_code": "pharmacy",
            "plan_code": "business",
            "contact_email": "api@shop.test",
            "owner": {
                "username": "api_owner",
                "email": "api@shop.test",
                "password": "pass12345",
            },
        },
        format="json",
    )
    assert replay.status_code == 200
    assert replay.data["data"]["idempotent_replay"] is True
