import pytest
from django.contrib.auth import get_user_model

from apps.authentication.models import Role
from apps.platform.models import BusinessType, Tenant, TenantDomain, TenantSettings
from apps.platform.services.domain_utils import (
    build_tenant_hostname,
    is_reserved_tenant_slug,
    validate_tenant_slug,
)
from apps.platform.services.platform_service import PlatformService


@pytest.mark.parametrize(
    "slug",
    ["www", "api", "admin", "platform", "erp", "billing"],
)
def test_reserved_slugs_blocked(slug):
    assert is_reserved_tenant_slug(slug)
    with pytest.raises(ValueError, match="reserved"):
        validate_tenant_slug(slug)


def test_valid_slug_and_hostname():
    assert validate_tenant_slug("Arabica Coffee") == "arabica-coffee"
    assert build_tenant_hostname("arabica") == "arabica.erp.safaritechno.com"


@pytest.mark.django_db
def test_ensure_business_types_seeded():
    PlatformService.ensure_default_business_types()
    codes = set(BusinessType.objects.values_list("code", flat=True))
    assert "retail" in codes
    assert "pharmacy" in codes
    assert "gym" in codes
    assert "futsal" in codes


@pytest.mark.django_db
def test_create_shop_provisions_settings_and_domain():
    PlatformService.ensure_default_plans()
    PlatformService.ensure_default_business_types()
    role, _ = Role.objects.get_or_create(
        slug="admin",
        defaults={"name": "Admin", "is_system": True},
    )
    User = get_user_model()
    actor = User.objects.create_user(
        username="platform_actor",
        password="pass12345",
        is_platform_admin=True,
        role=role,
    )
    tenant, owner = PlatformService.create_shop(
        data={
            "name": "Arabica Cafe",
            "subdomain": "arabica",
            "business_type_code": "cafeteria",
            "currency": "USD",
            "language": "en",
            "owner": {
                "username": "arabica_owner",
                "password": "pass12345",
                "role_slug": "admin",
            },
            "plan_code": "starter",
        },
        user=actor,
    )
    assert tenant.slug == "arabica"
    assert tenant.business_type.code == "cafeteria"
    assert tenant.status == Tenant.STATUS_TRIAL
    assert TenantSettings.objects.filter(tenant=tenant).exists()
    domain = TenantDomain.objects.get(tenant=tenant, is_primary=True)
    assert domain.domain == "arabica.erp.safaritechno.com"
    assert owner is not None
    assert owner.username == "arabica_owner"


@pytest.mark.django_db
def test_create_shop_rejects_reserved_subdomain():
    PlatformService.ensure_default_plans()
    PlatformService.ensure_default_business_types()
    with pytest.raises(ValueError, match="reserved"):
        PlatformService.create_shop(
            data={
                "name": "Bad Shop",
                "subdomain": "admin",
                "owner": {"username": "x", "password": "pass12345", "role_slug": "admin"},
                "plan_code": "starter",
            }
        )


@pytest.mark.django_db
def test_business_types_api(api_client, db):
    PlatformService.ensure_default_business_types()
    User = get_user_model()
    role, _ = Role.objects.get_or_create(
        slug="platform_admin",
        defaults={"name": "Platform Admin", "is_system": True},
    )
    user = User.objects.create_user(
        username="plat_admin",
        password="pass12345",
        is_platform_admin=True,
        role=role,
    )
    api_client.force_authenticate(user=user)
    response = api_client.get("/api/v1/platform/business-types/")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    codes = {item["code"] for item in body["data"]["items"]}
    assert "retail" in codes
    assert "www" in body["data"]["reserved_slugs"]


@pytest.mark.django_db
def test_slug_check_api(api_client, db):
    User = get_user_model()
    user = User.objects.create_user(
        username="plat_admin2",
        password="pass12345",
        is_platform_admin=True,
    )
    api_client.force_authenticate(user=user)
    bad = api_client.get("/api/v1/platform/slug-check/?slug=api")
    assert bad.json()["data"]["available"] is False
    good = api_client.get("/api/v1/platform/slug-check/?slug=freshmart")
    assert good.json()["data"]["available"] is True
    assert good.json()["data"]["hostname"] == "freshmart.erp.safaritechno.com"
