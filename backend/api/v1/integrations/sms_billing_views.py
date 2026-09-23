"""SMS reseller billing API.

Tenant side (``/api/v1/integrations/sms-billing/``): packages, balance, usage, purchases — never
provider configuration. Platform side (``/api/v1/platform/integrations/sms-billing/``): packages,
billing provider, tenant balances/ledgers and audited manual adjustments (global platform admin).
There is no endpoint that credits a purchase: only the verified webhook path does.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.audit.services.audit_write import write_audit
from apps.integrations.billing_guard import billing_provider_problem
from apps.integrations.models import (
    PaymentProviderConfig,
    SmsBillingSettings,
    SmsCreditEntry,
    SmsLog,
    SmsPackage,
    SmsPackagePurchase,
)
from apps.integrations.services.sms_credit_service import SmsCreditError, SmsCreditService, SmsPurchaseService
from apps.platform.models import Tenant
from core.branching import get_branch_scope
from core.responses.api_response import error_response, success_response
from core.tenancy import resolve_acting_tenant
from permissions.base import HasPermission

from .platform_access import parse_uuid, target_tenant
from .views import PLATFORM

MODULE = "integrations"
VIEW, PURCHASE = "integrations.sms.billing.view", "integrations.sms.billing.purchase"


def _bad(message, code=status.HTTP_400_BAD_REQUEST):
    return error_response(message=message, status=code)


def _iso(v):
    return v.isoformat() if v else None


def package_dict(p: SmsPackage) -> dict:
    return {
        "id": str(p.pk), "name": p.name, "code": p.code, "sms_quantity": p.sms_quantity,
        "price": str(p.price), "currency": p.currency, "validity_days": p.validity_days,
        "description": p.description, "is_active": p.is_active,
    }


def purchase_dict(p: SmsPackagePurchase) -> dict:
    # No provider id/config: tenants only see what they bought and its state.
    return {
        "id": str(p.pk), "package_id": str(p.package_id), "package_name": p.package_name,
        "sms_quantity": p.sms_quantity, "price": str(p.price), "currency": p.currency,
        "validity_days": p.validity_days, "status": p.status, "payment_reference": p.provider_reference,
        "failure_reason": p.failure_reason, "credited_at": _iso(p.credited_at), "created_at": p.created_at.isoformat(),
    }


def entry_dict(e: SmsCreditEntry) -> dict:
    return {
        "id": str(e.pk), "kind": e.kind, "units": e.units, "balance_after": e.balance_after,
        "purchase_id": str(e.purchase_id) if e.purchase_id else None,
        "sms_log_id": str(e.sms_log_id) if e.sms_log_id else None,
        "expires_at": _iso(e.lot.expires_at) if e.lot_id else None,
        "reason": e.reason, "created_at": e.created_at.isoformat(),
    }


def _tenant(request):
    return resolve_acting_tenant(request=request, user=request.user)


def _ledger(qs, request):
    """Branch-scoped users see message entries for their branches only; money entries are tenant-wide."""
    scope = get_branch_scope(request, permission=VIEW)
    if not scope.unscoped:
        qs = qs.filter(Q(sms_log__isnull=True) | Q(sms_log__branch_id__in=list(scope.branch_ids)))
    return qs.select_related("lot")


# ── tenant ──────────────────────────────────────────────────────────────────────

class TenantSmsPackageListView(APIView):
    permission_classes = [IsAuthenticated, HasPermission(VIEW)]

    def get(self, request):
        return success_response(data=[package_dict(p) for p in SmsPackage.active_objects().filter(is_active=True)])


class TenantSmsBillingSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission(VIEW)]

    def get(self, request):
        tenant = _tenant(request)
        if tenant is None:
            return _bad("No tenant context.", status.HTTP_403_FORBIDDEN)
        return success_response(data={**SmsCreditService.summary(tenant.pk),
                                      "payments_available": SmsPurchaseService.billing_provider() is not None})


class TenantSmsLedgerView(APIView):
    permission_classes = [IsAuthenticated, HasPermission(VIEW)]

    def get(self, request):
        qs = _ledger(SmsCreditEntry.objects.filter(tenant=_tenant(request)), request)
        if request.query_params.get("kind"):
            qs = qs.filter(kind=request.query_params["kind"])
        return success_response(data=[entry_dict(e) for e in qs[:200]])


class TenantSmsPurchaseListCreateView(APIView):
    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PURCHASE if self.request.method == "POST" else VIEW)()]

    def get(self, request):
        qs = SmsPackagePurchase.objects.filter(tenant=_tenant(request), deleted_at__isnull=True)
        return success_response(data=[purchase_dict(p) for p in qs[:100]])

    def post(self, request):
        tenant = _tenant(request)
        if tenant is None:
            return _bad("No tenant context.", status.HTTP_403_FORBIDDEN)
        if parse_uuid(request.data.get("package_id")) is None:
            return _bad("Choose a package.")
        key = request.data.get("idempotency_key") or request.headers.get("Idempotency-Key")
        try:
            purchase, created = SmsPurchaseService.create(
                tenant=tenant, package_id=request.data["package_id"], idempotency_key=key,
                user=request.user, request=request,
            )
        except SmsCreditError as exc:
            return _bad(str(exc))
        return success_response(data=purchase_dict(purchase), status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class TenantSmsPurchaseDetailView(APIView):
    """Polled by the frontend. Read-only: there is no client-side 'confirm payment'."""

    permission_classes = [IsAuthenticated, HasPermission(VIEW)]

    def get(self, request, pk):
        return success_response(data=purchase_dict(get_object_or_404(SmsPackagePurchase, pk=pk, tenant=_tenant(request))))


# ── platform ────────────────────────────────────────────────────────────────────

def _package_payload(data, package: SmsPackage):
    for field in ("name", "code", "description", "currency", "is_active"):
        if field in data:
            setattr(package, field, data[field] if field == "is_active" else str(data[field] or "").strip())
    try:
        if "sms_quantity" in data:
            package.sms_quantity = int(data["sms_quantity"])
        if "price" in data:
            package.price = Decimal(str(data["price"]))
        if "validity_days" in data:
            package.validity_days = int(data["validity_days"]) if data["validity_days"] not in (None, "") else None
    except (TypeError, ValueError, InvalidOperation):
        return "Quantity, price and validity must be numbers."
    package.currency = (package.currency or "USD").upper()[:3]
    if not package.name or not package.code:
        return "Name and code are required."
    if not package.sms_quantity or package.sms_quantity <= 0:
        return "SMS quantity must be greater than zero."
    if package.price is None or package.price < 0:
        return "Price cannot be negative."
    if package.validity_days is not None and package.validity_days <= 0:
        return "Validity must be a positive number of days, or empty for no expiry."
    clash = SmsPackage.active_objects().filter(code=package.code).exclude(pk=package.pk).exists()
    return "A package with this code already exists." if clash else ""


class PlatformSmsPackageListCreateView(APIView):
    permission_classes = PLATFORM

    def get(self, request):
        return success_response(data=[package_dict(p) for p in SmsPackage.active_objects()])

    def post(self, request):
        package = SmsPackage(created_by=request.user)
        problem = _package_payload(request.data, package)
        if problem:
            return _bad(problem)
        package.save()
        write_audit(action="create", module=MODULE, entity=package, user=request.user, request=request, new_values=package_dict(package))
        return success_response(data=package_dict(package), status=status.HTTP_201_CREATED)


class PlatformSmsPackageDetailView(APIView):
    permission_classes = PLATFORM

    def patch(self, request, pk):
        package = get_object_or_404(SmsPackage.active_objects(), pk=pk)
        before = package_dict(package)
        problem = _package_payload(request.data, package)
        if problem:
            return _bad(problem)
        package.updated_by = request.user
        package.save()
        write_audit(action="update", module=MODULE, entity=package, user=request.user, request=request,
                    old_values=before, new_values=package_dict(package))
        return success_response(data=package_dict(package))


class PlatformSmsBillingSettingsView(APIView):
    permission_classes = PLATFORM

    @staticmethod
    def _data(s):
        p = s.payment_provider
        return {"payment_provider_id": str(p.pk) if p else None, "payment_provider_name": p.name if p else None,
                "payment_provider_tenant_id": str(p.tenant_id) if p else None}

    def get(self, request):
        return success_response(data=self._data(SmsBillingSettings.load()))

    def put(self, request):
        s = SmsBillingSettings.load()
        pid = request.data.get("payment_provider_id")
        provider = None
        if pid:
            provider = PaymentProviderConfig.active_objects().filter(pk=parse_uuid(pid), is_active=True).first() if parse_uuid(pid) else None
            if provider is None:
                return _bad("Active payment provider not found.")
            problem = billing_provider_problem(provider)
            if problem:
                return _bad(problem)
        s.payment_provider, s.updated_by = provider, request.user
        s.save(update_fields=["payment_provider", "updated_by", "updated_at"])
        write_audit(action="update", module=MODULE, entity=s, user=request.user, request=request, new_values=self._data(s))
        return success_response(data=self._data(s))


class PlatformSmsBalanceListView(APIView):
    """Every tenant's balance, purchases and usage (platform overview)."""

    permission_classes = PLATFORM

    def get(self, request):
        now = timezone.now()
        rows = []
        for tenant in Tenant.objects.filter(deleted_at__isnull=True).order_by("name"):
            entries = SmsCreditEntry.objects.filter(tenant=tenant)
            rows.append({
                "tenant_id": str(tenant.pk), "tenant_name": tenant.name,
                "balance": SmsCreditService.balance(tenant.pk, now),
                "purchased": entries.filter(kind=SmsCreditEntry.KIND_PURCHASE).aggregate(s=Sum("units"))["s"] or 0,
                "used": SmsLog.objects.filter(tenant=tenant, credit_state=SmsLog.CREDIT_CHARGED).aggregate(s=Sum("credit_units"))["s"] or 0,
                "pending_purchases": SmsPackagePurchase.objects.filter(tenant=tenant, status=SmsPackagePurchase.STATUS_PENDING).count(),
                "review_purchases": SmsPackagePurchase.objects.filter(tenant=tenant, status=SmsPackagePurchase.STATUS_REVIEW).count(),
            })
        return success_response(data=rows)


class PlatformSmsTenantLedgerView(APIView):
    permission_classes = PLATFORM

    def get(self, request):
        tenant = target_tenant(request)
        return success_response(data={
            "summary": SmsCreditService.summary(tenant.pk),
            "entries": [entry_dict(e) for e in SmsCreditEntry.objects.filter(tenant=tenant).select_related("lot")[:200]],
            "purchases": [purchase_dict(p) for p in SmsPackagePurchase.objects.filter(tenant=tenant)[:100]],
        })


class PlatformSmsAdjustmentView(APIView):
    permission_classes = PLATFORM

    def post(self, request):
        tenant = target_tenant(request)
        units = request.data.get("units")
        if isinstance(units, str) and units.lstrip("-").isdigit():
            units = int(units)
        expires_at = None
        if request.data.get("expires_at"):
            try:
                expires_at = datetime.fromisoformat(str(request.data["expires_at"]))
            except ValueError:
                return _bad("expires_at must be an ISO date/time.")
            if timezone.is_naive(expires_at):
                expires_at = timezone.make_aware(expires_at)
        try:
            entry = SmsCreditService.adjust(
                tenant=tenant, units=units, reason=request.data.get("reason"), user=request.user,
                request=request, expires_at=expires_at,
            )
        except SmsCreditError as exc:
            return _bad(str(exc))
        return success_response(data=entry_dict(entry), status=status.HTTP_201_CREATED)
