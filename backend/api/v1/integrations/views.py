"""Integrations API — credentials, SMS providers/templates/logs, send.

Credentials and SMS providers are platform infrastructure: only a global platform administrator may
manage them (``IsPlatformIntegrationsAdmin``, explicit ``tenant_id``), mounted under
``/api/v1/platform/integrations/``. Templates, logs and sending stay tenant-scoped.

No response here ever contains a secret or ciphertext: credentials serialise through
``CredentialService.serialize`` (``has_secret`` + masked tail only).
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.audit.services.audit_write import write_audit
from apps.integrations.models import IntegrationCredential, SmsLog, SmsProvider, SmsTemplate
from apps.integrations.providers.registry import PROVIDER_REGISTRY
from apps.integrations.services import CredentialError, CredentialService, SmsError, SmsService
from core.branching import accessible_branches, get_branch_scope, has_branch_permission
from core.responses.api_response import error_response, success_response
from core.tenancy import resolve_acting_tenant
from permissions.base import HasPermission

from .platform_access import IsPlatformIntegrationsAdmin, parse_uuid, target_tenant, tenant_branch

MODULE = "integrations"


def _tenant(request):
    return resolve_acting_tenant(request=request, user=request.user)


def _bad(message, code=status.HTTP_400_BAD_REQUEST):
    return error_response(message=message, status=code)


def _provider_dict(p: SmsProvider) -> dict:
    return {
        "id": str(p.pk), "name": p.name, "provider_type": p.provider_type,
        "branch_id": str(p.branch_id) if p.branch_id else None, "sender_id": p.sender_id,
        "credential_id": str(p.credential_id) if p.credential_id else None,
        "config": p.config, "is_active": p.is_active, "is_default": p.is_default,
    }


def _log_dict(log: SmsLog) -> dict:
    return {
        "id": str(log.pk), "branch_id": str(log.branch_id) if log.branch_id else None,
        "provider_id": str(log.provider_id) if log.provider_id else None,
        "to": log.to_number, "sender_id": log.sender_id, "body": log.body, "status": log.status,
        "provider_reference": log.provider_reference, "attempts": log.attempts,
        "next_retry_at": log.next_retry_at.isoformat() if log.next_retry_at else None,
        "sent_at": log.sent_at.isoformat() if log.sent_at else None, "error": log.error,
        "entity_type": log.entity_type, "entity_id": log.entity_id,
        "created_at": log.created_at.isoformat(),
    }


def _template_dict(t: SmsTemplate) -> dict:
    return {"id": str(t.pk), "code": t.code, "name": t.name, "body": t.body, "is_active": t.is_active}


PLATFORM = [IsAuthenticated, IsPlatformIntegrationsAdmin]


class CredentialListCreateView(APIView):
    permission_classes = PLATFORM

    def get(self, request):
        qs = IntegrationCredential.active_objects().filter(tenant=target_tenant(request))
        return success_response(data=[CredentialService.serialize(c) for c in qs])

    def post(self, request):
        try:
            cred = CredentialService.create(
                tenant=target_tenant(request), label=request.data.get("label"),
                secret=request.data.get("secret"), actor=request.user, request=request,
            )
        except CredentialError as exc:
            return _bad(str(exc))
        return success_response(
            data=CredentialService.serialize(cred), message="Credential saved.",
            status=status.HTTP_201_CREATED,
        )


class CredentialDetailView(APIView):
    permission_classes = PLATFORM

    def patch(self, request, pk):
        cred = get_object_or_404(IntegrationCredential.active_objects(), pk=pk, tenant=target_tenant(request))
        try:
            if request.data.get("secret"):
                CredentialService.rotate(
                    credential=cred, secret=request.data["secret"], actor=request.user, request=request
                )
            if request.data.get("label"):
                cred.label = str(request.data["label"]).strip()
                cred.save(update_fields=["label", "updated_at"])
        except CredentialError as exc:
            return _bad(str(exc))
        return success_response(data=CredentialService.serialize(cred))


def provider_or_404(qs, request, pk):
    return get_object_or_404(qs, pk=pk, tenant=target_tenant(request))


def credential_or_none(tenant, credential_id):
    pk = parse_uuid(credential_id)
    return IntegrationCredential.active_objects().filter(pk=pk, tenant=tenant).first() if pk else None


class SmsProviderListCreateView(APIView):
    permission_classes = PLATFORM

    def get(self, request):
        qs = SmsProvider.active_objects().filter(tenant=target_tenant(request))
        return success_response(data=[_provider_dict(p) for p in qs])

    def post(self, request):
        return _save_provider(request, SmsProvider(tenant=target_tenant(request), created_by=request.user))


class SmsProviderDetailView(APIView):
    permission_classes = PLATFORM

    def patch(self, request, pk):
        provider = provider_or_404(SmsProvider.active_objects(), request, pk)
        return _save_provider(request, provider)


def _save_provider(request, provider: SmsProvider):
    data, tenant = request.data, provider.tenant
    creating = provider._state.adding
    ptype = data.get("provider_type", provider.provider_type)
    if ptype not in PROVIDER_REGISTRY:
        return _bad(f"provider_type must be one of {', '.join(PROVIDER_REGISTRY)}.")
    if "branch_id" in data:
        branch = tenant_branch(tenant, data["branch_id"]) if data["branch_id"] else None
        if data["branch_id"] and branch is None:
            return _bad("Branch not found for this tenant.")
        provider.branch = branch
    if data.get("credential_id"):
        cred = credential_or_none(tenant, data["credential_id"])
        if cred is None:
            return _bad("Credential not found.")
        provider.credential = cred
    provider.provider_type = ptype
    for field in ("name", "sender_id", "is_active", "is_default", "config"):
        if field in data:
            setattr(provider, field, data[field])
    if not provider.name:
        return _bad("A name is required.")
    problems = PROVIDER_REGISTRY[ptype](config=provider.config, secret=None).validate_config()
    if problems and ptype != "MOCK":
        return _bad(problems[0])
    provider.updated_by = request.user
    provider.save()
    write_audit(
        action="create" if creating else "update", module=MODULE, entity=provider,
        user=request.user, request=request, branch=provider.branch,
        new_values={"name": provider.name, "provider_type": provider.provider_type,
                    "is_active": provider.is_active},  # never the config: it may carry endpoints
    )
    return success_response(
        data=_provider_dict(provider), status=status.HTTP_201_CREATED if creating else status.HTTP_200_OK
    )


class SmsTemplateListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("integrations.view")]

    def get(self, request):
        qs = SmsTemplate.active_objects().filter(tenant=_tenant(request))
        return success_response(data=[_template_dict(t) for t in qs])

    def post(self, request):
        if not request.user.has_permission("integrations.manage"):
            return _bad("Forbidden.", status.HTTP_403_FORBIDDEN)
        code, body = (request.data.get("code") or "").strip(), request.data.get("body") or ""
        if not code or not body:
            return _bad("code and body are required.")
        if SmsTemplate.active_objects().filter(tenant=_tenant(request), code=code).exists():
            return _bad("A template with this code already exists.")
        t = SmsTemplate.objects.create(
            tenant=_tenant(request), code=code, name=request.data.get("name") or code, body=body,
            created_by=request.user,
        )
        return success_response(data=_template_dict(t), status=status.HTTP_201_CREATED)


class SmsLogListView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("integrations.view")]

    def get(self, request):
        scope = get_branch_scope(request, permission="integrations.view")
        qs = SmsLog.objects.filter(tenant=_tenant(request), deleted_at__isnull=True)
        # Tenant-level (branch-less) logs are visible only to callers who can see every branch.
        qs = qs.filter(branch_id__in=list(scope.branch_ids)) if not scope.unscoped else qs
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        return success_response(data=[_log_dict(log) for log in qs[:200]])


class SmsSendView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("integrations.sms.send")]

    def post(self, request):
        branch = None
        if request.data.get("branch_id"):
            branch = accessible_branches(request.user, request=request).filter(
                pk=request.data["branch_id"]
            ).first()
            if branch is None or not has_branch_permission(request.user, "integrations.sms.send", branch):
                return _bad("You do not have access to this branch.", status.HTTP_403_FORBIDDEN)
        try:
            log = SmsService.send(
                tenant=_tenant(request), to=request.data.get("to"), branch=branch,
                template_code=request.data.get("template_code"), body=request.data.get("body"),
                context=request.data.get("context") or {}, user=request.user,
            )
        except SmsError as exc:
            return _bad(str(exc))
        return success_response(data=_log_dict(log), status=status.HTTP_201_CREATED)


class PlatformTenantBranchListView(APIView):
    """Branches of the managed tenant, for binding a provider to one branch (Platform Admin only)."""

    permission_classes = PLATFORM

    def get(self, request):
        from apps.settings_app.models import Branch

        qs = Branch.objects.filter(tenant=target_tenant(request), deleted_at__isnull=True).order_by("name")
        return success_response(data=[{"id": str(b.pk), "name": b.name, "code": b.code} for b in qs])
