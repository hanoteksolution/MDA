"""Office rental services (PHASE 20) — commercial leases on shared PropertyUnit."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.office_rental.models import OfficeLease, OfficeLeaseCharge, OfficeTenant
from apps.property_management.models import PropertyUnit
from apps.property_management.services import PropertyError, PropertyService
from apps.settings_app.models import Branch
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class OfficeError(ValueError):
    pass


def _as_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return parse_date(str(value)[:10])


class OfficeService:
    @staticmethod
    def _scope(qs, *, user=None, request=None, branch_id=None):
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs

    @staticmethod
    def _require_branch(*, branch_id, user=None, request=None) -> Branch:
        if not branch_id:
            raise OfficeError("branch_id is required.")
        qs = apply_tenant_scope(Branch.active_objects(), user=user, request=request)
        branch = qs.filter(pk=branch_id).first()
        if not branch:
            branch = Branch.active_objects().filter(pk=branch_id).first()
        if not branch:
            raise OfficeError("Branch not found for this tenant.")
        return branch

    @staticmethod
    def _next_lease_number(*, tenant_id) -> str:
        today = timezone.localdate().strftime("%Y%m%d")
        prefix = f"OL-{today}-"
        count = (
            OfficeLease.objects.filter(
                tenant_id=tenant_id, lease_number__startswith=prefix
            ).count()
            + 1
        )
        return f"{prefix}{count:04d}"

    @staticmethod
    def summary(*, branch_id=None, user=None, request=None) -> dict:
        leases = OfficeService.list_leases(
            branch_id=branch_id, user=user, request=request
        )
        charges = OfficeService.list_charges(
            branch_id=branch_id, user=user, request=request
        )
        offices = PropertyService.list_units(
            branch_id=branch_id, user=user, request=request
        ).filter(
            kind__in=[PropertyUnit.KIND_OFFICE, PropertyUnit.KIND_RETAIL],
            is_active=True,
        )
        pending = charges.filter(
            status__in=[
                OfficeLeaseCharge.STATUS_PENDING,
                OfficeLeaseCharge.STATUS_INVOICED,
            ]
        )
        overdue = pending.filter(due_date__lt=timezone.localdate())
        return {
            "tenants": OfficeService.list_tenants(
                branch_id=branch_id, user=user, request=request
            ).count(),
            "leases_active": leases.filter(status=OfficeLease.STATUS_ACTIVE).count(),
            "leases_draft": leases.filter(status=OfficeLease.STATUS_DRAFT).count(),
            "office_units": offices.count(),
            "units_occupied": offices.filter(
                status=PropertyUnit.STATUS_OCCUPIED
            ).count(),
            "units_vacant": offices.filter(status=PropertyUnit.STATUS_VACANT).count(),
            "charges_pending": pending.count(),
            "charges_overdue": overdue.count(),
            "rent_pending_amount": float(
                pending.filter(
                    charge_type__in=[
                        OfficeLeaseCharge.TYPE_RENT,
                        OfficeLeaseCharge.TYPE_SERVICE,
                    ]
                ).aggregate(t=Sum("amount"))["t"]
                or 0
            ),
            "deposits_held": leases.filter(
                status=OfficeLease.STATUS_ACTIVE, deposit_held=True
            ).count(),
        }

    @staticmethod
    def list_tenants(*, branch_id=None, user=None, request=None):
        qs = OfficeTenant.active_objects().select_related("branch", "customer")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(Q(branch_id=branch_id) | Q(branch_id__isnull=True))
        return qs.order_by("company_name")

    @staticmethod
    def get_tenant(*, pk, user=None, request=None):
        return OfficeService.list_tenants(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_tenant(*, data, user=None, request=None) -> OfficeTenant:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = None
        if payload.get("branch_id"):
            branch = OfficeService._require_branch(
                branch_id=payload.get("branch_id"), user=user, request=request
            )
        name = (payload.get("company_name") or payload.get("full_name") or "").strip()
        if not name:
            raise OfficeError("company_name is required.")
        return OfficeTenant.objects.create(
            tenant_id=payload.get("tenant_id")
            or (branch.tenant_id if branch else None),
            branch=branch,
            customer_id=payload.get("customer_id") or None,
            company_name=name,
            registration_number=(payload.get("registration_number") or "").strip(),
            contact_name=(payload.get("contact_name") or "").strip(),
            phone=(payload.get("phone") or "").strip(),
            email=(payload.get("email") or "").strip(),
            notes=(payload.get("notes") or "").strip(),
            is_active=bool(payload.get("is_active", True)),
            created_by=user,
        )

    @staticmethod
    def list_leases(*, branch_id=None, status=None, user=None, request=None):
        qs = OfficeLease.active_objects().select_related(
            "branch", "unit", "unit__building", "office_tenant"
        )
        qs = OfficeService._scope(qs, user=user, request=request, branch_id=branch_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-start_date", "-created_at")

    @staticmethod
    def get_lease(*, pk, user=None, request=None):
        return OfficeService.list_leases(user=user, request=request).get(pk=pk)

    @staticmethod
    def _assert_unit_leaseable(*, unit: PropertyUnit, exclude_lease_id=None):
        if unit.kind not in (PropertyUnit.KIND_OFFICE, PropertyUnit.KIND_RETAIL):
            raise OfficeError("Housing units belong to housing rental, not office.")
        active = OfficeLease.active_objects().filter(
            unit_id=unit.id,
            status__in=[OfficeLease.STATUS_DRAFT, OfficeLease.STATUS_ACTIVE],
        )
        if exclude_lease_id:
            active = active.exclude(pk=exclude_lease_id)
        if active.exists():
            raise OfficeError(f"Unit {unit.code} already has an open office lease.")

    @staticmethod
    @transaction.atomic
    def create_lease(*, data, user=None, request=None) -> OfficeLease:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = OfficeService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        tenant_id = payload.get("tenant_id") or branch.tenant_id

        if payload.get("office_tenant_id"):
            person = OfficeService.get_tenant(
                pk=payload.get("office_tenant_id"), user=user, request=request
            )
        else:
            person = OfficeService.create_tenant(
                data={
                    "branch_id": branch.id,
                    "company_name": payload.get("company_name")
                    or payload.get("tenant_name"),
                    "registration_number": payload.get("registration_number") or "",
                    "contact_name": payload.get("contact_name") or "",
                    "phone": payload.get("phone") or "",
                    "email": payload.get("email") or "",
                    "customer_id": payload.get("customer_id"),
                    "tenant_id": tenant_id,
                },
                user=user,
                request=request,
            )

        try:
            unit = PropertyService.get_unit(
                pk=payload.get("unit_id"), user=user, request=request
            )
        except ObjectDoesNotExist as exc:
            raise OfficeError("Unit not found.") from exc

        OfficeService._assert_unit_leaseable(unit=unit)

        start = _as_date(payload.get("start_date")) or timezone.localdate()
        end = _as_date(payload.get("end_date"))
        if end and end <= start:
            raise OfficeError("end_date must be after start_date.")

        rent = payload.get("rent_amount")
        if rent is None or str(rent).strip() == "":
            rent = unit.rent_amount
        deposit = payload.get("deposit_amount")
        if deposit is None or str(deposit).strip() == "":
            deposit = unit.deposit_amount

        lease = OfficeLease.objects.create(
            tenant_id=tenant_id,
            branch=branch,
            unit=unit,
            office_tenant=person,
            lease_number=OfficeService._next_lease_number(tenant_id=tenant_id),
            status=OfficeLease.STATUS_DRAFT,
            start_date=start,
            end_date=end,
            rent_amount=Decimal(str(rent or 0)),
            service_charge=Decimal(str(payload.get("service_charge") or 0)),
            deposit_amount=Decimal(str(deposit or 0)),
            parking_slots=int(payload.get("parking_slots") or 0),
            furnished=bool(payload.get("furnished", False)),
            internet_included=bool(payload.get("internet_included", False)),
            electricity_included=bool(payload.get("electricity_included", False)),
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        if payload.get("activate"):
            lease = OfficeService.activate_lease(lease=lease, user=user)
        elif unit.status == PropertyUnit.STATUS_VACANT:
            try:
                PropertyService.set_unit_status(
                    unit=unit, status=PropertyUnit.STATUS_RESERVED, user=user
                )
            except PropertyError:
                pass
        return lease

    @staticmethod
    @transaction.atomic
    def activate_lease(*, lease: OfficeLease, user=None) -> OfficeLease:
        if lease.status != OfficeLease.STATUS_DRAFT:
            raise OfficeError("Only draft leases can be activated.")
        OfficeService._assert_unit_leaseable(unit=lease.unit, exclude_lease_id=lease.id)
        lease.status = OfficeLease.STATUS_ACTIVE
        lease.activated_at = timezone.now()
        lease.updated_by = user
        lease.save(update_fields=["status", "activated_at", "updated_by", "updated_at"])
        PropertyService.set_unit_status(
            unit=lease.unit, status=PropertyUnit.STATUS_OCCUPIED, user=user
        )
        if lease.deposit_amount and lease.deposit_amount > 0 and not lease.deposit_held:
            OfficeService.add_charge(
                lease=lease,
                data={
                    "charge_type": OfficeLeaseCharge.TYPE_DEPOSIT,
                    "description": f"Security deposit · {lease.lease_number}",
                    "amount": lease.deposit_amount,
                    "due_date": lease.start_date,
                },
                user=user,
            )
            lease.deposit_held = True
            lease.save(update_fields=["deposit_held", "updated_at"])
        return lease

    @staticmethod
    @transaction.atomic
    def terminate_lease(*, lease: OfficeLease, user=None, status=None) -> OfficeLease:
        if lease.status != OfficeLease.STATUS_ACTIVE:
            raise OfficeError("Only active leases can be terminated.")
        new_status = status or OfficeLease.STATUS_TERMINATED
        if new_status not in (OfficeLease.STATUS_TERMINATED, OfficeLease.STATUS_EXPIRED):
            raise OfficeError("Invalid termination status.")
        lease.status = new_status
        lease.terminated_at = timezone.now()
        lease.updated_by = user
        lease.save(
            update_fields=["status", "terminated_at", "updated_by", "updated_at"]
        )
        other = (
            OfficeLease.active_objects()
            .filter(unit_id=lease.unit_id, status=OfficeLease.STATUS_ACTIVE)
            .exclude(pk=lease.pk)
            .exists()
        )
        if not other:
            PropertyService.set_unit_status(
                unit=lease.unit, status=PropertyUnit.STATUS_VACANT, user=user
            )
        return lease

    @staticmethod
    def list_charges(*, branch_id=None, lease_id=None, user=None, request=None):
        qs = OfficeLeaseCharge.active_objects().select_related(
            "lease", "lease__office_tenant", "lease__unit", "invoice", "branch"
        )
        qs = OfficeService._scope(qs, user=user, request=request, branch_id=branch_id)
        if lease_id:
            qs = qs.filter(lease_id=lease_id)
        return qs.order_by("-posted_at")

    @staticmethod
    @transaction.atomic
    def add_charge(*, lease: OfficeLease, data, user=None) -> OfficeLeaseCharge:
        if lease.status not in (OfficeLease.STATUS_ACTIVE, OfficeLease.STATUS_DRAFT):
            raise OfficeError("Cannot charge a closed lease.")
        description = (data.get("description") or "").strip()
        if not description:
            raise OfficeError("Charge description is required.")
        charge_type = data.get("charge_type") or OfficeLeaseCharge.TYPE_RENT
        if charge_type not in dict(OfficeLeaseCharge.TYPE_CHOICES):
            raise OfficeError(f"Invalid charge type: {charge_type}")
        amount = Decimal(str(data.get("amount") or 0))
        if amount <= 0:
            raise OfficeError("Charge amount must be positive.")
        return OfficeLeaseCharge.objects.create(
            tenant_id=lease.tenant_id,
            lease=lease,
            branch_id=lease.branch_id,
            charge_type=charge_type,
            status=OfficeLeaseCharge.STATUS_PENDING,
            description=description,
            amount=amount,
            period_start=_as_date(data.get("period_start")),
            period_end=_as_date(data.get("period_end")),
            due_date=_as_date(data.get("due_date")) or timezone.localdate(),
            created_by=user,
        )

    @staticmethod
    @transaction.atomic
    def post_rent_charge(*, lease: OfficeLease, user=None, period_start=None, period_end=None):
        if lease.status != OfficeLease.STATUS_ACTIVE:
            raise OfficeError("Rent can only be posted on active leases.")
        start = _as_date(period_start) or timezone.localdate().replace(day=1)
        if period_end:
            end = _as_date(period_end)
        else:
            if start.month == 12:
                end = date(start.year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(start.year, start.month + 1, 1) - timedelta(days=1)
        charges = []
        charges.append(
            OfficeService.add_charge(
                lease=lease,
                data={
                    "charge_type": OfficeLeaseCharge.TYPE_RENT,
                    "description": f"Office rent {start.isoformat()} → {end.isoformat()} · {lease.unit.code}",
                    "amount": lease.rent_amount,
                    "period_start": start,
                    "period_end": end,
                    "due_date": start,
                },
                user=user,
            )
        )
        if lease.service_charge and lease.service_charge > 0:
            charges.append(
                OfficeService.add_charge(
                    lease=lease,
                    data={
                        "charge_type": OfficeLeaseCharge.TYPE_SERVICE,
                        "description": f"Service charge {start.isoformat()} → {end.isoformat()} · {lease.unit.code}",
                        "amount": lease.service_charge,
                        "period_start": start,
                        "period_end": end,
                        "due_date": start,
                    },
                    user=user,
                )
            )
        return charges[0]

    @staticmethod
    @transaction.atomic
    def invoice_charge(
        *,
        charge: OfficeLeaseCharge,
        payment_method: str = "on_account",
        payment_reference: str = "",
        user=None,
    ) -> OfficeLeaseCharge:
        from apps.property_management.services.rental_billing_service import (
            RentalBillingError,
            RentalBillingService,
        )

        lease = charge.lease
        tenant = lease.office_tenant
        try:
            customer = RentalBillingService.ensure_customer(
                tenant_id=charge.tenant_id,
                branch=charge.branch,
                full_name=tenant.company_name,
                phone=tenant.phone or "",
                email=tenant.email or "",
                code_prefix="OFC",
                existing_customer=tenant.customer,
                user=user,
            )
            if not tenant.customer_id:
                tenant.customer = customer
                tenant.updated_by = user
                tenant.save(update_fields=["customer", "updated_by", "updated_at"])
            product = RentalBillingService.ensure_service_product(
                tenant_id=charge.tenant_id,
                sku="office-rent",
                name="Office Rent",
                category_name="Office Rental",
                user=user,
            )
            RentalBillingService.create_invoice_for_charge(
                charge=charge,
                customer=customer,
                branch=charge.branch,
                product=product,
                vertical="office",
                payment_method=payment_method,
                payment_reference=payment_reference,
                lease_label=lease.lease_number,
                user=user,
            )
        except RentalBillingError as exc:
            raise OfficeError(str(exc)) from exc

        charge.refresh_from_db()
        if (
            charge.charge_type == OfficeLeaseCharge.TYPE_DEPOSIT
            and charge.status == OfficeLeaseCharge.STATUS_PAID
        ):
            lease.deposit_held = True
            lease.updated_by = user
            lease.save(update_fields=["deposit_held", "updated_by", "updated_at"])
        return charge

    @staticmethod
    @transaction.atomic
    def collect_charge(
        *,
        charge: OfficeLeaseCharge,
        payment_method: str = "cash",
        payment_reference: str = "",
        user=None,
    ) -> OfficeLeaseCharge:
        from apps.property_management.services.rental_billing_service import (
            RentalBillingError,
            RentalBillingService,
        )

        try:
            if charge.status == OfficeLeaseCharge.STATUS_PENDING:
                return OfficeService.invoice_charge(
                    charge=charge,
                    payment_method=payment_method,
                    payment_reference=payment_reference,
                    user=user,
                )
            RentalBillingService.collect_invoice_for_charge(
                charge=charge,
                payment_method=payment_method,
                payment_reference=payment_reference,
                user=user,
            )
        except RentalBillingError as exc:
            raise OfficeError(str(exc)) from exc

        charge.refresh_from_db()
        if (
            charge.charge_type == OfficeLeaseCharge.TYPE_DEPOSIT
            and charge.status == OfficeLeaseCharge.STATUS_PAID
        ):
            lease = charge.lease
            lease.deposit_held = True
            lease.updated_by = user
            lease.save(update_fields=["deposit_held", "updated_by", "updated_at"])
        return charge

    @staticmethod
    @transaction.atomic
    def mark_charge_paid(*, charge: OfficeLeaseCharge, user=None, data=None) -> OfficeLeaseCharge:
        data = data or {}
        return OfficeService.collect_charge(
            charge=charge,
            payment_method=data.get("payment_method") or "cash",
            payment_reference=(data.get("payment_reference") or "").strip(),
            user=user,
        )
