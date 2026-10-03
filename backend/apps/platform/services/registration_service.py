"""Security-sensitive public registration and tenant provisioning orchestration."""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services import write_audit
from apps.finance.services.chart_service import ChartService
from apps.platform.models import (
    AgreementAcceptance,
    EmailVerification,
    Module,
    ProvisioningJob,
    RegistrationRequest,
    SubscriptionPlan,
    Tenant,
)
from apps.platform.services.business_preset_service import BusinessPresetService
from apps.platform.services.domain_utils import (
    build_tenant_hostname,
    check_subdomain_availability,
    suggest_subdomains,
    validate_tenant_slug,
)
from apps.platform.services.entitlement_service import EntitlementService
from apps.platform.services.module_dependency_service import ModuleDependencyService
from apps.platform.services.module_service import ensure_default_modules, module_payload
from apps.platform.services.platform_service import PlatformService, SubdomainTakenError
from apps.authentication.models import User

logger = logging.getLogger(__name__)


class RegistrationError(ValueError):
    def __init__(
        self,
        message,
        *,
        code="REGISTRATION_ERROR",
        field_errors=None,
        status=400,
        suggestions=None,
    ):
        super().__init__(message)
        self.code = code
        self.field_errors = field_errors or {}
        self.status = status
        self.suggestions = suggestions or []


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_fingerprint(payload: dict) -> str:
    return _sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "") if request else ""
    return (forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")) if request else None


class PublicCatalogService:
    @staticmethod
    def catalog() -> dict:
        PlatformService.ensure_default_business_types()
        PlatformService.ensure_default_plans()
        BusinessPresetService.ensure_default_presets()
        ensure_default_modules()
        EntitlementService.ensure_default_plan_modules()
        return {
            "business_types": [
                PlatformService.business_type_payload(x)
                for x in PlatformService.list_business_types(active_only=True)
            ],
            "business_presets": [
                BusinessPresetService.serialize(x)
                for x in BusinessPresetService.list_presets()
            ],
            "modules": [module_payload(x) for x in Module.active_objects().filter(is_active=True)],
            "plans": [
                payload
                for plan in SubscriptionPlan.active_objects().filter(is_active=True).order_by("monthly_price", "name")
                for payload in [PlatformService.plan_payload(plan)]
                if payload.get("modules")
            ],
            "base_domain": settings.TENANT_BASE_DOMAIN,
            "public_app_url": getattr(settings, "PUBLIC_APP_URL", "https://erp.safaritechno.com"),
            "terms_version": getattr(settings, "TERMS_VERSION", "2026-09-01"),
            "privacy_version": getattr(settings, "PRIVACY_VERSION", "2026-09-01"),
            "email_verification_required": getattr(settings, "REGISTRATION_REQUIRE_EMAIL_VERIFICATION", False),
        }


class TenantProvisioningService:
    STAGES = ("company", "workspace", "owner", "modules", "subscription", "accounting", "final_checks")

    @staticmethod
    def _job(registration, stage, status, *, tenant=None, message="", category=""):
        now = timezone.now()
        return ProvisioningJob.objects.create(
            registration=registration,
            tenant=tenant,
            stage=stage,
            status=status,
            attempt=registration.retry_count + 1,
            started_at=now,
            completed_at=now if status in {ProvisioningJob.STATUS_SUCCEEDED, ProvisioningJob.STATUS_FAILED} else None,
            safe_message=message[:500],
            failure_category=category[:64],
        )

    @staticmethod
    @transaction.atomic
    def provision(registration: RegistrationRequest) -> RegistrationRequest:
        registration = RegistrationRequest.objects.select_for_update().get(pk=registration.pk)
        if registration.status == RegistrationRequest.STATUS_READY:
            return registration
        registration.status = RegistrationRequest.STATUS_PROVISIONING
        registration.failure_category = ""
        registration.failure_message = ""
        registration.save(update_fields=["status", "failure_category", "failure_message", "updated_at"])
        TenantProvisioningService._job(registration, "company", ProvisioningJob.STATUS_RUNNING)
        payload = dict(registration.payload)
        owner = dict(payload.get("owner") or {})
        owner["_password_hash"] = registration.owner_password_hash
        payload["owner"] = owner
        payload["_registration_id"] = str(registration.pk)  # its own slug hold must not block it
        try:
            tenant, owner_user = PlatformService.create_shop(data=payload, user=None)
            registration.tenant = tenant
            TenantProvisioningService._job(registration, "company", ProvisioningJob.STATUS_SUCCEEDED, tenant=tenant)
            for stage in ("workspace", "owner", "modules", "subscription"):
                TenantProvisioningService._job(registration, stage, ProvisioningJob.STATUS_SUCCEEDED, tenant=tenant)
            TenantProvisioningService._job(registration, "accounting", ProvisioningJob.STATUS_RUNNING, tenant=tenant)
            ChartService.ensure_default_chart(tenant_id=tenant.id, user=owner_user)
            TenantProvisioningService._job(registration, "accounting", ProvisioningJob.STATUS_SUCCEEDED, tenant=tenant)
            for agreement in registration.agreements.all():
                agreement.tenant = tenant
                agreement.user = owner_user
                agreement.save(update_fields=["tenant", "user", "updated_at"])
            TenantProvisioningService._job(registration, "final_checks", ProvisioningJob.STATUS_SUCCEEDED, tenant=tenant)
            registration.status = RegistrationRequest.STATUS_READY
            registration.completed_at = timezone.now()
            registration.save(update_fields=["tenant", "status", "completed_at", "updated_at"])
            write_audit(action="registration_completed", module="platform", entity=tenant, user=owner_user, new_values={"registration_id": str(registration.id), "subdomain": registration.subdomain})
            logger.info("tenant provisioning completed", extra={"registration_id": str(registration.id), "tenant_id": str(tenant.id), "subdomain": registration.subdomain, "provisioning_stage": "ready"})
            RegistrationService.request_tls_sync(registration.subdomain)
            return registration
        except Exception as exc:
            logger.exception("tenant provisioning failed", extra={"registration_id": str(registration.id), "subdomain": registration.subdomain, "provisioning_stage": "failed"})
            raise exc


class RegistrationService:
    @staticmethod
    def check_subdomain(raw: str) -> dict:
        return check_subdomain_availability(raw)

    @staticmethod
    def _validate(data: dict) -> tuple[dict, str]:
        company = data.get("company") if isinstance(data.get("company"), dict) else {}
        owner = data.get("owner") if isinstance(data.get("owner"), dict) else {}
        agreements = data.get("agreements") if isinstance(data.get("agreements"), dict) else {}
        name = (company.get("trading_name") or company.get("legal_name") or data.get("name") or "").strip()
        email = (owner.get("email") or company.get("contact_email") or "").strip().lower()
        username = (owner.get("username") or email.split("@")[0] or "").strip()
        password = owner.get("password") or ""
        field_errors = {}
        if not name: field_errors["company.trading_name"] = ["Company name is required."]
        try: validate_email(email)
        except ValidationError: field_errors["owner.email"] = ["Enter a valid email address."]
        try: validate_password(password)
        except ValidationError as exc: field_errors["owner.password"] = list(exc.messages)
        if username and User.objects.filter(username__iexact=username, deleted_at__isnull=True).exists():
            field_errors["owner.username"] = ["This username is already in use."]
        try: slug = validate_tenant_slug(data.get("subdomain") or data.get("slug") or "")
        except ValueError as exc:
            slug = ""
            field_errors["subdomain"] = [str(exc)]
        if not agreements.get("terms_accepted"): field_errors["agreements.terms_accepted"] = ["Terms must be accepted."]
        if not agreements.get("privacy_accepted"): field_errors["agreements.privacy_accepted"] = ["Privacy Policy must be accepted."]
        PlatformService.ensure_default_business_types(); PlatformService.ensure_default_plans(); BusinessPresetService.ensure_default_presets(); ensure_default_modules(); EntitlementService.ensure_default_plan_modules()
        bt = PlatformService.resolve_business_type(code=(data.get("business_type_code") or "retail").strip().lower())
        if not bt: field_errors["business_type_code"] = ["Select a valid business type."]
        preset_code = (data.get("preset_code") or "custom").strip().lower()
        preset = BusinessPresetService.resolve(code=preset_code)
        if not preset and preset_code != "custom": field_errors["preset_code"] = ["Select a valid business preset."]
        plan_code = (data.get("plan_code") or "starter").strip().lower()
        plan = SubscriptionPlan.active_objects().filter(code=plan_code, is_active=True).first()
        if not plan: field_errors["plan_code"] = ["Select a valid plan."]
        requested = data.get("modules") if isinstance(data.get("modules"), list) else []
        if not requested and preset: requested = BusinessPresetService.module_codes(preset)
        try: modules = sorted(ModuleDependencyService.validate_enable_set(requested))
        except ValueError as exc:
            modules = []
            field_errors["modules"] = [str(exc)]
        if plan:
            allowed = EntitlementService.plan_module_codes(plan=plan)
            disallowed = sorted(set(modules) - allowed)
            if disallowed: field_errors["modules"] = [f"Not included in {plan.name}: {', '.join(disallowed)}."]
        if field_errors: raise RegistrationError("Please correct the highlighted fields.", code="VALIDATION_ERROR", field_errors=field_errors)
        payload = {
            "name": name, "legal_name": (company.get("legal_name") or name).strip(), "address": (company.get("address") or "").strip(),
            "contact_email": (company.get("contact_email") or email).strip().lower(), "contact_phone": (company.get("contact_phone") or owner.get("phone") or "").strip(),
            "country": (company.get("country") or "").strip(), "currency": (company.get("currency") or "USD").upper(), "timezone": company.get("timezone") or "UTC", "language": company.get("language") or "en",
            "slug": slug, "subdomain": slug, "business_type_code": bt.code, "preset_code": preset_code, "plan_code": plan_code, "trial_days": int(data.get("trial_days") or 14), "modules": modules,
            "branch_name": (company.get("branch_name") or "Main Branch").strip(), "settings": {"date_format": company.get("date_format") or "YYYY-MM-DD", "fiscal_year_start_month": int(company.get("fiscal_year_start_month") or 1)},
            "owner": {"username": username, "email": email, "first_name": (owner.get("first_name") or "").strip(), "last_name": (owner.get("last_name") or "").strip(), "phone": (owner.get("phone") or "").strip(), "role_slug": "admin"},
        }
        return payload, password

    @staticmethod
    @transaction.atomic
    def create(*, data: dict, idempotency_key: str, request=None) -> RegistrationRequest:
        if not idempotency_key or len(idempotency_key) < 16:
            raise RegistrationError("A valid Idempotency-Key header is required.", code="IDEMPOTENCY_REQUIRED")
        payload, password = RegistrationService._validate(data)
        key_hash = _sha256(idempotency_key[:200])
        fingerprint = _canonical_fingerprint(payload)
        existing = RegistrationRequest.active_objects().filter(idempotency_key_hash=key_hash).first()
        if existing:
            if existing.payload_fingerprint != fingerprint:
                raise RegistrationError("This idempotency key was used for a different request.", code="IDEMPOTENCY_CONFLICT", status=409)
            return existing
        if RegistrationService.check_subdomain(payload["slug"])["available"] is False:
            avail = RegistrationService.check_subdomain(payload["slug"])
            raise RegistrationError(
                "This workspace URL was just taken. Please choose another.",
                code="SUBDOMAIN_TAKEN",
                field_errors={"subdomain": ["Choose another workspace URL."]},
                status=409,
                suggestions=avail.get("suggestions") or [],
            )
        require_verification = getattr(settings, "REGISTRATION_REQUIRE_EMAIL_VERIFICATION", False)
        try:
            registration = RegistrationRequest.objects.create(
                status=RegistrationRequest.STATUS_PENDING_EMAIL if require_verification else RegistrationRequest.STATUS_VERIFIED,
                mode=RegistrationRequest.MODE_TRIAL, email=payload["owner"]["email"], subdomain=payload["slug"], payload=payload,
                payload_fingerprint=fingerprint, idempotency_key_hash=key_hash, owner_password_hash=make_password(password), verified_at=None if require_verification else timezone.now(),
            )
        except IntegrityError as exc:
            raise RegistrationError(
                "This workspace URL was just taken. Please choose another.",
                code="SUBDOMAIN_TAKEN",
                status=409,
                suggestions=suggest_subdomains(payload["slug"]),
            ) from exc
        now = timezone.now()
        for doc, accepted_key, version_key in (("terms", "terms_accepted", "terms_version"), ("privacy", "privacy_accepted", "privacy_version")):
            AgreementAcceptance.objects.create(registration=registration, document_type=doc, document_version=str((data.get("agreements") or {}).get(version_key) or getattr(settings, version_key.upper(), "2026-09-01")), accepted_at=now, ip_address=_client_ip(request), user_agent=(request.META.get("HTTP_USER_AGENT", "")[:300] if request else ""))
        if require_verification:
            RegistrationService.send_verification(registration)
        else:
            try:
                TenantProvisioningService.provision(registration)
            except SubdomainTakenError as exc:
                registration.refresh_from_db()
                registration.status = RegistrationRequest.STATUS_FAILED_RETRYABLE
                registration.failure_category = "subdomain"
                registration.failure_message = str(exc)
                registration.retry_count += 1
                registration.save(update_fields=["status", "failure_category", "failure_message", "retry_count", "updated_at"])
                raise RegistrationError(
                    str(exc),
                    code=SubdomainTakenError.code,
                    field_errors={"subdomain": [str(exc)]},
                    status=409,
                    suggestions=exc.suggestions,
                ) from exc
            except Exception:
                registration.refresh_from_db()
                registration.status = RegistrationRequest.STATUS_FAILED_RETRYABLE
                registration.failure_category = "provisioning"
                registration.failure_message = "We could not finish setting up your workspace. Please try again shortly."
                registration.retry_count += 1
                registration.save(update_fields=["status", "failure_category", "failure_message", "retry_count", "updated_at"])
                TenantProvisioningService._job(
                    registration,
                    "provisioning",
                    ProvisioningJob.STATUS_FAILED,
                    message=registration.failure_message,
                    category=registration.failure_category,
                )
        return RegistrationRequest.objects.select_related("tenant").get(pk=registration.pk)

    @staticmethod
    def send_verification(registration):
        raw = secrets.token_urlsafe(32)
        EmailVerification.objects.create(registration=registration, token_hash=_sha256(raw), expires_at=timezone.now() + timedelta(hours=24))
        url = f"{getattr(settings, 'PUBLIC_APP_URL', 'https://erp.safaritechno.com')}/verify-email?token={raw}"
        send_mail("Verify your Safari ERP email", f"Verify your email to create your workspace: {url}", getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@safaritechno.com"), [registration.email], fail_silently=False)

    @staticmethod
    @transaction.atomic
    def verify(token: str):
        row = EmailVerification.objects.select_for_update().filter(token_hash=_sha256(token or ""), deleted_at__isnull=True).first()
        if not row or row.consumed_at or row.expires_at <= timezone.now():
            raise RegistrationError("Verification link is invalid or expired.", code="VERIFICATION_INVALID")
        row.consumed_at = timezone.now(); row.attempts += 1; row.save(update_fields=["consumed_at", "attempts", "updated_at"])
        reg = row.registration; reg.status = RegistrationRequest.STATUS_VERIFIED; reg.verified_at = timezone.now(); reg.save(update_fields=["status", "verified_at", "updated_at"])
        return TenantProvisioningService.provision(reg)

    @staticmethod
    def request_tls_sync(subdomain: str = "") -> None:
        """Ask the host sync-erp-cert job to expand SANs for the new shop hostname."""
        try:
            from pathlib import Path

            base = Path(getattr(settings, "MEDIA_ROOT", "/app/media")) / ".system"
            base.mkdir(parents=True, exist_ok=True)
            marker = base / "tls-sync-request"
            payload = f"{timezone.now().isoformat()} {subdomain or ''}\n"
            marker.write_text(payload, encoding="utf-8")
            host_marker = Path("/var/lib/mda/tls-sync/request")
            try:
                host_marker.parent.mkdir(parents=True, exist_ok=True)
                host_marker.write_text(payload, encoding="utf-8")
            except OSError:
                # Host bind-mount is optional; media marker is enough for the cron job.
                pass
            logger.info("tls sync requested", extra={"subdomain": subdomain})
        except Exception:
            logger.exception("failed to request tls sync", extra={"subdomain": subdomain})

    @staticmethod
    def workspace_tls_ready(hostname: str) -> bool:
        """True when the public hostname presents a valid certificate matching the name."""
        import socket
        import ssl

        host = (hostname or "").strip().lower().rstrip(".")
        if not host:
            return False
        try:
            context = ssl.create_default_context()
            with socket.create_connection((host, 443), timeout=4) as sock:
                with context.wrap_socket(sock, server_hostname=host):
                    return True
        except Exception:
            return False

    @staticmethod
    def payload(registration):
        tenant = registration.tenant
        jobs = [{"stage": x.stage, "status": x.status, "message": x.safe_message} for x in registration.jobs.all()]
        hostname = build_tenant_hostname(registration.subdomain)
        tls_ready = False
        if registration.status == RegistrationRequest.STATUS_READY and hostname:
            tls_ready = RegistrationService.workspace_tls_ready(hostname)
        return {
            "id": str(registration.id),
            "status": registration.status,
            "subdomain": registration.subdomain,
            "hostname": hostname,
            "workspace_url": f"https://{hostname}",
            "tls_ready": tls_ready,
            "tenant_id": str(tenant.id) if tenant else None,
            "failure_category": registration.failure_category,
            "message": registration.failure_message,
            "stages": jobs,
        }
