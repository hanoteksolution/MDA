"""Workspace subdomain availability — focused unit + API tests."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import connection

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.platform.models import Tenant
from apps.platform.services.domain_utils import (
    RESERVED_TENANT_SLUGS,
    check_subdomain_availability,
    normalize_tenant_slug,
    suggest_subdomains,
    validate_tenant_slug,
)
from apps.platform.services.onboarding_service import OnboardingError, OnboardingService
from apps.platform.services.platform_service import PlatformService, SubdomainTakenError


@pytest.fixture
def onboard_ready(db):
    bootstrap_roles_and_permissions()
    PlatformService.ensure_default_plans()
    PlatformService.ensure_default_business_types()
    return True


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Barista", "barista"),
        ("Barista Coffee", "barista-coffee"),
        ("  ARABICA  ", "arabica"),
        ("shop_name", "shop-name"),
        ("a--b", "a-b"),
    ],
)
def test_normalize_tenant_slug(raw, expected):
    assert normalize_tenant_slug(raw) == expected


@pytest.mark.unit
@pytest.mark.parametrize("value", ["shop", "shop-2", "a1", "barista-coffee"])
def test_valid_tenant_slug(value):
    assert validate_tenant_slug(value) == value


@pytest.mark.unit
@pytest.mark.parametrize("value", ["www", "API", "-shop", "shop-", "a", "💥", "erp", "admin"])
def test_invalid_or_reserved_tenant_slug(value):
    with pytest.raises(ValueError):
        validate_tenant_slug(value)


@pytest.mark.unit
def test_reserved_list_covers_required_names():
    required = {
        "www", "api", "admin", "app", "auth", "login", "register", "signup",
        "billing", "payments", "payment", "sms", "integrations", "support",
        "help", "status", "docs", "static", "media", "assets", "files", "cdn",
        "mail", "smtp", "ftp", "dev", "staging", "test", "demo", "dashboard",
        "portal", "system", "internal", "erp",
    }
    assert required.issubset(RESERVED_TENANT_SLUGS)


@pytest.mark.django_db
def test_availability_available(onboard_ready):
    result = check_subdomain_availability("Barista")
    assert result["requested"] == "Barista"
    assert result["normalized"] == "barista"
    assert result["available"] is True
    assert result["hostname"] == "barista.erp.safaritechno.com"
    assert result["reason"] is None
    assert result["suggestions"] == []


@pytest.mark.django_db
def test_availability_taken_with_suggestions(onboard_ready):
    OnboardingService.provision(
        data={
            "name": "Arabica",
            "slug": "arabica",
            "business_type_code": "retail",
            "plan_code": "starter",
            "contact_email": "a@arabica.test",
            "owner": {
                "username": "arabica_owner",
                "email": "a@arabica.test",
                "password": "pass12345",
            },
        }
    )
    result = check_subdomain_availability("arabica")
    assert result["available"] is False
    assert result["reason"] == "taken"
    assert result["hostname"] is None
    assert "email" not in result
    assert "tenant" not in result
    assert "owner" not in result
    assert result["suggestions"]
    assert all(s.startswith("arabica-") for s in result["suggestions"])
    assert not any(s.rstrip("0123456789") != s and s[-1].isdigit() and "-" not in s[-4:] for s in result["suggestions"])


@pytest.mark.django_db
def test_availability_reserved(onboard_ready):
    result = check_subdomain_availability("admin")
    assert result["available"] is False
    assert result["reason"] == "reserved"
    assert result["suggestions"]


@pytest.mark.django_db
def test_availability_invalid(onboard_ready):
    result = check_subdomain_availability("...")
    assert result["available"] is False
    assert result["reason"] == "invalid"
    assert result["normalized"] is None
    assert result["suggestions"] == []


@pytest.mark.django_db
def test_no_silent_suffix_on_create(onboard_ready):
    OnboardingService.provision(
        data={
            "name": "Baarista One",
            "slug": "baarista",
            "business_type_code": "retail",
            "plan_code": "starter",
            "contact_email": "a@baarista.test",
            "owner": {
                "username": "baarista_a",
                "email": "a@baarista.test",
                "password": "pass12345",
            },
        }
    )
    with pytest.raises(OnboardingError) as exc:
        OnboardingService.provision(
            data={
                "name": "Baarista Two",
                "slug": "baarista",
                "business_type_code": "retail",
                "plan_code": "starter",
                "contact_email": "b@baarista.test",
                "owner": {
                    "username": "baarista_b",
                    "email": "b@baarista.test",
                    "password": "pass12345",
                },
            }
        )
    assert exc.value.code == "SUBDOMAIN_TAKEN"
    assert Tenant.objects.filter(slug__startswith="baarista").count() == 1
    assert not Tenant.objects.exclude(slug="baarista").filter(slug__startswith="baarista").exists()


@pytest.mark.django_db
def test_create_shop_never_rewrites_selected_slug(onboard_ready):
    PlatformService.create_shop(
        data={
            "name": "Coffee One",
            "slug": "coffee",
            "business_type_code": "retail",
            "owner": {
                "username": "coffee_a",
                "email": "a@coffee.test",
                "password": "pass12345",
            },
        },
        user=None,
    )
    with pytest.raises(SubdomainTakenError):
        PlatformService.create_shop(
            data={
                "name": "Coffee Two",
                "slug": "coffee",
                "business_type_code": "retail",
                "owner": {
                    "username": "coffee_b",
                    "email": "b@coffee.test",
                    "password": "pass12345",
                },
            },
            user=None,
        )
    assert list(Tenant.objects.filter(slug__startswith="coffee").values_list("slug", flat=True)) == [
        "coffee"
    ]


@pytest.mark.django_db
def test_public_availability_api(api_client, onboard_ready):
    ok = api_client.get("/api/v1/public/workspaces/subdomain-availability/?subdomain=newcafe99")
    assert ok.status_code == 200
    body = ok.data["data"]
    assert body["available"] is True
    assert body["normalized"] == "newcafe99"
    assert body["hostname"].endswith(".erp.safaritechno.com")

    reserved = api_client.get("/api/v1/public/subdomains/check/?subdomain=www")
    assert reserved.data["data"]["reason"] == "reserved"


@pytest.mark.django_db
def test_onboarding_slug_check_api_shape(api_client, onboard_ready):
    resp = api_client.get("/api/v1/onboarding/slug-check/?slug=FreshShop")
    data = resp.data["data"]
    assert data["requested"] == "FreshShop"
    assert data["normalized"] == "freshshop"
    assert data["available"] is True


@pytest.mark.django_db
def test_suggestions_are_available(onboard_ready):
    Tenant.objects.create(name="X", slug="arabica", is_active=True)
    suggestions = suggest_subdomains("arabica")
    assert suggestions
    for s in suggestions:
        assert check_subdomain_availability(s)["available"] is True


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_creation_returns_conflict(onboard_ready):
    """One wins; the other must 409 — never coffee123 / coffee456."""
    if connection.vendor != "postgresql":
        pytest.skip("Concurrency uniqueness proof requires PostgreSQL")

    def attempt(idx: int):
        from django.test import Client

        client = Client()
        return client.post(
            "/api/v1/onboarding/provision/",
            data={
                "name": f"Coffee {idx}",
                "slug": "coffee",
                "business_type_code": "retail",
                "plan_code": "starter",
                "contact_email": f"c{idx}@coffee.test",
                "owner": {
                    "username": f"coffee_owner_{idx}",
                    "email": f"c{idx}@coffee.test",
                    "password": "pass12345",
                },
            },
            content_type="application/json",
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, (1, 2)))

    statuses = sorted(r.status_code for r in results)
    assert statuses == [201, 409]
    assert Tenant.objects.filter(slug="coffee").count() == 1
    assert not Tenant.objects.filter(slug__regex=r"^coffee\d+$").exists()
    conflict = next(r for r in results if r.status_code == 409)
    assert conflict.json()["code"] == "SUBDOMAIN_TAKEN"


@pytest.mark.django_db
def test_deleted_shop_releases_its_workspace_url(onboard_ready):
    from apps.platform.models import TenantDomain

    def _create(name, owner):
        return PlatformService.create_shop(
            data={
                "name": name,
                "slug": "reuse",
                "business_type_code": "retail",
                "owner": {"username": owner, "email": f"{owner}@reuse.test", "password": "pass12345"},
            },
            user=None,
        )[0]

    old = _create("Reuse One", "reuse_a")
    assert check_subdomain_availability("reuse")["available"] is False
    PlatformService.delete_shop(tenant=old, user=None)

    assert check_subdomain_availability("reuse")["available"] is True
    new = _create("Reuse Two", "reuse_b")
    assert new.slug == "reuse" and new.pk != old.pk
    old.refresh_from_db()
    assert old.deleted_at is not None and old.slug.startswith("reuse-deleted-")
    live = TenantDomain.objects.filter(domain="reuse.erp.safaritechno.com", deleted_at__isnull=True)
    assert [d.tenant_id for d in live] == [new.pk]


@pytest.mark.django_db
def test_soft_deleted_legacy_slug_is_reclaimable(onboard_ready):
    """Rows deleted before slugs were released on delete are freed on claim."""
    from django.utils import timezone

    Tenant.objects.create(name="Old", slug="legacyname", is_active=False, deleted_at=timezone.now())
    assert check_subdomain_availability("legacyname")["available"] is True
    tenant, _ = PlatformService.create_shop(
        data={
            "name": "New",
            "slug": "legacyname",
            "business_type_code": "retail",
            "owner": {"username": "legacy_o", "email": "o@legacy.test", "password": "pass12345"},
        },
        user=None,
    )
    assert tenant.slug == "legacyname"


@pytest.mark.django_db
def test_public_registration_can_claim_its_own_slug_hold(onboard_ready):
    """The registration being provisioned holds its slug; that hold must not block create_shop."""
    from apps.platform.models import RegistrationRequest
    from apps.platform.services.registration_service import RegistrationService

    registration = RegistrationService.create(
        data={
            "name": "Kaafi School",
            "slug": "kaafi-school",
            "business_type_code": "retail",
            "plan_code": "starter",
            "contact_email": "owner@kaafi.test",
            "owner": {"username": "kaafi_owner", "email": "owner@kaafi.test", "password": "Str0ng-Pass-9271"},
            "agreements": {"terms_accepted": True, "privacy_accepted": True},
        },
        idempotency_key="k" * 24,
    )
    assert registration.status == RegistrationRequest.STATUS_READY
    assert Tenant.objects.filter(slug="kaafi-school", deleted_at__isnull=True).count() == 1
    assert check_subdomain_availability("kaafi-school")["available"] is False


def test_school_permissions_are_assignable_only_for_school_tenants(monkeypatch):
    """The user-form permission matrix must include the school group for school workspaces."""
    from apps.authentication.services.auth_service import UserService

    monkeypatch.setattr(
        "apps.platform.services.module_service.usable_module_codes",
        lambda **_: {"school", "sales"},
    )
    assert "school" in UserService._permission_modules_for_tenant(object())
    monkeypatch.setattr(
        "apps.platform.services.module_service.usable_module_codes",
        lambda **_: {"sales"},
    )
    assert "school" not in UserService._permission_modules_for_tenant(object())
