"""SMS sending with failure isolation, bounded retries and no secret leakage.

Contract that the rest of the ERP relies on:

* ``enqueue`` / ``send_safe`` **never raise** — a provider outage, a bad template or a
  missing provider can never break the sale/transfer/shift that asked for an SMS.
* Every attempt is recorded on an ``SmsLog``; retries are bounded (``MAX_ATTEMPTS``) and a
  message that cannot be delivered ends in the terminal ``FAILED`` state, not a queue.
* The provider secret is decrypted only for the duration of one call and scrubbed from
  anything stored or logged.
"""

from __future__ import annotations

import logging
import re
from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils import timezone

from apps.integrations.crypto import SecretDecryptError
from apps.integrations.models import SmsLog, SmsProvider, SmsTemplate
from apps.integrations.providers.base import OK, PERMANENT, TRANSIENT, OutboundSms
from apps.integrations.providers.registry import get_adapter_class
from apps.integrations.services.credential_service import CredentialService
from apps.integrations.services.sms_credit_service import SmsCreditService

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 4
BACKOFF = (timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=30))  # after attempt 1,2,3
_PLACEHOLDER = re.compile(r"\{(\w+)\}")
_NUMBER = re.compile(r"^\+?\d{6,15}$")


class SmsError(ValueError):
    pass


class SmsTemplateError(SmsError):
    pass


def render_template(body: str, context: dict) -> str:
    """``{name}`` substitution only — no attribute access, no format specs, no code paths.
    A placeholder with no value is an error rather than a silently broken message."""
    missing = sorted({m for m in _PLACEHOLDER.findall(body) if m not in context})
    if missing:
        raise SmsTemplateError(f"Missing template values: {', '.join(missing)}")
    return _PLACEHOLDER.sub(lambda m: str(context[m.group(1)]), body)


def scrub(text: str, secret: str | None) -> str:
    text = text or ""
    if secret:
        text = text.replace(secret, "***")
    return text[:300]


class SmsService:
    # ------------------------------------------------------------------ resolution
    @staticmethod
    def resolve_provider(*, tenant_id, branch=None) -> SmsProvider | None:
        """Branch-specific provider wins; otherwise the tenant default (else any tenant-wide one)."""
        qs = SmsProvider.active_objects().filter(tenant_id=tenant_id, is_active=True)
        if branch is not None:
            found = qs.filter(branch=branch).order_by("-is_default", "name").first()
            if found:
                return found
        return qs.filter(branch__isnull=True).order_by("-is_default", "name").first()

    @staticmethod
    def sender_for(provider: SmsProvider, branch=None) -> str:
        return provider.sender_id or (getattr(branch, "code", "") or "")[:11]

    # ------------------------------------------------------------------ create + dispatch
    @staticmethod
    def _create_log(*, tenant, to, branch=None, template=None, body=None, context=None,
                    entity_type="", entity_id="", user=None) -> SmsLog:
        number = re.sub(r"[\s\-()]", "", str(to or ""))
        error = ""
        provider = SmsService.resolve_provider(tenant_id=tenant.pk, branch=branch)
        text = ""
        try:
            if template is not None:
                text = render_template(template.body, context or {})
            else:
                text = render_template(body or "", context or {})
        except SmsTemplateError as exc:
            error = str(exc)
        if not error and not _NUMBER.match(number):
            error = "Invalid phone number."
        if not error and not text.strip():
            error = "Message is empty."
        if not error and provider is None:
            error = "No active SMS provider for this branch."
        log = SmsLog.objects.create(
            tenant=tenant, branch=branch, provider=provider, template=template,
            to_number=number[:32], body=text,
            sender_id=SmsService.sender_for(provider, branch) if provider else "",
            status=SmsLog.STATUS_FAILED if error else SmsLog.STATUS_QUEUED,
            error=error, entity_type=entity_type, entity_id=str(entity_id or ""), created_by=user,
        )
        if log.status == SmsLog.STATUS_QUEUED:
            # Reseller credits: accepted messages reserve their segments; no credit, no send.
            credit_error = SmsCreditService.reserve(log)
            if credit_error:
                log.status, log.error = SmsLog.STATUS_FAILED, credit_error
                log.save(update_fields=["status", "error", "updated_at"])
        return log

    @staticmethod
    def _resolve_template(tenant, template_code):
        if not template_code:
            return None
        return SmsTemplate.active_objects().filter(
            tenant=tenant, code=template_code, is_active=True
        ).first()

    @staticmethod
    def send(*, tenant, to, branch=None, template_code=None, body=None, context=None,
             entity_type="", entity_id="", user=None) -> SmsLog:
        """Create the log and attempt delivery now. Raises only for programmer errors
        (unknown template code); provider trouble is recorded on the returned log."""
        template = SmsService._resolve_template(tenant, template_code)
        if template_code and template is None:
            raise SmsError(f"Unknown SMS template: {template_code}")
        log = SmsService._create_log(
            tenant=tenant, branch=branch, to=to, template=template, body=body, context=context,
            entity_type=entity_type, entity_id=entity_id, user=user,
        )
        if log.status != SmsLog.STATUS_QUEUED:
            return log
        return SmsService.dispatch_safe(log.pk) or SmsLog.objects.get(pk=log.pk)

    @staticmethod
    def enqueue(**kwargs) -> SmsLog | None:
        """Fire-and-forget for business flows: log now (in a savepoint), send after the
        caller's transaction commits. Never raises and never touches the caller's transaction
        state, so an SMS problem cannot roll back or abort the business operation."""
        try:
            with transaction.atomic():
                template = SmsService._resolve_template(kwargs["tenant"], kwargs.pop("template_code", None))
                log = SmsService._create_log(template=template, **{
                    k: v for k, v in kwargs.items()
                    if k in ("tenant", "branch", "to", "body", "context", "entity_type", "entity_id", "user")
                })
            if log.status == SmsLog.STATUS_QUEUED:
                transaction.on_commit(lambda pk=log.pk: SmsService.dispatch_safe(pk))
            return log
        except Exception as exc:  # noqa: BLE001 - isolation is the point
            logger.warning("SMS enqueue failed (%s); business operation unaffected.", type(exc).__name__)
            return None

    @staticmethod
    def dispatch_safe(log_id) -> SmsLog | None:
        try:
            return SmsService.dispatch(log_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("SMS dispatch %s failed (%s).", log_id, type(exc).__name__)
            return None

    @staticmethod
    def dispatch(log_id) -> SmsLog:
        """One delivery attempt. Idempotent: a terminal or not-yet-due log is left alone, and
        the row lock stops two workers sending the same message."""
        with transaction.atomic():
            # Lock only the log row: PostgreSQL refuses FOR UPDATE across the nullable provider join.
            log = (
                SmsLog.objects.select_for_update(of=("self",))
                .select_related("provider", "provider__credential")
                .get(pk=log_id)
            )
            if log.status in SmsLog.TERMINAL:
                return log
            if log.status == SmsLog.STATUS_RETRYING and log.next_retry_at and log.next_retry_at > timezone.now():
                return log
            secret = None
            try:
                result, secret = SmsService._call_provider(log)
            except Exception as exc:  # noqa: BLE001 - adapters must not raise, but never trust that
                logger.warning("SMS %s: unexpected provider error (%s).", log.pk, type(exc).__name__)
                result = SendResultLike(TRANSIENT, "Unexpected provider error.")
            SmsService._apply_result(log, result, secret)
        logger.info("sms %s status=%s attempts=%s", log.pk, log.status, log.attempts)
        return log

    @staticmethod
    def _call_provider(log: SmsLog):
        provider = log.provider
        if provider is None or not provider.is_active:
            return SendResultLike(PERMANENT, "SMS provider is not available."), None
        try:
            adapter_cls = get_adapter_class(provider.provider_type)
            secret = CredentialService.reveal(provider.credential)
        except (LookupError,):
            return SendResultLike(PERMANENT, "Unsupported SMS provider type."), None
        except (ImproperlyConfigured, SecretDecryptError):
            # Operator problem, retrying will not help until the key/secret is fixed.
            return SendResultLike(PERMANENT, "Integration credentials cannot be used."), None
        adapter = adapter_cls(config=provider.config, secret=secret)
        result = adapter.send(OutboundSms(to=log.to_number, body=log.body, sender_id=log.sender_id))
        return result, secret

    @staticmethod
    def _apply_result(log: SmsLog, result, secret):
        log.attempts += 1
        log.error = ""
        log.next_retry_at = None
        if result.outcome == OK:
            log.status = SmsLog.STATUS_SENT
            log.sent_at = timezone.now()
            log.provider_reference = (result.reference or "")[:190]
        elif result.outcome == TRANSIENT and log.attempts < MAX_ATTEMPTS:
            log.status = SmsLog.STATUS_RETRYING
            log.error = scrub(result.error, secret)
            log.next_retry_at = timezone.now() + BACKOFF[min(log.attempts, len(BACKOFF)) - 1]
        else:
            log.status = SmsLog.STATUS_FAILED
            suffix = " (retries exhausted)" if result.outcome == TRANSIENT else ""
            log.error = scrub(result.error + suffix, secret)
        log.save(update_fields=[
            "attempts", "status", "error", "next_retry_at", "sent_at", "provider_reference", "updated_at",
        ])
        if log.status in SmsLog.TERMINAL:
            SmsCreditService.settle(log)  # SENT keeps the charge; FAILED returns it

    @staticmethod
    def retry_due(*, now=None, limit=100) -> int:
        """Re-attempt RETRYING messages whose backoff has elapsed. Returns how many were tried."""
        now = now or timezone.now()
        ids = list(
            SmsLog.objects.filter(status=SmsLog.STATUS_RETRYING, next_retry_at__lte=now)
            .order_by("next_retry_at").values_list("pk", flat=True)[:limit]
        )
        for pk in ids:
            SmsService.dispatch_safe(pk)
        return len(ids)


class SendResultLike:
    def __init__(self, outcome, error=""):
        self.outcome, self.error, self.reference = outcome, error, ""
