"""Tenant Billing & Subscription API.

Read-only views of the tenant's own subscription, plans and subscription invoices/payments, plus a
checkout that only *starts* a payment. Nothing here can mark a payment paid or a subscription
active: that happens only in ``SubscriptionBillingService.on_intent_settled`` after a verified
provider webhook settles the intent.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.platform.models import SubscriptionPayment, SubscriptionPlan, TenantSubscription
from apps.platform.services.subscription_billing_service import SubscriptionBillingError, SubscriptionBillingService
from core.responses.api_response import error_response, success_response
from core.tenancy import resolve_acting_tenant
from permissions.base import HasPermission

VIEW, PAY = "billing.subscription.view", "billing.subscription.pay"


def _tenant(request):
    return resolve_acting_tenant(request=request, user=request.user)


def _subscription(request):
    tenant = _tenant(request)
    if tenant is None:
        return None
    return TenantSubscription.active_objects().filter(tenant=tenant).select_related("plan", "tenant").first()


def payment_dict(p: SubscriptionPayment) -> dict:
    intent = p.intent if p.intent_id else None
    return {
        "id": str(p.pk), "reference": p.payment_reference, "kind": p.kind or "legacy",
        "plan_id": str(p.plan_id) if p.plan_id else None, "plan_name": p.plan.name if p.plan_id else None,
        "amount": str(p.amount), "currency": p.currency or SubscriptionBillingService.currency(),
        "status": p.status, "failure_reason": p.failure_reason,
        "invoice_number": p.invoice.invoice_number if p.invoice_id else None,
        "payment_reference": intent.provider_reference if intent else "",
        "payment_expires_at": intent.expires_at.isoformat() if intent and intent.expires_at else None,
        "confirmed_at": p.confirmed_at.isoformat() if p.confirmed_at else None,
        "created_at": p.created_at.isoformat(),
    }


class SubscriptionOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasPermission(VIEW)]

    def get(self, request):
        sub = _subscription(request)
        if sub is None:
            return success_response(data={"subscription": None, "plans": [], "payments": [], "online_payment": False})
        plans = []
        for plan in SubscriptionPlan.active_objects().filter(is_active=True).order_by("monthly_price"):
            problem = SubscriptionBillingService.plan_problem(sub, plan)
            plans.append({
                "id": str(plan.pk), "code": plan.code, "name": plan.name, "description": plan.description,
                "monthly_price": str(SubscriptionBillingService.amount_for(sub, plan)), "max_users": plan.max_users,
                "max_branches": plan.max_branches, "is_current": plan.pk == sub.plan_id,
                "action": "renew" if plan.pk == sub.plan_id else "change", "available": not problem, "reason": problem,
            })
        payments = SubscriptionPayment.active_objects().filter(subscription=sub).select_related("plan", "invoice", "intent")[:50]
        return success_response(data={
            "subscription": {
                "reference": sub.reference_code, "plan_id": str(sub.plan_id), "plan_name": sub.plan.name, "status": sub.status,
                "started_at": sub.started_at.isoformat() if sub.started_at else None,
                "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
                "next_billing_date": sub.expires_at.isoformat() if sub.expires_at else None,
                "days_until_expiry": sub.days_until_expiry, "grace_period_days": sub.grace_period_days,
                "billing_period_days": sub.billing_period_days, "is_usable": sub.is_usable,
                "last_paid_at": sub.last_paid_at.isoformat() if sub.last_paid_at else None,
                "monthly_fee": str(sub.effective_monthly_fee), "currency": SubscriptionBillingService.currency(),
            },
            "plans": plans,
            "payments": [payment_dict(p) for p in payments],
            "online_payment": SubscriptionBillingService.billing_provider() is not None,
            # Monthly periods only: plans carry a monthly price and no yearly price/discount exists.
            "billing_cycles": ["monthly"],
        })


class SubscriptionCheckoutView(APIView):
    permission_classes = [IsAuthenticated, HasPermission(PAY)]

    def post(self, request):
        tenant = _tenant(request)
        if tenant is None:
            return error_response(message="No workspace context.", status=status.HTTP_403_FORBIDDEN)
        key = request.data.get("idempotency_key") or request.headers.get("Idempotency-Key")
        try:
            payment, created = SubscriptionBillingService.checkout(
                tenant=tenant, plan_id=request.data.get("plan_id"), idempotency_key=key, user=request.user, request=request,
            )
        except SubscriptionBillingError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return error_response(message="Choose a plan.", status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=payment_dict(payment), status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class SubscriptionPaymentDetailView(APIView):
    """Polled while a payment is pending. Read-only by design."""

    permission_classes = [IsAuthenticated, HasPermission(VIEW)]

    def get(self, request, pk):
        sub = _subscription(request)
        if sub is None:
            return error_response(message="Not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(data=payment_dict(get_object_or_404(SubscriptionPayment.active_objects(), pk=pk, subscription=sub)))
