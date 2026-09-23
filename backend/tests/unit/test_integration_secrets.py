"""SEC-1 / SEC-2: credentials are encrypted at rest and never leak."""

from __future__ import annotations

import json
import logging
from unittest import mock

import pytest
import requests
from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.integrations import crypto
from apps.integrations.models import IntegrationCredential, SmsLog, SmsProvider
from apps.integrations.providers import custom_http
from apps.integrations.services import CredentialService, SmsService
from tests.helpers.branch_factory import add_owner, build_branch_tenant
from tests.helpers.platform_admin import PLATFORM_INTEGRATIONS, superadmin_client
from tests.helpers.shop_factory import auth_client_as

pytestmark = pytest.mark.django_db

SECRET = "S3CRET-VALUE-XYZ-123456"
BASE = "/api/v1/integrations"


@pytest.fixture(autouse=True)
def key(settings):
    settings.INTEGRATION_ENCRYPTION_KEY = Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def public_dns():
    with mock.patch.object(custom_http.socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 0))]):
        yield


@pytest.fixture
def ctx():
    return build_branch_tenant(slug="sec-tenant", branch_codes=("HODAN",))


@pytest.fixture
def owner(ctx):
    return add_owner(ctx, username="sec_owner")


@pytest.fixture
def client(owner):
    return auth_client_as(APIClient(), owner)


@pytest.fixture
def platform(ctx):
    """Provider configuration is platform-only: a Super Admin managing this tenant."""
    return superadmin_client("sec_root")


def P(ctx, path):
    return f"{PLATFORM_INTEGRATIONS}/{path}?tenant_id={ctx.tenant.pk}"


def raw_secret_column(cred):
    """The column exactly as the database holds it (no model-level decryption exists)."""
    return IntegrationCredential.objects.filter(pk=cred.pk).values_list("encrypted_secret", flat=True).get()


# --------------------------------------------------------------------------- #
# SEC-1: encrypted at rest, masked over the API
# --------------------------------------------------------------------------- #


def test_secret_is_ciphertext_in_the_database_and_round_trips(ctx):
    cred = CredentialService.create(tenant=ctx.tenant, label="gw", secret=SECRET)
    stored = raw_secret_column(cred)
    assert SECRET not in stored and stored.startswith("gAAAA")  # Fernet token
    assert CredentialService.reveal(IntegrationCredential.objects.get(pk=cred.pk)) == SECRET


def test_api_returns_only_has_secret_and_a_masked_tail(ctx, platform):
    created = platform.post(P(ctx, "credentials/"), {"label": "gw", "secret": SECRET}, format="json")
    assert created.status_code == 201
    data = created.json()["data"]
    assert data["has_secret"] is True and data["masked_tail"] == "••••3456"
    assert set(data) == {"id", "label", "has_secret", "masked_tail", "rotated_at"}
    listed = platform.get(P(ctx, "credentials/")).json()["data"]
    assert listed[0]["has_secret"] is True and SECRET not in json.dumps(listed)


def test_short_secrets_show_no_tail(ctx):
    cred = CredentialService.create(tenant=ctx.tenant, label="short", secret="abc123")
    assert CredentialService.serialize(cred)["masked_tail"] == ""


def test_module_refuses_to_work_without_a_key_instead_of_storing_plaintext(ctx, settings):
    settings.INTEGRATION_ENCRYPTION_KEY = ""
    with pytest.raises(ImproperlyConfigured):
        CredentialService.create(tenant=ctx.tenant, label="gw", secret=SECRET)
    assert not IntegrationCredential.objects.exists()
    settings.INTEGRATION_ENCRYPTION_KEY = "not-a-fernet-key"
    with pytest.raises(ImproperlyConfigured) as exc:
        crypto.encrypt_secret("x")
    assert "not-a-fernet-key" not in str(exc.value)


def test_key_rotation_keeps_old_secrets_readable_and_can_re_encrypt(ctx, settings):
    old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    settings.INTEGRATION_ENCRYPTION_KEY = old
    cred = CredentialService.create(tenant=ctx.tenant, label="gw", secret=SECRET)

    settings.INTEGRATION_ENCRYPTION_KEY = f"{new},{old}"  # new primary, old still accepted
    assert CredentialService.reveal(cred) == SECRET
    cred.encrypted_secret = crypto.rotate_token(cred.encrypted_secret)

    settings.INTEGRATION_ENCRYPTION_KEY = new  # old key retired
    assert CredentialService.reveal(cred) == SECRET


def test_wrong_key_is_a_controlled_error_and_a_failed_sms_not_a_crash(ctx, settings):
    cred = CredentialService.create(tenant=ctx.tenant, label="gw", secret=SECRET)
    SmsProvider.objects.create(
        tenant=ctx.tenant, name="gw", provider_type="CUSTOM_HTTP", credential=cred, is_default=True,
        config={"url": "https://gateway.example.test/send"},
    )
    settings.INTEGRATION_ENCRYPTION_KEY = Fernet.generate_key().decode()  # lost the original key
    with pytest.raises(crypto.SecretDecryptError):
        CredentialService.reveal(cred)
    log = SmsService.send(tenant=ctx.tenant, to="+252611234567", body="hi")
    assert log.status == "FAILED" and "cannot be used" in log.error and log.attempts == 1


# --------------------------------------------------------------------------- #
# SEC-2: never in logs, audit text, API responses or serialised errors
# --------------------------------------------------------------------------- #


def test_secret_appears_nowhere_after_a_full_lifecycle(ctx, client, platform, caplog):
    caplog.set_level(logging.DEBUG)  # capture everything, every logger
    bodies = []

    def call(method, path, **kw):
        # Provider configuration goes through Platform Admin; sending/logs stay tenant operations.
        admin = path.startswith(("credentials", "sms-providers"))
        r = getattr(platform if admin else client, method)(P(ctx, path) if admin else f"{BASE}/{path}", **kw)
        bodies.append(r.content.decode())
        return r

    cred = call("post", "credentials/", data={"label": "gw", "secret": SECRET}, format="json").json()["data"]
    call("patch", f"credentials/{cred['id']}/", data={"secret": SECRET + "-ROTATED"}, format="json")
    call("get", "credentials/")
    provider = call("post", "sms-providers/", data={
        "name": "gw", "provider_type": "CUSTOM_HTTP", "credential_id": cred["id"], "is_default": True,
        "config": {"url": "https://gateway.example.test/send", "headers": {"Authorization": "Bearer {secret}"},
                   "body": {"text": "{message}"}},
    }, format="json")
    assert provider.status_code == 201
    call("get", "sms-providers/")

    leaky = requests.ConnectionError(f"cannot reach https://gateway.example.test/send?key={SECRET}-ROTATED")
    with mock.patch.object(custom_http.requests, "request", side_effect=leaky):
        sent = call("post", "sms/send/", data={"to": "+252611234567", "body": "hello"}, format="json")
    assert sent.status_code == 201 and sent.json()["data"]["status"] == "RETRYING"
    call("get", "sms-logs/")
    call("post", "credentials/", data={"label": "", "secret": SECRET}, format="json")  # serialised error
    call("post", "sms-providers/", data={"name": "x", "provider_type": "NOPE", "config": {"k": SECRET}}, format="json")

    for needle in (SECRET, SECRET + "-ROTATED"):
        assert all(needle not in b for b in bodies), "secret leaked in an API response"
        assert needle not in caplog.text, "secret leaked into application logs"
        audit = " ".join(json.dumps([a.old_values, a.new_values], default=str) for a in AuditLog.objects.all())
        assert needle not in audit, "secret leaked into audit rows"
        log_rows = " ".join(
            " ".join(str(getattr(l, f.name, "")) for f in SmsLog._meta.fields) for l in SmsLog.objects.all()
        )
        assert needle not in log_rows
        assert needle not in json.dumps(list(IntegrationCredential.objects.values("label", "secret_tail")))
    assert AuditLog.objects.filter(module="integrations").exists()  # the events *are* audited, minus values


def test_only_platform_admins_can_manage_credentials(ctx, owner):
    from tests.helpers.branch_factory import add_user

    cashier = add_user(ctx, username="sec_cashier", role_slug="cashier", branches=("HODAN",))
    for user in (cashier, owner):  # a tenant admin holding integrations.manage is refused too
        client = auth_client_as(APIClient(), user)
        assert client.get(P(ctx, "credentials/")).status_code == 403
        assert client.post(P(ctx, "credentials/"), {"label": "x", "secret": SECRET}, format="json").status_code == 403
        assert client.get(f"{BASE}/credentials/").status_code == 404  # no tenant-side route exists
    assert not IntegrationCredential.objects.exists()


# --------------------------------------------------------------------------- #
# SEC-3: payment provider credentials follow SEC-1 / SEC-2
# --------------------------------------------------------------------------- #

WEBHOOK_SECRET = "whsec-SEC3-a1b2c3d4e5f6"


def test_payment_secrets_are_encrypted_never_returned_and_never_audited(ctx, client, platform):
    import time

    from apps.integrations.models import PaymentWebhookEvent
    from apps.integrations.providers.payment_base import sign
    from apps.finance.services.chart_service import ChartService
    from tests.helpers.payment_factory import make_invoice

    ChartService.ensure_default_chart(tenant_id=ctx.tenant.pk)
    cred = platform.post(P(ctx, "credentials/"), {"label": "wh", "secret": WEBHOOK_SECRET}, format="json").json()["data"]
    api_key = platform.post(P(ctx, "credentials/"), {"label": "api", "secret": SECRET}, format="json").json()["data"]
    created = platform.post(
        P(ctx, "payment-providers/"),
        {"name": "gw", "provider_type": "MOCK", "credential_id": api_key["id"], "webhook_credential_id": cred["id"]},
        format="json",
    )
    assert created.status_code == 201
    provider = created.json()["data"]
    assert provider["webhook_credential_id"] == cred["id"]

    # Encrypted at rest.
    for secret, label in ((WEBHOOK_SECRET, "wh"), (SECRET, "api")):
        stored = IntegrationCredential.objects.get(label=label).encrypted_secret
        assert secret not in stored and stored.startswith("gAAAA")

    # Drive a real signed + a forged webhook so events, intents and records all exist.
    invoice = make_invoice(ctx, "HODAN")
    intent = client.post(
        f"{BASE}/payments/intents/", {"invoice_id": str(invoice.pk), "idempotency_key": "sec3"}, format="json"
    ).json()["data"]
    body = json.dumps({"event_id": "s3", "type": "payment.succeeded", "reference": intent["provider_reference"],
                       "amount": "100"}).encode()
    ts = str(int(time.time()))
    sig = sign(WEBHOOK_SECRET, ts, body)
    APIClient().post(f"{BASE}/payments/webhooks/{provider['id']}/", body, content_type="application/json",
                     HTTP_X_PAYMENT_SIGNATURE=sig, HTTP_X_PAYMENT_TIMESTAMP=ts)
    APIClient().post(f"{BASE}/payments/webhooks/{provider['id']}/", body, content_type="application/json",
                     HTTP_X_PAYMENT_SIGNATURE="bad", HTTP_X_PAYMENT_TIMESTAMP=ts)
    platform.post(P(ctx, "payments/reconcile/"), {}, format="json")

    ciphertexts = list(IntegrationCredential.objects.values_list("encrypted_secret", flat=True))
    surfaces = [
        platform.get(P(ctx, "payment-providers/")), platform.get(P(ctx, "credentials/")),
        client.get(f"{BASE}/payments/intents/"), platform.get(P(ctx, "payments/webhook-events/")),
        platform.get(P(ctx, "payments/reconciliation/")),
    ]
    for resp in surfaces:
        assert resp.status_code == 200
        text = resp.content.decode()
        assert WEBHOOK_SECRET not in text and SECRET not in text and sig not in text
        assert not any(c in text for c in ciphertexts)
    assert "raw_body" not in surfaces[3].content.decode()
    assert PaymentWebhookEvent.objects.filter(signature_valid=False).count() == 1

    audit_text = json.dumps(list(AuditLog.objects.values_list("new_values", "old_values")), default=str)
    assert WEBHOOK_SECRET not in audit_text and SECRET not in audit_text and sig not in audit_text


def test_an_undecryptable_webhook_secret_rejects_instead_of_erroring(ctx, settings):
    from apps.integrations.models import PaymentWebhookEvent
    from tests.helpers.payment_factory import deliver, make_provider

    provider = make_provider(ctx, name="rot", secret=WEBHOOK_SECRET)
    settings.INTEGRATION_ENCRYPTION_KEY = Fernet.generate_key().decode()  # old key lost
    event = deliver(provider, event_id="e", reference="r", amount="1")
    assert event.status == PaymentWebhookEvent.STATUS_REJECTED


def test_payment_writes_need_the_matching_permission(ctx):
    from tests.helpers.branch_factory import add_user
    from tests.helpers.payment_factory import make_invoice

    cashier = add_user(ctx, username="pay_cashier", role_slug="cashier", branches=("HODAN",))
    c = auth_client_as(APIClient(), cashier)
    invoice = make_invoice(ctx, "HODAN")
    assert c.post(P(ctx, "payment-providers/"), {"name": "x", "provider_type": "MOCK"}, format="json").status_code == 403
    assert c.post(P(ctx, "payments/reconcile/"), {}, format="json").status_code == 403
    assert c.post(
        f"{BASE}/payments/intents/", {"invoice_id": str(invoice.pk), "idempotency_key": "p"}, format="json"
    ).status_code == 403
