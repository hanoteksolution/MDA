"""Gym membership checkout via central Invoice + Payment (STEP 20)."""

from __future__ import annotations

from decimal import Decimal
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.customers.models import Customer
from apps.gym.models import Member, MembershipPlan, MembershipSubscription
from apps.gym.services.subscription_service import SubscriptionService
from apps.products.models import Category, Product, Unit
from apps.sales.models import Invoice, Payment
from apps.sales.services.sales_service import InvoiceService, _resolve_branch
from apps.settings_app.models import Branch
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class GymPaymentError(ValueError):
    pass


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.0001"))


class GymPaymentService:
    @staticmethod
    def _resolve_member(*, member_id, user=None, request=None) -> Member:
        member = (
            apply_tenant_scope(Member.active_objects(), user=user, request=request)
            .select_related("customer", "branch")
            .filter(pk=member_id)
            .first()
        )
        if member is None:
            raise GymPaymentError("Member not found.")
        return member

    @staticmethod
    def _resolve_plan(*, plan_id, user=None, request=None) -> MembershipPlan:
        plan = (
            apply_tenant_scope(
                MembershipPlan.active_objects().filter(is_active=True),
                user=user,
                request=request,
            )
            .filter(pk=plan_id)
            .first()
        )
        if plan is None:
            raise GymPaymentError("Membership plan not found.")
        return plan

    @staticmethod
    def _resolve_branch(*, branch_id, member: Member, user=None) -> Branch:
        branch = _resolve_branch(branch_id or member.branch_id, user=user)
        if branch is None:
            raise GymPaymentError("Branch is required for checkout.")
        if member.tenant_id and branch.tenant_id and member.tenant_id != branch.tenant_id:
            raise GymPaymentError("Member and branch tenant mismatch.")
        return branch

    @staticmethod
    @transaction.atomic
    def ensure_customer_for_member(*, member: Member, branch: Branch, user=None) -> Customer:
        if member.customer_id:
            return member.customer
        code_base = (member.membership_number or "MEM").replace(" ", "-")[:40]
        code = f"GYM-{code_base}"
        n = 0
        while Customer.active_objects().filter(
            tenant_id=member.tenant_id, customer_code=code
        ).exists():
            n += 1
            code = f"GYM-{code_base}-{n}"
        customer = Customer.objects.create(
            customer_code=code,
            full_name=member.full_name,
            email=member.email or "",
            phone=member.phone or "",
            address=member.address or "",
            customer_type="retail",
            branch=branch,
            tenant_id=member.tenant_id,
            created_by=user,
        )
        member.customer = customer
        member.updated_by = user
        member.save(update_fields=["customer", "updated_by", "updated_at"])
        return customer

    @staticmethod
    @transaction.atomic
    def ensure_plan_product(*, plan: MembershipPlan, user=None) -> Product:
        sku = f"gym-plan-{plan.code}"[:100]
        existing = Product.active_objects().filter(tenant_id=plan.tenant_id, sku=sku).first()
        if existing:
            if existing.selling_price != plan.price:
                existing.selling_price = plan.price
                existing.name = plan.name
                existing.updated_by = user
                existing.save(update_fields=["selling_price", "name", "updated_by", "updated_at"])
            return existing

        category = Category.active_objects().filter(
            tenant_id=plan.tenant_id, name__iexact="Gym Services"
        ).first()
        if category is None:
            category = Category.objects.create(
                name="Gym Services",
                description="Membership and gym service lines",
                tenant_id=plan.tenant_id,
                created_by=user,
            )

        unit = Unit.active_objects().filter(
            tenant_id=plan.tenant_id, abbreviation__iexact="svc"
        ).first()
        if unit is None:
            unit = Unit.objects.create(
                name="Service",
                abbreviation="svc",
                tenant_id=plan.tenant_id,
                created_by=user,
            )

        return Product.objects.create(
            sku=sku,
            name=plan.name,
            category=category,
            unit=unit,
            cost_price=Decimal("0"),
            selling_price=plan.price,
            minimum_stock=0,
            description=f"Gym membership: {plan.name} ({plan.duration_days} days)",
            tenant_id=plan.tenant_id,
            created_by=user,
        )

    @staticmethod
    def _normalize_tenders(*, data, total_amount: Decimal):
        payment_method = (data.get("payment_method") or "cash").strip().lower()
        payment_reference = (data.get("payment_reference") or "").strip()
        raw_payments = data.get("payments")

        if raw_payments:
            tender_lines = []
            for row in raw_payments:
                method = (row.get("method") or "cash").strip().lower()
                amount = _money(row.get("amount") or 0)
                if amount <= 0 and method != Payment.METHOD_ON_ACCOUNT:
                    continue
                tender_lines.append(
                    {
                        "method": method,
                        "amount": amount,
                        "reference": (row.get("reference") or "").strip(),
                    }
                )
            if not tender_lines:
                raise GymPaymentError("Split payment requires at least one positive tender.")
            paid_sum = sum((t["amount"] for t in tender_lines), Decimal("0"))
            methods = {t["method"] for t in tender_lines}
            if methods == {Payment.METHOD_ON_ACCOUNT}:
                payment_method = Payment.METHOD_ON_ACCOUNT
            elif len(methods) > 1:
                payment_method = "split"
            else:
                payment_method = next(iter(methods))
            if payment_method != Payment.METHOD_ON_ACCOUNT and paid_sum + Decimal("0.01") < total_amount:
                raise GymPaymentError(
                    f"Tenders ({paid_sum}) are less than total ({total_amount})."
                )
            if not payment_reference and tender_lines[0].get("reference"):
                payment_reference = tender_lines[0]["reference"]
            return payment_method, payment_reference, tender_lines

        if payment_method == Payment.METHOD_ON_ACCOUNT:
            amount = Decimal("0")
        else:
            amount = total_amount
        return payment_method, payment_reference, [
            {
                "method": payment_method,
                "amount": amount,
                "reference": payment_reference,
            }
        ]

    @staticmethod
    def serialize_checkout(*, subscription, invoice, idempotent_replay=False) -> dict:
        payments = [
            {
                "id": str(p.id),
                "method": p.method,
                "amount": float(p.amount),
                "reference": p.reference or "",
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
            }
            for p in invoice.payments.filter(deleted_at__isnull=True).order_by("paid_at")
        ]
        primary_ref = payments[0]["reference"] if payments else subscription.payment_reference
        return {
            "subscription": SubscriptionService.serialize(subscription),
            "invoice": {
                "id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "status": invoice.status,
                "total_amount": float(invoice.total_amount),
                "amount_paid": float(invoice.amount_paid),
            },
            "payments": payments,
            "payment_reference": primary_ref or "",
            "idempotent_replay": idempotent_replay,
        }

    @staticmethod
    @transaction.atomic
    def checkout_membership(*, data, user=None, request=None) -> dict:
        member_id = data.get("member_id")
        plan_id = data.get("plan_id")
        if not member_id or not plan_id:
            raise GymPaymentError("member_id and plan_id are required.")

        idempotency_key = (data.get("idempotency_key") or "").strip() or None
        if idempotency_key:
            existing_invoice = (
                Invoice.active_objects()
                .filter(idempotency_key=idempotency_key, deleted_at__isnull=True)
                .prefetch_related("payments", "gym_subscriptions")
                .first()
            )
            if existing_invoice is not None:
                sub = existing_invoice.gym_subscriptions.filter(deleted_at__isnull=True).first()
                if sub is not None:
                    from apps.finance.services.posting_service import AccountingPostingService

                    AccountingPostingService.post_gym_membership(
                        invoice=existing_invoice, user=user
                    )
                    return GymPaymentService.serialize_checkout(
                        subscription=sub,
                        invoice=existing_invoice,
                        idempotent_replay=True,
                    )

        member = GymPaymentService._resolve_member(
            member_id=member_id, user=user, request=request
        )
        plan = GymPaymentService._resolve_plan(plan_id=plan_id, user=user, request=request)
        if member.tenant_id and plan.tenant_id and member.tenant_id != plan.tenant_id:
            raise GymPaymentError("Member and plan must belong to the same tenant.")

        branch = GymPaymentService._resolve_branch(
            branch_id=data.get("branch_id"), member=member, user=user
        )
        customer = GymPaymentService.ensure_customer_for_member(
            member=member, branch=branch, user=user
        )
        product = GymPaymentService.ensure_plan_product(plan=plan, user=user)
        total_amount = _money(data.get("price_paid") if data.get("price_paid") is not None else plan.price)

        payment_method, payment_reference, tender_lines = GymPaymentService._normalize_tenders(
            data=data, total_amount=total_amount
        )
        if payment_method == Payment.METHOD_ON_ACCOUNT and not customer:
            raise GymPaymentError("A registered customer is required for on-account sales.")

        is_on_account = payment_method == Payment.METHOD_ON_ACCOUNT
        invoice_status = Invoice.STATUS_SENT if is_on_account else Invoice.STATUS_PAID
        if is_on_account:
            amount_paid = Decimal("0")
        elif payment_method == "split":
            amount_paid = min(
                total_amount,
                sum(
                    (t["amount"] for t in tender_lines if t["method"] != Payment.METHOD_ON_ACCOUNT),
                    Decimal("0"),
                ),
            )
        else:
            amount_paid = total_amount

        payment_note = f"Payment: {payment_method} | Gym membership: {plan.name}"
        if payment_reference:
            payment_note += f" | Ref: {payment_reference}"
        notes = (data.get("notes") or "").strip()
        if notes:
            notes = f"{notes}\n{payment_note}"
        else:
            notes = payment_note

        invoice_data = stamp_tenant_id(
            {
                "customer_id": str(customer.id),
                "branch_id": str(branch.id),
                "status": invoice_status,
                "issue_date": timezone.localdate(),
                "due_date": timezone.localdate() + timedelta(days=30) if is_on_account else None,
                "discount_amount": Decimal("0"),
                "amount_paid": amount_paid,
                "notes": notes,
                "served_by_user": user,
            },
            user=user,
            request=request,
        )
        if idempotency_key:
            invoice_data["idempotency_key"] = idempotency_key

        invoice = InvoiceService.create(
            data=invoice_data,
            items=[
                {
                    "product_id": str(product.id),
                    "quantity": Decimal("1"),
                    "unit_price": total_amount,
                }
            ],
            user=user,
        )
        invoice.total_amount = total_amount
        invoice.subtotal = total_amount
        invoice.save(update_fields=["total_amount", "subtotal", "updated_at"])

        invoice.payments.all().delete()
        for tender in tender_lines:
            method = tender["method"]
            if method not in dict(Payment.METHOD_CHOICES):
                method = Payment.METHOD_OTHER
            Payment.objects.create(
                invoice=invoice,
                branch=branch,
                method=method,
                amount=tender["amount"],
                reference=tender.get("reference") or payment_reference or "",
                tenant_id=invoice.tenant_id,
                created_by=user,
            )

        activate = not is_on_account and bool(data.get("activate_on_pay", True))
        sub = SubscriptionService.subscribe(
            member_id=member.id,
            plan_id=plan.id,
            activate=activate,
            payment_reference=payment_reference,
            invoice_id=invoice.id,
            price_paid=total_amount,
            notes=data.get("subscription_notes") or data.get("notes") or "",
            user=user,
            request=request,
        )

        from apps.finance.services.posting_service import AccountingPostingService

        AccountingPostingService.post_gym_membership(
            invoice=invoice,
            user=user,
            payment_method=payment_method,
            tender_lines=[
                {
                    "method": t["method"],
                    "amount": str(t["amount"]),
                    "reference": t.get("reference") or "",
                }
                for t in tender_lines
            ],
        )

        return GymPaymentService.serialize_checkout(
            subscription=sub, invoice=invoice, idempotent_replay=False
        )

    @staticmethod
    @transaction.atomic
    def pay_pending_subscription(*, subscription_id, data, user=None, request=None) -> dict:
        sub = (
            SubscriptionService.list(user=user, request=request)
            .select_related("invoice", "member", "plan")
            .filter(pk=subscription_id)
            .first()
        )
        if sub is None:
            raise GymPaymentError("Subscription not found.")
        if sub.status != MembershipSubscription.STATUS_PENDING:
            raise GymPaymentError("Only pending subscriptions can be paid via this endpoint.")

        total_amount = _money(
            data.get("amount_paid") if data.get("amount_paid") is not None else sub.price_paid or sub.plan.price
        )
        payment_method, payment_reference, tender_lines = GymPaymentService._normalize_tenders(
            data=data, total_amount=total_amount
        )
        is_on_account = payment_method == Payment.METHOD_ON_ACCOUNT
        if is_on_account:
            raise GymPaymentError("Use checkout with on_account for unpaid memberships.")

        invoice = sub.invoice
        if invoice is None:
            member = sub.member
            branch = GymPaymentService._resolve_branch(
                branch_id=data.get("branch_id"), member=member, user=user
            )
            customer = GymPaymentService.ensure_customer_for_member(
                member=member, branch=branch, user=user
            )
            product = GymPaymentService.ensure_plan_product(plan=sub.plan, user=user)
            payment_note = f"Payment: {payment_method} | Gym membership: {sub.plan.name}"
            if payment_reference:
                payment_note += f" | Ref: {payment_reference}"
            invoice = InvoiceService.create(
                data=stamp_tenant_id(
                    {
                        "customer_id": str(customer.id),
                        "branch_id": str(branch.id),
                        "status": Invoice.STATUS_PAID,
                        "issue_date": timezone.localdate(),
                        "amount_paid": total_amount,
                        "notes": payment_note,
                        "served_by_user": user,
                    },
                    user=user,
                    request=request,
                ),
                items=[
                    {
                        "product_id": str(product.id),
                        "quantity": Decimal("1"),
                        "unit_price": total_amount,
                    }
                ],
                user=user,
            )
            invoice.total_amount = total_amount
            invoice.subtotal = total_amount
            invoice.save(update_fields=["total_amount", "subtotal", "updated_at"])
            sub.invoice = invoice
            sub.save(update_fields=["invoice", "updated_at"])

        invoice.status = Invoice.STATUS_PAID
        invoice.amount_paid = total_amount
        invoice.notes = (invoice.notes or "") + f"\nPaid: {payment_method}"
        invoice.save(update_fields=["status", "amount_paid", "notes", "updated_at"])

        invoice.payments.all().delete()
        branch = invoice.branch
        for tender in tender_lines:
            method = tender["method"]
            if method not in dict(Payment.METHOD_CHOICES):
                method = Payment.METHOD_OTHER
            Payment.objects.create(
                invoice=invoice,
                branch=branch,
                method=method,
                amount=tender["amount"],
                reference=tender.get("reference") or payment_reference or "",
                tenant_id=invoice.tenant_id,
                created_by=user,
            )

        sub = SubscriptionService.activate(
            subscription=sub,
            payment_reference=payment_reference,
            invoice_id=invoice.id,
            price_paid=total_amount,
            user=user,
            request=request,
        )

        from apps.finance.services.posting_service import AccountingPostingService

        AccountingPostingService.post_gym_membership(
            invoice=invoice,
            user=user,
            payment_method=payment_method,
            tender_lines=[
                {
                    "method": t["method"],
                    "amount": str(t["amount"]),
                    "reference": t.get("reference") or "",
                }
                for t in tender_lines
            ],
        )

        return GymPaymentService.serialize_checkout(subscription=sub, invoice=invoice)

    @staticmethod
    @transaction.atomic
    def ensure_pt_product(*, tenant_id, user=None) -> Product:
        sku = "gym-pt-session"
        existing = Product.active_objects().filter(tenant_id=tenant_id, sku=sku).first()
        if existing:
            return existing

        category = Category.active_objects().filter(
            tenant_id=tenant_id, name__iexact="Gym Services"
        ).first()
        if category is None:
            category = Category.objects.create(
                name="Gym Services",
                description="Membership and gym service lines",
                tenant_id=tenant_id,
                created_by=user,
            )

        unit = Unit.active_objects().filter(
            tenant_id=tenant_id, abbreviation__iexact="svc"
        ).first()
        if unit is None:
            unit = Unit.objects.create(
                name="Service",
                abbreviation="svc",
                tenant_id=tenant_id,
                created_by=user,
            )

        return Product.objects.create(
            sku=sku,
            name="Personal Training Session",
            category=category,
            unit=unit,
            cost_price=Decimal("0"),
            selling_price=Decimal("0"),
            minimum_stock=0,
            description="Billable personal training session",
            tenant_id=tenant_id,
            created_by=user,
        )

    @staticmethod
    def _pt_amount(*, session, data) -> Decimal:
        if data.get("amount") is not None and str(data.get("amount")).strip() != "":
            return _money(data.get("amount"))
        hours = Decimal(str(session.duration_minutes or 60)) / Decimal("60")
        rate = _money(getattr(session.trainer, "hourly_rate", 0) or 0)
        return _money(hours * rate)

    @staticmethod
    def serialize_pt_checkout(*, session, invoice, idempotent_replay=False) -> dict:
        from apps.gym.services.trainer_service import PTSessionService

        payments = [
            {
                "id": str(p.id),
                "method": p.method,
                "amount": float(p.amount),
                "reference": p.reference or "",
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
            }
            for p in invoice.payments.filter(deleted_at__isnull=True).order_by("paid_at")
        ]
        return {
            "session": PTSessionService.serialize(session),
            "invoice": {
                "id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "status": invoice.status,
                "total_amount": float(invoice.total_amount),
                "amount_paid": float(invoice.amount_paid),
            },
            "payments": payments,
            "payment_reference": (
                payments[0]["reference"] if payments else session.payment_reference or ""
            ),
            "idempotent_replay": idempotent_replay,
        }

    @staticmethod
    @transaction.atomic
    def checkout_pt_session(*, session_id, data, user=None, request=None) -> dict:
        from apps.gym.models import PersonalTrainingSession
        from apps.gym.services.trainer_service import PTSessionService, TrainerError

        qs = PTSessionService.list(user=user, request=request).select_related(
            "member", "trainer", "member__customer", "member__branch", "invoice"
        )
        session = qs.filter(pk=session_id).first()
        if session is None:
            raise GymPaymentError("PT session not found.")

        idempotency_key = (data.get("idempotency_key") or "").strip() or None
        if session.invoice_id and session.status == PersonalTrainingSession.STATUS_COMPLETED:
            from apps.finance.services.posting_service import AccountingPostingService

            AccountingPostingService.post_gym_service(
                invoice=session.invoice, user=user
            )
            return GymPaymentService.serialize_pt_checkout(
                session=session, invoice=session.invoice, idempotent_replay=True
            )
        if idempotency_key:
            existing_invoice = (
                Invoice.active_objects()
                .filter(idempotency_key=idempotency_key, deleted_at__isnull=True)
                .prefetch_related("payments", "gym_pt_sessions")
                .first()
            )
            if existing_invoice is not None:
                linked = existing_invoice.gym_pt_sessions.filter(
                    deleted_at__isnull=True
                ).first()
                if linked is not None:
                    from apps.finance.services.posting_service import AccountingPostingService

                    AccountingPostingService.post_gym_service(
                        invoice=existing_invoice, user=user
                    )
                    return GymPaymentService.serialize_pt_checkout(
                        session=linked,
                        invoice=existing_invoice,
                        idempotent_replay=True,
                    )

        if session.status == PersonalTrainingSession.STATUS_CANCELLED:
            raise GymPaymentError("Cannot bill a cancelled PT session.")
        if session.status == PersonalTrainingSession.STATUS_NO_SHOW:
            raise GymPaymentError("Cannot bill a no-show PT session.")

        member = session.member
        branch = GymPaymentService._resolve_branch(
            branch_id=data.get("branch_id"), member=member, user=user
        )
        customer = GymPaymentService.ensure_customer_for_member(
            member=member, branch=branch, user=user
        )
        total_amount = GymPaymentService._pt_amount(session=session, data=data)
        if total_amount <= 0:
            raise GymPaymentError(
                "Amount must be positive. Set trainer hourly_rate or pass amount."
            )

        product = GymPaymentService.ensure_pt_product(
            tenant_id=member.tenant_id or branch.tenant_id, user=user
        )
        if product.selling_price != total_amount:
            product.selling_price = total_amount
            product.updated_by = user
            product.save(update_fields=["selling_price", "updated_by", "updated_at"])

        payment_method, payment_reference, tender_lines = GymPaymentService._normalize_tenders(
            data=data, total_amount=total_amount
        )
        is_on_account = payment_method == Payment.METHOD_ON_ACCOUNT
        invoice_status = Invoice.STATUS_SENT if is_on_account else Invoice.STATUS_PAID
        if is_on_account:
            amount_paid = Decimal("0")
        elif payment_method == "split":
            amount_paid = min(
                total_amount,
                sum(
                    (t["amount"] for t in tender_lines if t["method"] != Payment.METHOD_ON_ACCOUNT),
                    Decimal("0"),
                ),
            )
        else:
            amount_paid = total_amount

        trainer_name = session.trainer.full_name if session.trainer_id else "trainer"
        payment_note = (
            f"Payment: {payment_method} | Gym PT: {trainer_name} "
            f"({session.duration_minutes} min)"
        )
        if payment_reference:
            payment_note += f" | Ref: {payment_reference}"
        notes = (data.get("notes") or "").strip()
        if notes:
            notes = f"{notes}\n{payment_note}"
        else:
            notes = payment_note

        invoice_data = stamp_tenant_id(
            {
                "customer_id": str(customer.id),
                "branch_id": str(branch.id),
                "status": invoice_status,
                "issue_date": timezone.localdate(),
                "due_date": timezone.localdate() + timedelta(days=30) if is_on_account else None,
                "discount_amount": Decimal("0"),
                "amount_paid": amount_paid,
                "notes": notes,
                "served_by_user": user,
            },
            user=user,
            request=request,
        )
        if idempotency_key:
            invoice_data["idempotency_key"] = idempotency_key

        invoice = InvoiceService.create(
            data=invoice_data,
            items=[
                {
                    "product_id": str(product.id),
                    "quantity": Decimal("1"),
                    "unit_price": total_amount,
                }
            ],
            user=user,
        )
        invoice.total_amount = total_amount
        invoice.subtotal = total_amount
        invoice.save(update_fields=["total_amount", "subtotal", "updated_at"])

        invoice.payments.all().delete()
        for tender in tender_lines:
            method = tender["method"]
            if method not in dict(Payment.METHOD_CHOICES):
                method = Payment.METHOD_OTHER
            Payment.objects.create(
                invoice=invoice,
                branch=branch,
                method=method,
                amount=tender["amount"],
                reference=tender.get("reference") or payment_reference or "",
                tenant_id=invoice.tenant_id,
                created_by=user,
            )

        try:
            session = PTSessionService.set_status(
                session=session,
                status=PersonalTrainingSession.STATUS_COMPLETED,
                user=user,
            )
        except TrainerError as exc:
            raise GymPaymentError(str(exc)) from exc

        session.amount_charged = total_amount
        session.invoice = invoice
        session.payment_reference = payment_reference or ""
        session.updated_by = user
        session.save(
            update_fields=[
                "amount_charged",
                "invoice",
                "payment_reference",
                "updated_by",
                "updated_at",
            ]
        )

        from apps.finance.services.posting_service import AccountingPostingService

        AccountingPostingService.post_gym_service(
            invoice=invoice,
            user=user,
            payment_method=payment_method,
            tender_lines=[
                {
                    "method": t["method"],
                    "amount": str(t["amount"]),
                    "reference": t.get("reference") or "",
                }
                for t in tender_lines
            ],
            revenue_mapping_key="GYM_PERSONAL_TRAINING_REVENUE",
            service_label="personal_training",
        )

        return GymPaymentService.serialize_pt_checkout(
            session=session, invoice=invoice, idempotent_replay=False
        )

    @staticmethod
    @transaction.atomic
    def ensure_class_product(*, tenant_id, user=None) -> Product:
        sku = "gym-class-dropin"
        existing = Product.active_objects().filter(tenant_id=tenant_id, sku=sku).first()
        if existing:
            return existing

        category = Category.active_objects().filter(
            tenant_id=tenant_id, name__iexact="Gym Services"
        ).first()
        if category is None:
            category = Category.objects.create(
                name="Gym Services",
                description="Membership and gym service lines",
                tenant_id=tenant_id,
                created_by=user,
            )

        unit = Unit.active_objects().filter(
            tenant_id=tenant_id, abbreviation__iexact="svc"
        ).first()
        if unit is None:
            unit = Unit.objects.create(
                name="Service",
                abbreviation="svc",
                tenant_id=tenant_id,
                created_by=user,
            )

        return Product.objects.create(
            sku=sku,
            name="Class Drop-in",
            category=category,
            unit=unit,
            cost_price=Decimal("0"),
            selling_price=Decimal("0"),
            minimum_stock=0,
            description="Billable gym class drop-in",
            tenant_id=tenant_id,
            created_by=user,
        )

    @staticmethod
    def _class_booking_amount(*, booking, data) -> Decimal:
        if data.get("amount") is not None and str(data.get("amount")).strip() != "":
            return _money(data.get("amount"))
        price = getattr(booking.schedule.gym_class, "drop_in_price", 0) or 0
        return _money(price)

    @staticmethod
    def serialize_class_checkout(*, booking, invoice, idempotent_replay=False) -> dict:
        from apps.gym.services.class_service import BookingService

        payments = [
            {
                "id": str(p.id),
                "method": p.method,
                "amount": float(p.amount),
                "reference": p.reference or "",
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
            }
            for p in invoice.payments.filter(deleted_at__isnull=True).order_by("paid_at")
        ]
        return {
            "booking": BookingService.serialize(booking),
            "invoice": {
                "id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "status": invoice.status,
                "total_amount": float(invoice.total_amount),
                "amount_paid": float(invoice.amount_paid),
            },
            "payments": payments,
            "payment_reference": (
                payments[0]["reference"]
                if payments
                else booking.payment_reference or ""
            ),
            "idempotent_replay": idempotent_replay,
        }

    @staticmethod
    @transaction.atomic
    def checkout_class_booking(*, booking_id, data, user=None, request=None) -> dict:
        from apps.gym.models import ClassBooking
        from apps.gym.services.class_service import BookingService

        qs = BookingService.list(user=user, request=request).select_related(
            "member",
            "member__customer",
            "member__branch",
            "schedule",
            "schedule__gym_class",
            "invoice",
        )
        booking = qs.filter(pk=booking_id).first()
        if booking is None:
            raise GymPaymentError("Class booking not found.")

        idempotency_key = (data.get("idempotency_key") or "").strip() or None
        if booking.invoice_id:
            from apps.finance.services.posting_service import AccountingPostingService

            AccountingPostingService.post_gym_service(
                invoice=booking.invoice,
                user=user,
                revenue_mapping_key="GYM_CLASS_REVENUE",
                service_label="class_drop_in",
            )
            return GymPaymentService.serialize_class_checkout(
                booking=booking, invoice=booking.invoice, idempotent_replay=True
            )
        if idempotency_key:
            existing_invoice = (
                Invoice.active_objects()
                .filter(idempotency_key=idempotency_key, deleted_at__isnull=True)
                .prefetch_related("payments", "gym_class_bookings")
                .first()
            )
            if existing_invoice is not None:
                linked = existing_invoice.gym_class_bookings.filter(
                    deleted_at__isnull=True
                ).first()
                if linked is not None:
                    from apps.finance.services.posting_service import AccountingPostingService

                    AccountingPostingService.post_gym_service(
                        invoice=existing_invoice,
                        user=user,
                        revenue_mapping_key="GYM_CLASS_REVENUE",
                        service_label="class_drop_in",
                    )
                    return GymPaymentService.serialize_class_checkout(
                        booking=linked,
                        invoice=existing_invoice,
                        idempotent_replay=True,
                    )

        if booking.status == ClassBooking.STATUS_CANCELLED:
            raise GymPaymentError("Cannot bill a cancelled booking.")
        if booking.status == ClassBooking.STATUS_WAITLISTED:
            raise GymPaymentError("Promote waitlist booking before billing.")

        member = booking.member
        branch = GymPaymentService._resolve_branch(
            branch_id=data.get("branch_id")
            or getattr(booking.schedule, "branch_id", None),
            member=member,
            user=user,
        )
        customer = GymPaymentService.ensure_customer_for_member(
            member=member, branch=branch, user=user
        )
        total_amount = GymPaymentService._class_booking_amount(booking=booking, data=data)
        if total_amount <= 0:
            raise GymPaymentError(
                "Amount must be positive. Set class drop_in_price or pass amount."
            )

        product = GymPaymentService.ensure_class_product(
            tenant_id=member.tenant_id or branch.tenant_id, user=user
        )
        if product.selling_price != total_amount:
            product.selling_price = total_amount
            product.updated_by = user
            product.save(update_fields=["selling_price", "updated_by", "updated_at"])

        payment_method, payment_reference, tender_lines = GymPaymentService._normalize_tenders(
            data=data, total_amount=total_amount
        )
        is_on_account = payment_method == Payment.METHOD_ON_ACCOUNT
        invoice_status = Invoice.STATUS_SENT if is_on_account else Invoice.STATUS_PAID
        if is_on_account:
            amount_paid = Decimal("0")
        elif payment_method == "split":
            amount_paid = min(
                total_amount,
                sum(
                    (t["amount"] for t in tender_lines if t["method"] != Payment.METHOD_ON_ACCOUNT),
                    Decimal("0"),
                ),
            )
        else:
            amount_paid = total_amount

        class_name = booking.schedule.gym_class.name if booking.schedule_id else "class"
        payment_note = f"Payment: {payment_method} | Gym class drop-in: {class_name}"
        if payment_reference:
            payment_note += f" | Ref: {payment_reference}"
        notes = (data.get("notes") or "").strip()
        if notes:
            notes = f"{notes}\n{payment_note}"
        else:
            notes = payment_note

        invoice_data = stamp_tenant_id(
            {
                "customer_id": str(customer.id),
                "branch_id": str(branch.id),
                "status": invoice_status,
                "issue_date": timezone.localdate(),
                "due_date": timezone.localdate() + timedelta(days=30) if is_on_account else None,
                "discount_amount": Decimal("0"),
                "amount_paid": amount_paid,
                "notes": notes,
                "served_by_user": user,
            },
            user=user,
            request=request,
        )
        if idempotency_key:
            invoice_data["idempotency_key"] = idempotency_key

        invoice = InvoiceService.create(
            data=invoice_data,
            items=[
                {
                    "product_id": str(product.id),
                    "quantity": Decimal("1"),
                    "unit_price": total_amount,
                }
            ],
            user=user,
        )
        invoice.total_amount = total_amount
        invoice.subtotal = total_amount
        invoice.save(update_fields=["total_amount", "subtotal", "updated_at"])

        invoice.payments.all().delete()
        for tender in tender_lines:
            method = tender["method"]
            if method not in dict(Payment.METHOD_CHOICES):
                method = Payment.METHOD_OTHER
            Payment.objects.create(
                invoice=invoice,
                branch=branch,
                method=method,
                amount=tender["amount"],
                reference=tender.get("reference") or payment_reference or "",
                tenant_id=invoice.tenant_id,
                created_by=user,
            )

        booking.amount_charged = total_amount
        booking.invoice = invoice
        booking.payment_reference = payment_reference or ""
        booking.updated_by = user
        booking.save(
            update_fields=[
                "amount_charged",
                "invoice",
                "payment_reference",
                "updated_by",
                "updated_at",
            ]
        )

        from apps.finance.services.posting_service import AccountingPostingService

        AccountingPostingService.post_gym_service(
            invoice=invoice,
            user=user,
            payment_method=payment_method,
            tender_lines=[
                {
                    "method": t["method"],
                    "amount": str(t["amount"]),
                    "reference": t.get("reference") or "",
                }
                for t in tender_lines
            ],
            revenue_mapping_key="GYM_CLASS_REVENUE",
            service_label="class_drop_in",
        )

        return GymPaymentService.serialize_class_checkout(
            booking=booking, invoice=invoice, idempotent_replay=False
        )
