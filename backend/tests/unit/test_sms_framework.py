"""B7-1..B7-5: SMS provider registry, templates, failure isolation, bounded retry, safe logs."""

from __future__ import annotations

from datetime import timedelta
from unittest import mock

import pytest
import requests
from cryptography.fernet import Fernet
from django.db import transaction
from django.utils import timezone

from apps.integrations.models import IntegrationCredential, SmsLog, SmsProvider, SmsTemplate
from apps.integrations.providers import custom_http
from apps.integrations.providers.mock import MockProvider
from apps.integrations.providers.registry import PROVIDER_REGISTRY, get_adapter_class
from apps.integrations.services import CredentialService, SmsError, SmsService, render_template
from apps.integrations.services.sms_service import MAX_ATTEMPTS, SmsTemplateError
from tests.helpers.branch_factory import add_owner, build_branch_tenant

pytestmark = pytest.mark.django_db

SECRET = "S3CRET-VALUE-XYZ-123456"
URL = "https://gateway.example.test/send"


@pytest.fixture(autouse=True)
def key(settings):
    settings.INTEGRATION_ENCRYPTION_KEY = Fernet.generate_key().decode()
    MockProvider.outbox.clear()


@pytest.fixture(autouse=True)
def public_dns():
    with mock.patch.object(custom_http.socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 0))]):
        yield


@pytest.fixture
def ctx():
    return build_branch_tenant(slug="sms-tenant", branch_codes=("HODAN", "BAKAARO"))


@pytest.fixture
def owner(ctx):
    return add_owner(ctx, username="sms_owner")


def mock_provider(ctx, *, mode="success", branch=None, default=True, sender="ACME", name=None, **extra):
    return SmsProvider.objects.create(
        tenant=ctx.tenant, name=name or f"mock-{mode}-{branch or 'all'}", provider_type="MOCK",
        branch=ctx.branch(branch) if branch else None, sender_id=sender, is_default=default,
        config={"mode": mode}, **extra,
    )


def http_provider(ctx, *, config=None, secret=SECRET):
    cred = CredentialService.create(tenant=ctx.tenant, label="gw", secret=secret)
    return SmsProvider.objects.create(
        tenant=ctx.tenant, name="gw", provider_type="CUSTOM_HTTP", credential=cred, is_default=True,
        config={
            "url": URL, "headers": {"Authorization": "Bearer {secret}"},
            "body": {"to": "{to}", "text": "{message}", "from": "{sender}"},
            "reference_path": "data.id", **(config or {}),
        },
    )


def send(ctx, **kw):
    kw.setdefault("body", "hello")
    return SmsService.send(tenant=ctx.tenant, to="+252611234567", branch=ctx.branch("HODAN"), **kw)


def resp(status=200, json=None, bad_json=False):
    r = mock.Mock(status_code=status)
    r.json.side_effect = ValueError("bad") if bad_json else (lambda: json)
    return r


# --------------------------------------------------------------------------- #
# B7-1: only Mock and generic CustomHttp exist
# --------------------------------------------------------------------------- #


def test_registry_has_exactly_the_mock_and_custom_http_adapters():
    assert set(PROVIDER_REGISTRY) == {"MOCK", "CUSTOM_HTTP"}
    assert get_adapter_class("MOCK").type_code == "MOCK"
    with pytest.raises(LookupError):
        get_adapter_class("SOMALI_TELECOM_X")  # no invented vendor adapters (D7)
    assert {c[0] for c in SmsProvider.TYPE_CHOICES} == {"MOCK", "CUSTOM_HTTP"}


def test_custom_http_refuses_plain_http_and_internal_addresses():
    adapter = lambda cfg: custom_http.CustomHttpProvider(config=cfg, secret=None)  # noqa: E731
    assert adapter({"url": URL}).validate_config() == []
    assert adapter({"url": "http://gateway.example.test/x"}).validate_config()  # not https
    assert adapter({"url": "ftp://x"}).validate_config()
    with mock.patch.object(custom_http.socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("10.0.0.5", 0))]):
        assert "private" in adapter({"url": URL}).validate_config()[0]
    with mock.patch.object(custom_http.socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 0))]):
        assert adapter({"url": URL}).validate_config()


# --------------------------------------------------------------------------- #
# B7-2: template rendering and per-tenant / per-branch sender resolution
# --------------------------------------------------------------------------- #


def test_template_renders_placeholders_and_rejects_missing_values():
    assert render_template("Hi {name}, total {amount}", {"name": "Amina", "amount": 12}) == "Hi Amina, total 12"
    with pytest.raises(SmsTemplateError, match="amount"):
        render_template("Hi {name}, total {amount}", {"name": "Amina"})


def test_template_is_not_a_code_path():
    # Attribute access / format specs are inert text, never evaluated.
    assert render_template("{a.__class__} {b!r}", {"a": 1, "b": 2}) == "{a.__class__} {b!r}"


def test_send_by_template_code_renders_into_the_log(ctx):
    mock_provider(ctx)
    SmsTemplate.objects.create(tenant=ctx.tenant, code="receipt", name="Receipt", body="Thanks {name}: {amount}")
    log = send(ctx, body=None, template_code="receipt", context={"name": "Amina", "amount": "12.00"})
    assert (log.status, log.body) == ("SENT", "Thanks Amina: 12.00")
    assert log.template.code == "receipt" and MockProvider.outbox[-1].body == "Thanks Amina: 12.00"
    with pytest.raises(SmsError, match="Unknown SMS template"):
        send(ctx, body=None, template_code="nope")


def test_a_message_with_missing_template_values_is_logged_failed_not_sent(ctx):
    mock_provider(ctx)
    log = send(ctx, body="Hi {name}")
    assert log.status == "FAILED" and "name" in log.error and not MockProvider.outbox


def test_branch_provider_overrides_tenant_default_and_falls_back(ctx):
    tenant_wide = mock_provider(ctx, sender="TENANT")
    hodan = mock_provider(ctx, branch="HODAN", sender="HODAN-SMS", name="hodan")
    inactive = mock_provider(ctx, branch="BAKAARO", sender="OFF", name="off", default=False, is_active=False)

    on_hodan = send(ctx)
    on_bakaaro = SmsService.send(tenant=ctx.tenant, to="+252611234567", branch=ctx.branch("BAKAARO"), body="hi")

    assert (on_hodan.provider_id, on_hodan.sender_id) == (hodan.pk, "HODAN-SMS")
    assert (on_bakaaro.provider_id, on_bakaaro.sender_id) == (tenant_wide.pk, "TENANT")  # inactive ignored
    assert inactive.pk not in {on_hodan.provider_id, on_bakaaro.provider_id}


def test_provider_resolution_never_crosses_tenants(ctx):
    other = build_branch_tenant(slug="sms-other", branch_codes=("REMOTE",))
    mock_provider(other, sender="THEIRS")
    log = send(ctx)  # our tenant has no provider
    assert log.status == "FAILED" and "No active SMS provider" in log.error and log.provider_id is None


def test_sender_falls_back_to_the_branch_code(ctx):
    mock_provider(ctx, sender="")
    assert send(ctx).sender_id == "HODAN"


def test_invalid_number_is_logged_failed(ctx):
    mock_provider(ctx)
    log = SmsService.send(tenant=ctx.tenant, to="not-a-number", body="hi")
    assert log.status == "FAILED" and "phone" in log.error


# --------------------------------------------------------------------------- #
# B7-3: a provider problem never breaks the business transaction
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("mode", ["timeout", "server_error", "malformed"])
def test_mock_provider_failures_are_results_not_exceptions(ctx, mode):
    mock_provider(ctx, mode=mode)
    log = send(ctx)
    assert log.status == "RETRYING" and log.attempts == 1 and log.error


@pytest.mark.parametrize(
    "outcome, expected",
    [
        (requests.Timeout("t"), ("RETRYING", "timed out")),
        (requests.ConnectionError("boom"), ("RETRYING", "Could not reach")),
        (resp(503), ("RETRYING", "HTTP 503")),
        (resp(429), ("RETRYING", "HTTP 429")),
        (resp(200, bad_json=True), ("RETRYING", "unreadable")),  # accepted? unknowable -> retry
        (resp(200, json={"nope": 1}), ("RETRYING", "unreadable")),
        (resp(400), ("FAILED", "HTTP 400")),  # our request is wrong: retrying is pointless
        (resp(302), ("FAILED", "HTTP 302")),  # redirects are never followed
    ],
)
def test_custom_http_maps_every_failure_shape_without_raising(ctx, outcome, expected):
    http_provider(ctx)
    side = {"side_effect": outcome} if isinstance(outcome, Exception) else {"return_value": outcome}
    with mock.patch.object(custom_http.requests, "request", **side):
        log = send(ctx)
    assert log.status == expected[0] and expected[1] in log.error


def test_custom_http_success_records_the_provider_reference(ctx):
    http_provider(ctx)
    with mock.patch.object(custom_http.requests, "request", return_value=resp(200, {"data": {"id": "msg-77"}})) as call:
        log = send(ctx)
    assert (log.status, log.provider_reference, log.attempts) == ("SENT", "msg-77", 1)
    kwargs = call.call_args.kwargs
    assert kwargs["headers"]["Authorization"] == f"Bearer {SECRET}"  # injected at send time
    assert kwargs["allow_redirects"] is False and kwargs["json"]["to"] == "+252611234567"


def test_an_unexpected_adapter_exception_is_contained(ctx):
    mock_provider(ctx)
    with mock.patch.object(MockProvider, "send", side_effect=RuntimeError("driver exploded")):
        log = send(ctx)
    assert log.status == "RETRYING" and "driver exploded" not in log.error


def test_enqueue_inside_a_business_transaction_cannot_break_it(ctx, django_capture_on_commit_callbacks):
    from apps.settings_app.models import Branch

    mock_provider(ctx, mode="server_error")
    with django_capture_on_commit_callbacks(execute=True):
        with transaction.atomic():
            Branch.objects.filter(pk=ctx.branch("HODAN").pk).update(name="Renamed")  # the business write
            log = SmsService.enqueue(tenant=ctx.tenant, to="+252611234567", branch=ctx.branch("HODAN"), body="x")
            # Even a hard failure while queuing is swallowed and leaves the transaction usable.
            with mock.patch.object(SmsService, "_create_log", side_effect=RuntimeError("db down")):
                assert SmsService.enqueue(tenant=ctx.tenant, to="+252611234567", body="y") is None
            Branch.objects.filter(pk=ctx.branch("BAKAARO").pk).update(name="AlsoRenamed")
    assert Branch.objects.get(pk=ctx.branch("HODAN").pk).name == "Renamed"
    assert Branch.objects.get(pk=ctx.branch("BAKAARO").pk).name == "AlsoRenamed"
    log.refresh_from_db()
    assert log.status == "RETRYING"  # sent after commit; the outage only affected the SMS


def test_enqueue_delivers_after_commit(ctx, django_capture_on_commit_callbacks):
    mock_provider(ctx)
    with django_capture_on_commit_callbacks(execute=True):
        with transaction.atomic():
            log = SmsService.enqueue(tenant=ctx.tenant, to="+252611234567", body="ok")
            assert log.status == "QUEUED" and not MockProvider.outbox  # nothing sent mid-transaction
    log.refresh_from_db()
    assert log.status == "SENT" and len(MockProvider.outbox) == 1


def test_enqueue_with_no_provider_records_a_failed_log_and_returns(ctx):
    log = SmsService.enqueue(tenant=ctx.tenant, to="+252611234567", body="x")
    assert log.status == "FAILED"


# --------------------------------------------------------------------------- #
# B7-4: bounded retry, terminal states
# --------------------------------------------------------------------------- #


def make_due(log):
    SmsLog.objects.filter(pk=log.pk).update(next_retry_at=timezone.now() - timedelta(seconds=1))


def test_transient_failures_retry_with_growing_backoff_then_end_terminal(ctx):
    mock_provider(ctx, mode="timeout")
    log = send(ctx)
    delays = []
    while True:
        log.refresh_from_db()
        if log.status != "RETRYING":
            break
        delays.append(log.next_retry_at - timezone.now())
        make_due(log)
        assert SmsService.retry_due() == 1

    log.refresh_from_db()
    assert (log.status, log.attempts) == ("FAILED", MAX_ATTEMPTS)  # bounded
    assert "retries exhausted" in log.error and log.next_retry_at is None
    assert delays == sorted(delays) and len(delays) == MAX_ATTEMPTS - 1  # 1m < 5m < 30m
    assert SmsService.retry_due() == 0  # nothing left in the queue: no infinite retry


def test_retry_is_not_attempted_before_it_is_due(ctx):
    mock_provider(ctx, mode="timeout")
    log = send(ctx)
    assert SmsService.retry_due() == 0
    SmsService.dispatch(log.pk)  # a stray dispatch before the backoff elapsed is a no-op
    log.refresh_from_db()
    assert log.attempts == 1


def test_permanent_failure_is_terminal_immediately(ctx):
    mock_provider(ctx, mode="rejected")
    log = send(ctx)
    assert (log.status, log.attempts, log.next_retry_at) == ("FAILED", 1, None)


def test_a_recovering_provider_delivers_on_retry_exactly_once(ctx):
    provider = mock_provider(ctx, mode="timeout")
    log = send(ctx)
    provider.config = {"mode": "success"}
    provider.save()
    make_due(log)
    SmsService.retry_due()
    SmsService.retry_due()
    SmsService.dispatch(log.pk)
    log.refresh_from_db()
    assert (log.status, log.attempts) == ("SENT", 2) and len(MockProvider.outbox) == 1


def test_a_sent_message_is_never_dispatched_again(ctx):
    mock_provider(ctx)
    log = send(ctx)
    SmsService.dispatch(log.pk)
    SmsService.dispatch(log.pk)
    assert len(MockProvider.outbox) == 1


# --------------------------------------------------------------------------- #
# B7-5: SmsLog records status and reference, never the credential
# --------------------------------------------------------------------------- #


def log_text(log):
    return " ".join(str(getattr(log, f.name, "")) for f in SmsLog._meta.fields)


def test_log_keeps_status_and_reference_but_never_the_secret(ctx):
    http_provider(ctx)
    with mock.patch.object(custom_http.requests, "request", return_value=resp(200, {"data": {"id": "ref-1"}})):
        ok = send(ctx)
    with mock.patch.object(custom_http.requests, "request", return_value=resp(500)):
        failed = send(ctx)
    assert (ok.status, ok.provider_reference) == ("SENT", "ref-1")
    assert failed.status == "RETRYING"
    for log in (ok, failed):
        log.refresh_from_db()
        assert SECRET not in log_text(log)


def test_an_exception_that_embeds_the_secret_is_not_stored(ctx):
    http_provider(ctx)
    leaky = requests.ConnectionError(f"HTTPSConnectionPool(url=...?key={SECRET})")
    with mock.patch.object(custom_http.requests, "request", side_effect=leaky):
        log = send(ctx)
    log.refresh_from_db()
    assert log.status == "RETRYING" and SECRET not in log_text(log)


def test_error_text_is_scrubbed_even_if_an_adapter_echoes_the_secret(ctx):
    from apps.integrations.providers.base import SendResult, TRANSIENT

    http_provider(ctx)
    echo = SendResult(TRANSIENT, error=f"gateway said: bad key {SECRET}")
    with mock.patch.object(custom_http.CustomHttpProvider, "send", return_value=echo):
        log = send(ctx)
    log.refresh_from_db()
    assert SECRET not in log.error and "***" in log.error
