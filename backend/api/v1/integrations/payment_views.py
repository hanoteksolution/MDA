"""Payment framework API — providers, intents, webhook intake, reconciliation.

Nothing here returns a secret or ciphertext (credentials are referenced by id only), and no
endpoint except the signed webhook can move an intent to ``succeeded`` — the "confirm" a
browser could call does not exist; clients poll the intent instead.

Providers, webhook events and reconciliation are platform infrastructure (global platform admin only,
explicit ``tenant_id``; mounted under ``/api/v1/platform/integrations/``). Intents stay tenant-scoped.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.audit.services.audit_write import write_audit
from apps.integrations.models import (
    PaymentIntent,
    PaymentProviderConfig,
    PaymentWebhookEvent,
    ReconciliationRecord,
)
from apps.integrations.providers.payment_base import SIGNATURE_HEADER, TIMESTAMP_HEADER
from apps.integrations.providers.registry import PAYMENT_PROVIDER_REGISTRY
from apps.integrations.services import PaymentError, PaymentService, ReconciliationService
from apps.integrations.services.payment_service import MAX_BODY_BYTES
from api.v1.integrations.platform_access import parse_uuid, target_tenant, tenant_branch
from api.v1.integrations.views import PLATFORM, credential_or_none, provider_or_404
from apps.sales.models import Invoice
from core.branching import accessible_branches, get_branch_scope, has_branch_permission
from core.responses.api_response import error_response, success_response
from core.tenancy import resolve_acting_tenant
from permissions.base import HasPermission

MODULE = "integrations"


def _tenant(request):
    return resolve_acting_tenant(request=request, user=request.user)


def _bad(message, code=status.HTTP_400_BAD_REQUEST):
    return error_response(message=message, status=code)


def _iso(value):
    return value.isoformat() if value else None


def _provider_dict(p: PaymentProviderConfig) -> dict:
    return {
        "id": str(p.pk), "name": p.name, "provider_type": p.provider_type,
        "branch_id": str(p.branch_id) if p.branch_id else None,
        "credential_id": str(p.credential_id) if p.credential_id else None,
        "webhook_credential_id": str(p.webhook_credential_id) if p.webhook_credential_id else None,
        "config": p.config, "is_active": p.is_active,
        "webhook_path": f"/api/v1/integrations/payments/webhooks/{p.pk}/",
    }


def _intent_dict(i: PaymentIntent) -> dict:
    return {
        "id": str(i.pk), "invoice_id": str(i.invoice_id), "branch_id": str(i.branch_id),
        "provider_id": str(i.provider_id), "idempotency_key": i.idempotency_key,
        "amount": str(i.amount), "currency": i.currency, "method": i.method, "status": i.status,
        "provider_reference": i.provider_reference, "expires_at": _iso(i.expires_at),
        "failure_reason": i.failure_reason, "payment_id": str(i.payment_id) if i.payment_id else None,
        "settled_at": _iso(i.settled_at), "created_at": i.created_at.isoformat(),
    }


def _event_dict(e: PaymentWebhookEvent) -> dict:
    # No raw body and no signature: the body is provider-controlled text, the signature is a credential-derived value.
    return {
        "id": str(e.pk), "provider_id": str(e.provider_id), "event_id": e.event_id,
        "signature_valid": e.signature_valid, "status": e.status, "reason": e.reason,
        "intent_id": str(e.intent_id) if e.intent_id else None, "received_at": e.created_at.isoformat(),
        "processed_at": _iso(e.processed_at),
    }


def _record_dict(r: ReconciliationRecord) -> dict:
    money = lambda v: None if v is None else str(v)  # noqa: E731
    return {
        "id": str(r.pk), "branch_id": str(r.branch_id), "provider_id": str(r.provider_id),
        "intent_id": str(r.intent_id), "kind": r.kind, "status": r.status,
        "provider_status": r.provider_status, "provider_amount": money(r.provider_amount),
        "ledger_status": r.ledger_status, "ledger_amount": money(r.ledger_amount), "detail": r.detail,
        "resolved_at": _iso(r.resolved_at), "resolution_note": r.resolution_note,
        "created_at": r.created_at.isoformat(),
    }


def _scoped(qs, request, permission):
    """Restrict to the caller's branches. Every payment row has a branch, so no NULL case."""
    scope = get_branch_scope(request, permission=permission)
    return qs if scope.unscoped else qs.filter(branch_id__in=list(scope.branch_ids))


class PaymentProviderListCreateView(APIView):
    permission_classes = PLATFORM

    def get(self, request):
        qs = PaymentProviderConfig.active_objects().filter(tenant=target_tenant(request))
        return success_response(data=[_provider_dict(p) for p in qs])

    def post(self, request):
        return _save_provider(request, PaymentProviderConfig(tenant=target_tenant(request), created_by=request.user))


class PaymentProviderDetailView(APIView):
    permission_classes = PLATFORM

    def patch(self, request, pk):
        provider = provider_or_404(PaymentProviderConfig.active_objects(), request, pk)
        return _save_provider(request, provider)


def _save_provider(request, provider: PaymentProviderConfig):
    data, tenant = request.data, provider.tenant
    creating = provider._state.adding
    ptype = data.get("provider_type", provider.provider_type)
    if ptype not in PAYMENT_PROVIDER_REGISTRY:
        return _bad(f"provider_type must be one of {', '.join(PAYMENT_PROVIDER_REGISTRY)}.")
    if "branch_id" in data:
        branch = tenant_branch(tenant, data["branch_id"]) if data["branch_id"] else None
        if data["branch_id"] and branch is None:
            return _bad("Branch not found for this tenant.")
        provider.branch = branch
    for field, attr in (("credential_id", "credential"), ("webhook_credential_id", "webhook_credential")):
        if data.get(field):
            cred = credential_or_none(tenant, data[field])
            if cred is None:
                return _bad("Credential not found.")
            setattr(provider, attr, cred)
    provider.provider_type = ptype
    for field in ("name", "is_active", "config"):
        if field in data:
            setattr(provider, field, data[field])
    if not provider.name:
        return _bad("A name is required.")
    provider.updated_by = request.user
    provider.save()
    write_audit(
        action="create" if creating else "update", module=MODULE, entity=provider, user=request.user,
        request=request, branch=provider.branch,
        new_values={"name": provider.name, "provider_type": provider.provider_type, "is_active": provider.is_active},
    )
    return success_response(
        data=_provider_dict(provider), status=status.HTTP_201_CREATED if creating else status.HTTP_200_OK
    )


class PaymentIntentListCreateView(APIView):
    def get_permissions(self):
        perm = "integrations.payments.collect" if self.request.method == "POST" else "integrations.payments.view"
        return [IsAuthenticated(), HasPermission(perm)()]

    def get(self, request):
        qs = PaymentIntent.objects.filter(tenant=_tenant(request), deleted_at__isnull=True)
        qs = _scoped(qs, request, "integrations.payments.view")
        if request.query_params.get("invoice_id"):
            qs = qs.filter(invoice_id=request.query_params["invoice_id"])
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        return success_response(data=[_intent_dict(i) for i in qs[:200]])

    def post(self, request):
        tenant = _tenant(request)
        invoice = Invoice.objects.select_related("branch").filter(
            pk=request.data.get("invoice_id"), tenant=tenant, deleted_at__isnull=True
        ).first() if request.data.get("invoice_id") else None
        branch = (
            accessible_branches(request.user, request=request).filter(pk=invoice.branch_id).first()
            if invoice else None
        )
        # Someone else's branch looks exactly like a missing invoice.
        if branch is None or not has_branch_permission(request.user, "integrations.payments.collect", branch):
            return _bad("Invoice not found.", status.HTTP_404_NOT_FOUND)
        key = request.data.get("idempotency_key") or request.headers.get("Idempotency-Key")
        try:
            intent, created = PaymentService.create_intent(
                tenant=tenant, invoice=invoice, idempotency_key=key, amount=request.data.get("amount"),
                provider_id=request.data.get("provider_id"), method=request.data.get("method") or "mobile",
                user=request.user, request=request,
            )
        except PaymentError as exc:
            return _bad(str(exc))
        return success_response(
            data=_intent_dict(intent), status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class PaymentIntentDetailView(APIView):
    """Polled by the frontend. Read-only by design: there is no client-side 'confirm'."""

    permission_classes = [IsAuthenticated, HasPermission("integrations.payments.view")]

    def get(self, request, pk):
        qs = _scoped(PaymentIntent.objects.filter(tenant=_tenant(request)), request, "integrations.payments.view")
        return success_response(data=_intent_dict(get_object_or_404(qs, pk=pk)))


class PaymentWebhookEventListView(APIView):
    permission_classes = PLATFORM

    def get(self, request):
        qs = PaymentWebhookEvent.objects.filter(tenant=target_tenant(request), deleted_at__isnull=True)
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        return success_response(data=[_event_dict(e) for e in qs[:200]])


class PaymentWebhookView(APIView):
    """Public, unauthenticated by design: authenticity comes from the HMAC signature, and the
    unguessable provider id selects the tenant. Replies leak nothing about *why* a call failed."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request, provider_id):
        provider = PaymentProviderConfig.active_objects().filter(pk=provider_id, is_active=True).first()
        if provider is None:
            return error_response(message="Not found.", status=status.HTTP_404_NOT_FOUND)
        raw = request.body
        if len(raw) > MAX_BODY_BYTES:
            return error_response(message="Payload too large.", status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        event = PaymentService.receive_webhook(
            provider=provider, raw_body=raw,
            signature=request.headers.get(SIGNATURE_HEADER, ""), timestamp=request.headers.get(TIMESTAMP_HEADER, ""),
        )
        if event.status == PaymentWebhookEvent.STATUS_REJECTED:
            return error_response(message="Rejected.", status=status.HTTP_401_UNAUTHORIZED)
        if event.status == PaymentWebhookEvent.STATUS_INVALID:
            return error_response(message="Invalid payload.", status=status.HTTP_400_BAD_REQUEST)
        if event.status == PaymentWebhookEvent.STATUS_ERROR:  # non-2xx makes the provider retry
            return error_response(message="Temporary failure.", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return success_response(data={"received": True})


class ReconciliationRunView(APIView):
    permission_classes = PLATFORM

    def post(self, request):
        tenant = target_tenant(request)
        provider = None
        if request.data.get("provider_id"):
            pk = parse_uuid(request.data["provider_id"])
            provider = PaymentProviderConfig.active_objects().filter(pk=pk, tenant=tenant).first() if pk else None
            if provider is None:
                return _bad("Payment provider not found.", status.HTTP_404_NOT_FOUND)
        summary = ReconciliationService.run(tenant=tenant, provider=provider, branch_ids=None)
        write_audit(
            action="create", module=MODULE, entity_type="PaymentReconciliationRun", entity_id=None,
            user=request.user, request=request,
            new_values={"tenant_id": str(tenant.pk), "checked": summary["checked"], "mismatches": summary["mismatches"]},
        )
        return success_response(data=summary)


class ReconciliationRecordListView(APIView):
    permission_classes = PLATFORM

    def get(self, request):
        qs = ReconciliationRecord.objects.filter(tenant=target_tenant(request), deleted_at__isnull=True)
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        return success_response(data=[_record_dict(r) for r in qs[:200]])


class ReconciliationResolveView(APIView):
    permission_classes = PLATFORM

    def post(self, request, pk):
        record = get_object_or_404(ReconciliationRecord.objects.filter(tenant=target_tenant(request)), pk=pk)
        try:
            ReconciliationService.resolve(
                record=record, user=request.user, note=request.data.get("note"), request=request
            )
        except PaymentError as exc:
            return _bad(str(exc))
        return success_response(data=_record_dict(record))
