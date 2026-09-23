"""Platform Admin → Integrations: provider infrastructure is managed only by global platform admins.

Tenant users (including tenant admins holding ``integrations.manage``) must get 403 on every
platform integration endpoint; tenant operations (templates, logs, send, intents) stay available.
"""

from __future__ import annotations

import json

import pytest
from cryptography.fernet import Fernet
from rest_framework.test import APIClient

from apps.integrations.models import IntegrationCredential, PaymentProviderConfig, SmsProvider
from apps.integrations.services import CredentialService
from tests.helpers.branch_factory import add_owner, add_user, build_branch_tenant
from tests.helpers.platform_admin import PLATFORM_INTEGRATIONS as P, superadmin_client
from tests.helpers.shop_factory import auth_client_as

pytestmark = pytest.mark.django_db

SECRET = "PLATFORM-ONLY-SECRET-987654"

# Every platform integration endpoint: (method, path-template, body).
ENDPOINTS = [
    ("get", "branches/", None),
    ("get", "credentials/", None),
    ("post", "credentials/", {"label": "x", "secret": SECRET}),
    ("patch", "credentials/{cred}/", {"label": "y"}),
    ("get", "sms-providers/", None),
    ("post", "sms-providers/", {"name": "gw", "provider_type": "MOCK"}),
    ("patch", "sms-providers/{sms}/", {"is_active": False}),
    ("get", "payment-providers/", None),
    ("post", "payment-providers/", {"name": "pay", "provider_type": "MOCK"}),
    ("patch", "payment-providers/{pay}/", {"is_active": False}),
    ("get", "payments/webhook-events/", None),
    ("post", "payments/reconcile/", {}),
    ("get", "payments/reconciliation/", None),
    ("post", "payments/reconciliation/00000000-0000-0000-0000-000000000000/resolve/", {"note": "x"}),
]


@pytest.fixture(autouse=True)
def key(settings):
    settings.INTEGRATION_ENCRYPTION_KEY = Fernet.generate_key().decode()


@pytest.fixture
def world():
    ctx = build_branch_tenant(slug="plat-a", branch_codes=("HODAN",))
    other = build_branch_tenant(slug="plat-b", branch_codes=("MAIN",))
    cred = CredentialService.create(tenant=ctx.tenant, label="gw", secret=SECRET)
    sms = SmsProvider.objects.create(tenant=ctx.tenant, name="gw", provider_type="MOCK", credential=cred)
    pay = PaymentProviderConfig.objects.create(tenant=ctx.tenant, name="pay", provider_type="MOCK")
    foreign_cred = CredentialService.create(tenant=other.tenant, label="b", secret="B-SECRET-000111")
    return {"ctx": ctx, "other": other, "cred": cred, "sms": sms, "pay": pay, "foreign_cred": foreign_cred}


def url(world, template, tenant=None):
    path = template.format(cred=world["cred"].pk, sms=world["sms"].pk, pay=world["pay"].pk)
    return f"{P}/{path}?tenant_id={(tenant or world['ctx'].tenant).pk}"


@pytest.mark.parametrize("role", ["owner", "cashier", "anonymous"])
def test_tenant_users_are_refused_on_every_platform_endpoint(world, role):
    ctx = world["ctx"]
    if role == "anonymous":
        client, expected = APIClient(), {401, 403}
    else:
        user = add_owner(ctx, username="t_owner") if role == "owner" else add_user(
            ctx, username="t_cashier", role_slug="cashier", branches=("HODAN",))
        client, expected = auth_client_as(APIClient(), user), {403}
    before = (IntegrationCredential.objects.count(), SmsProvider.objects.count(), PaymentProviderConfig.objects.count())
    for method, template, body in ENDPOINTS:
        response = getattr(client, method)(url(world, template), body, format="json") if body is not None \
            else getattr(client, method)(url(world, template))
        assert response.status_code in expected, (role, method, template, response.status_code)
        assert SECRET not in response.content.decode()
    world["sms"].refresh_from_db()
    assert world["sms"].is_active is True
    assert before == (IntegrationCredential.objects.count(), SmsProvider.objects.count(), PaymentProviderConfig.objects.count())


def test_legacy_tenant_management_routes_no_longer_exist(world):
    owner = auth_client_as(APIClient(), add_owner(world["ctx"], username="legacy_owner"))
    for path in ("credentials/", "sms-providers/", "payment-providers/", "payments/webhook-events/",
                 "payments/reconciliation/", "payments/reconcile/"):
        assert owner.get(f"/api/v1/integrations/{path}").status_code in {404, 405}, path


def test_superadmin_manages_a_selected_tenant(world):
    admin = superadmin_client()
    for method, template, body in ENDPOINTS:
        response = getattr(admin, method)(url(world, template), body, format="json") if body is not None \
            else getattr(admin, method)(url(world, template))
        assert response.status_code in {200, 201, 404}, (method, template, response.status_code)
        if "00000000" not in template:
            assert response.status_code in {200, 201}, (method, template)
    assert SmsProvider.objects.filter(tenant=world["ctx"].tenant, name="gw").count() == 2


def test_branch_list_is_scoped_to_the_selected_tenant(world):
    admin = superadmin_client()
    codes = [b["code"] for b in admin.get(url(world, "branches/")).json()["data"]]
    assert "HODAN" in codes and "MAIN" not in codes


def test_tenant_must_be_named_and_accessible(world):
    admin = superadmin_client()
    assert admin.get(f"{P}/sms-providers/").status_code == 400
    assert admin.get(f"{P}/sms-providers/?tenant_id=not-a-uuid").status_code == 404
    assert admin.get(f"{P}/sms-providers/?tenant_id=00000000-0000-0000-0000-000000000000").status_code == 404


def test_platform_writes_cannot_cross_tenants(world):
    admin, other = superadmin_client(), world["other"]
    foreign_branch = other.branch("MAIN")
    for kind in ("sms-providers/", "payment-providers/"):
        assert admin.post(url(world, kind), {"name": "x", "provider_type": "MOCK", "credential_id": str(world["foreign_cred"].pk)},
                          format="json").status_code == 400
        assert admin.post(url(world, kind), {"name": "x", "provider_type": "MOCK", "branch_id": str(foreign_branch.pk)},
                          format="json").status_code == 400
    # A provider addressed through the wrong tenant looks missing.
    assert admin.patch(url(world, "sms-providers/{sms}/", tenant=other.tenant), {"name": "hijack"}, format="json").status_code == 404
    listed = admin.get(url(world, "credentials/", tenant=other.tenant)).json()["data"]
    assert [c["label"] for c in listed] == ["b"]


def test_platform_responses_keep_secrets_masked(world):
    admin = superadmin_client()
    created = admin.post(url(world, "credentials/"), {"label": "new", "secret": SECRET + "-2"}, format="json")
    assert created.status_code == 201
    assert set(created.json()["data"]) == {"id", "label", "has_secret", "masked_tail", "rotated_at"}
    stored = IntegrationCredential.objects.get(pk=created.json()["data"]["id"]).encrypted_secret
    assert stored.startswith("gAAAA") and SECRET not in stored
    text = json.dumps([admin.get(url(world, p)).json() for p in ("credentials/", "sms-providers/", "payment-providers/")])
    assert SECRET not in text and stored not in text


def test_tenant_operations_remain_available(world):
    owner = auth_client_as(APIClient(), add_owner(world["ctx"], username="ops_owner"))
    assert owner.get("/api/v1/integrations/sms-templates/").status_code == 200
    assert owner.post("/api/v1/integrations/sms-templates/", {"code": "welcome", "body": "Hi {name}"}, format="json").status_code == 201
    assert owner.get("/api/v1/integrations/sms-logs/").status_code == 200
    sent = owner.post("/api/v1/integrations/sms/send/", {"to": "+252611234567", "body": "hello"}, format="json")
    assert sent.status_code == 201 and SECRET not in sent.content.decode()
    assert owner.get("/api/v1/integrations/payments/intents/").status_code == 200
