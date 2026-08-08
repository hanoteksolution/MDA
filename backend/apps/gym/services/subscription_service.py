"""Gym membership plans + subscription lifecycle (STEP 15)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.gym.models import Member, MembershipPlan, MembershipSubscription
from core.tenancy import apply_tenant_scope, resolve_acting_tenant, stamp_tenant_id


class SubscriptionError(ValueError):
    pass


class PlanService:
    @staticmethod
    def list(*, search=None, is_active=None, user=None, request=None):
        qs = MembershipPlan.active_objects()
        qs = apply_tenant_scope(qs, user=user, request=request)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(code__icontains=search))
        return qs.order_by("sort_order", "name")

    @staticmethod
    def get(*, pk, user=None, request=None):
        return PlanService.list(user=user, request=request).get(pk=pk)

    @staticmethod
    def serialize(plan: MembershipPlan) -> dict:
        return {
            "id": str(plan.id),
            "code": plan.code,
            "name": plan.name,
            "description": plan.description or "",
            "duration_days": plan.duration_days,
            "price": float(plan.price),
            "visit_limit": plan.visit_limit,
            "freeze_allowed": plan.freeze_allowed,
            "max_freeze_days": plan.max_freeze_days,
            "is_active": plan.is_active,
            "sort_order": plan.sort_order,
        }

    @staticmethod
    def _prepare(data, *, for_create: bool, user=None, request=None) -> dict:
        prepared = {}
        for key in (
            "code",
            "name",
            "description",
            "duration_days",
            "price",
            "visit_limit",
            "freeze_allowed",
            "max_freeze_days",
            "is_active",
            "sort_order",
        ):
            if key not in data:
                continue
            value = data.get(key)
            if key == "code" and isinstance(value, str):
                prepared[key] = value.strip().lower().replace(" ", "_")
            elif key == "name" and isinstance(value, str):
                prepared[key] = value.strip()
            elif key == "visit_limit" and value in ("", None):
                prepared[key] = None
            elif key == "price":
                prepared[key] = Decimal(str(value if value is not None else 0))
            elif key in ("duration_days", "max_freeze_days", "sort_order") and value is not None:
                prepared[key] = int(value)
            elif key in ("freeze_allowed", "is_active") and value is not None:
                prepared[key] = bool(value)
            else:
                prepared[key] = value

        if for_create:
            if data.get("tenant_id"):
                prepared["tenant_id"] = data["tenant_id"]
            if data.get("tenant"):
                prepared["tenant"] = data["tenant"]
            prepared = stamp_tenant_id(prepared, user=user, request=request)
            if not prepared.get("code"):
                raise SubscriptionError("Plan code is required.")
            if not prepared.get("name"):
                raise SubscriptionError("Plan name is required.")
            if int(prepared.get("duration_days") or 0) <= 0:
                raise SubscriptionError("duration_days must be positive.")
            if "is_active" not in prepared:
                prepared["is_active"] = True
            if "sort_order" not in prepared:
                prepared["sort_order"] = 100
            if "freeze_allowed" not in prepared:
                prepared["freeze_allowed"] = True
            if "max_freeze_days" not in prepared:
                prepared["max_freeze_days"] = 30
            if "price" not in prepared:
                prepared["price"] = Decimal("0")
        return prepared

    @staticmethod
    @transaction.atomic
    def create(*, data, user=None, request=None) -> MembershipPlan:
        prepared = PlanService._prepare(data, for_create=True, user=user, request=request)
        tenant_id = prepared.get("tenant_id") or getattr(prepared.get("tenant"), "pk", None)
        if tenant_id and MembershipPlan.active_objects().filter(
            tenant_id=tenant_id, code=prepared["code"]
        ).exists():
            raise SubscriptionError(f"Plan code '{prepared['code']}' already exists.")
        return MembershipPlan.objects.create(**prepared, created_by=user)

    @staticmethod
    @transaction.atomic
    def update(*, plan: MembershipPlan, data, user=None, request=None) -> MembershipPlan:
        prepared = PlanService._prepare(data, for_create=False, user=user, request=request)
        prepared.pop("tenant_id", None)
        prepared.pop("tenant", None)
        if "code" in prepared and prepared["code"]:
            clash = (
                MembershipPlan.active_objects()
                .filter(tenant_id=plan.tenant_id, code=prepared["code"])
                .exclude(pk=plan.pk)
                .exists()
            )
            if clash:
                raise SubscriptionError(f"Plan code '{prepared['code']}' already exists.")
        for key, value in prepared.items():
            setattr(plan, key, value)
        plan.updated_by = user
        plan.save()
        return plan

    @staticmethod
    def soft_delete(*, plan: MembershipPlan, user=None):
        plan.soft_delete(user=user)
        return plan


class SubscriptionService:
    @staticmethod
    def list(
        *,
        member_id=None,
        status=None,
        search=None,
        user=None,
        request=None,
    ):
        qs = MembershipSubscription.active_objects().select_related(
            "member", "plan", "invoice"
        )
        qs = apply_tenant_scope(qs, user=user, request=request)
        if member_id:
            qs = qs.filter(member_id=member_id)
        if status:
            qs = qs.filter(status=status)
        if search:
            qs = qs.filter(
                Q(member__full_name__icontains=search)
                | Q(member__membership_number__icontains=search)
                | Q(plan__name__icontains=search)
            )
        return qs.order_by("-created_at")

    @staticmethod
    def get(*, pk, user=None, request=None):
        return SubscriptionService.list(user=user, request=request).get(pk=pk)

    @staticmethod
    def summary(*, user=None, request=None):
        qs = apply_tenant_scope(
            MembershipSubscription.active_objects(), user=user, request=request
        )
        by_status = {
            row["status"]: row["c"]
            for row in qs.values("status").annotate(c=Count("id"))
        }
        return {
            "total": qs.count(),
            "pending": by_status.get(MembershipSubscription.STATUS_PENDING, 0),
            "active": by_status.get(MembershipSubscription.STATUS_ACTIVE, 0),
            "frozen": by_status.get(MembershipSubscription.STATUS_FROZEN, 0),
            "expired": by_status.get(MembershipSubscription.STATUS_EXPIRED, 0),
            "cancelled": by_status.get(MembershipSubscription.STATUS_CANCELLED, 0),
        }

    @staticmethod
    def serialize(sub: MembershipSubscription) -> dict:
        return {
            "id": str(sub.id),
            "member_id": str(sub.member_id),
            "member_name": sub.member.full_name if sub.member_id else "",
            "membership_number": sub.member.membership_number if sub.member_id else "",
            "plan_id": str(sub.plan_id),
            "plan_name": sub.plan.name if sub.plan_id else "",
            "plan_code": sub.plan.code if sub.plan_id else "",
            "status": sub.status,
            "start_date": sub.start_date.isoformat() if sub.start_date else None,
            "end_date": sub.end_date.isoformat() if sub.end_date else None,
            "visits_allowed": sub.visits_allowed,
            "visits_used": sub.visits_used,
            "price_paid": float(sub.price_paid),
            "freeze_days_used": sub.freeze_days_used,
            "frozen_at": sub.frozen_at.isoformat() if sub.frozen_at else None,
            "cancelled_at": sub.cancelled_at.isoformat() if sub.cancelled_at else None,
            "activated_at": sub.activated_at.isoformat() if sub.activated_at else None,
            "invoice_id": str(sub.invoice_id) if sub.invoice_id else None,
            "invoice_number": sub.invoice.invoice_number if sub.invoice_id else None,
            "payment_reference": sub.payment_reference or "",
            "notes": sub.notes or "",
            "is_access_allowed": SubscriptionService.is_access_allowed(sub),
            "created_at": sub.created_at.isoformat() if sub.created_at else None,
        }

    @staticmethod
    def _compute_end(start: date, duration_days: int) -> date:
        return start + timedelta(days=int(duration_days))

    @staticmethod
    def expire_if_needed(sub: MembershipSubscription, *, today=None, user=None) -> MembershipSubscription:
        """Server-side expiry: active/frozen past end_date → expired."""
        today = today or timezone.localdate()
        if sub.status not in (
            MembershipSubscription.STATUS_ACTIVE,
            MembershipSubscription.STATUS_FROZEN,
        ):
            return sub
        if sub.end_date and sub.end_date < today:
            sub.status = MembershipSubscription.STATUS_EXPIRED
            sub.frozen_at = None
            sub.updated_by = user
            sub.save(update_fields=["status", "frozen_at", "updated_by", "updated_at"])
        return sub

    @staticmethod
    def is_access_allowed(sub: MembershipSubscription, *, today=None) -> bool:
        today = today or timezone.localdate()
        SubscriptionService.expire_if_needed(sub, today=today)
        sub.refresh_from_db()
        if sub.status != MembershipSubscription.STATUS_ACTIVE:
            return False
        if sub.end_date and sub.end_date < today:
            return False
        if sub.visits_allowed is not None and sub.visits_used >= sub.visits_allowed:
            return False
        return True

    @staticmethod
    @transaction.atomic
    def subscribe(
        *,
        member_id,
        plan_id,
        start_date=None,
        activate=False,
        payment_reference="",
        invoice_id=None,
        price_paid=None,
        notes="",
        user=None,
        request=None,
    ) -> MembershipSubscription:
        member = apply_tenant_scope(Member.active_objects(), user=user, request=request).get(
            pk=member_id
        )
        plan = apply_tenant_scope(
            MembershipPlan.active_objects().filter(is_active=True),
            user=user,
            request=request,
        ).get(pk=plan_id)

        if member.tenant_id and plan.tenant_id and member.tenant_id != plan.tenant_id:
            raise SubscriptionError("Member and plan must belong to the same tenant.")

        start = start_date
        if isinstance(start, str) and start:
            from django.utils.dateparse import parse_date

            start = parse_date(start)
        if activate and not start:
            start = timezone.localdate()

        end = None
        if start:
            end = SubscriptionService._compute_end(start, plan.duration_days)

        status = (
            MembershipSubscription.STATUS_ACTIVE
            if activate
            else MembershipSubscription.STATUS_PENDING
        )
        paid = Decimal(str(price_paid if price_paid is not None else plan.price))

        payload = stamp_tenant_id(
            {
                "member": member,
                "plan": plan,
                "status": status,
                "start_date": start,
                "end_date": end,
                "visits_allowed": plan.visit_limit,
                "visits_used": 0,
                "price_paid": paid,
                "payment_reference": payment_reference or "",
                "notes": notes or "",
                "tenant_id": member.tenant_id or plan.tenant_id,
            },
            user=user,
            request=request,
        )
        # stamp may add tenant_id; strip FK confusion
        sub = MembershipSubscription(
            member=member,
            plan=plan,
            status=status,
            start_date=start,
            end_date=end,
            visits_allowed=plan.visit_limit,
            visits_used=0,
            price_paid=paid,
            payment_reference=payment_reference or "",
            notes=notes or "",
            tenant_id=member.tenant_id or plan.tenant_id or payload.get("tenant_id"),
            created_by=user,
        )
        if invoice_id:
            from apps.sales.models import Invoice

            inv = apply_tenant_scope(Invoice.active_objects(), user=user, request=request).filter(
                pk=invoice_id
            ).first()
            if inv is None and member.tenant_id:
                inv = Invoice.active_objects().filter(
                    pk=invoice_id, tenant_id=member.tenant_id
                ).first()
            if inv is None:
                raise SubscriptionError("Invoice not found for this tenant.")
            sub.invoice = inv
        if activate:
            sub.activated_at = timezone.now()
        sub.save()
        return sub

    @staticmethod
    @transaction.atomic
    def activate(
        *,
        subscription: MembershipSubscription,
        start_date=None,
        payment_reference="",
        invoice_id=None,
        price_paid=None,
        user=None,
        request=None,
    ) -> MembershipSubscription:
        SubscriptionService.expire_if_needed(subscription, user=user)
        subscription.refresh_from_db()
        if subscription.status not in (
            MembershipSubscription.STATUS_PENDING,
            MembershipSubscription.STATUS_EXPIRED,
        ):
            if subscription.status == MembershipSubscription.STATUS_ACTIVE:
                return subscription
            raise SubscriptionError(
                f"Cannot activate subscription in status '{subscription.status}'."
            )

        start = start_date or subscription.start_date or timezone.localdate()
        if isinstance(start, str):
            from django.utils.dateparse import parse_date

            start = parse_date(start) or timezone.localdate()

        subscription.start_date = start
        subscription.end_date = SubscriptionService._compute_end(
            start, subscription.plan.duration_days
        )
        subscription.status = MembershipSubscription.STATUS_ACTIVE
        subscription.activated_at = timezone.now()
        if payment_reference:
            subscription.payment_reference = payment_reference
        if price_paid is not None:
            subscription.price_paid = Decimal(str(price_paid))
        if invoice_id:
            from apps.sales.models import Invoice

            inv = Invoice.active_objects().filter(pk=invoice_id).first()
            if inv is None:
                raise SubscriptionError("Invoice not found.")
            if (
                subscription.tenant_id
                and inv.tenant_id
                and inv.tenant_id != subscription.tenant_id
            ):
                raise SubscriptionError("Invoice tenant mismatch.")
            subscription.invoice = inv
        subscription.updated_by = user
        subscription.save()
        return subscription

    @staticmethod
    @transaction.atomic
    def freeze(
        *,
        subscription: MembershipSubscription,
        days: int | None = None,
        user=None,
    ) -> MembershipSubscription:
        SubscriptionService.expire_if_needed(subscription, user=user)
        subscription.refresh_from_db()
        if subscription.status != MembershipSubscription.STATUS_ACTIVE:
            raise SubscriptionError("Only active subscriptions can be frozen.")
        if not subscription.plan.freeze_allowed:
            raise SubscriptionError("This plan does not allow freezes.")
        remaining = int(subscription.plan.max_freeze_days) - int(
            subscription.freeze_days_used or 0
        )
        if remaining <= 0:
            raise SubscriptionError("No freeze days remaining.")
        # days reserved for future partial freeze; freeze starts today
        _ = days
        subscription.status = MembershipSubscription.STATUS_FROZEN
        subscription.frozen_at = timezone.localdate()
        subscription.updated_by = user
        subscription.save(
            update_fields=["status", "frozen_at", "updated_by", "updated_at"]
        )
        return subscription

    @staticmethod
    @transaction.atomic
    def unfreeze(*, subscription: MembershipSubscription, user=None) -> MembershipSubscription:
        if subscription.status != MembershipSubscription.STATUS_FROZEN:
            raise SubscriptionError("Subscription is not frozen.")
        today = timezone.localdate()
        frozen_at = subscription.frozen_at or today
        days = max(0, (today - frozen_at).days)
        remaining = int(subscription.plan.max_freeze_days) - int(
            subscription.freeze_days_used or 0
        )
        days = min(days, remaining) if remaining >= 0 else days
        subscription.freeze_days_used = int(subscription.freeze_days_used or 0) + days
        if subscription.end_date and days:
            subscription.end_date = subscription.end_date + timedelta(days=days)
        subscription.status = MembershipSubscription.STATUS_ACTIVE
        subscription.frozen_at = None
        subscription.updated_by = user
        subscription.save()
        SubscriptionService.expire_if_needed(subscription, user=user)
        subscription.refresh_from_db()
        return subscription

    @staticmethod
    @transaction.atomic
    def cancel(*, subscription: MembershipSubscription, user=None, notes="") -> MembershipSubscription:
        if subscription.status in (
            MembershipSubscription.STATUS_CANCELLED,
            MembershipSubscription.STATUS_EXPIRED,
        ):
            return subscription
        subscription.status = MembershipSubscription.STATUS_CANCELLED
        subscription.cancelled_at = timezone.now()
        subscription.frozen_at = None
        if notes:
            subscription.notes = (
                (subscription.notes + "\n" if subscription.notes else "") + notes
            )
        subscription.updated_by = user
        subscription.save()
        return subscription

    @staticmethod
    def expire_due(*, user=None, request=None, today=None) -> int:
        """Mark all due active/frozen subscriptions as expired. Returns count."""
        today = today or timezone.localdate()
        qs = apply_tenant_scope(
            MembershipSubscription.active_objects().filter(
                status__in=[
                    MembershipSubscription.STATUS_ACTIVE,
                    MembershipSubscription.STATUS_FROZEN,
                ],
                end_date__lt=today,
            ),
            user=user,
            request=request,
        )
        count = 0
        for sub in qs:
            SubscriptionService.expire_if_needed(sub, today=today, user=user)
            count += 1
        return count
