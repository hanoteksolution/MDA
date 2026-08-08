"""Housing rental services (PHASE 19) — leases on shared PropertyUnit."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.housing_rental.models import HousingTenant, Lease, LeaseCharge
from apps.property_management.models import PropertyUnit
from apps.property_management.services import PropertyError, PropertyService
from apps.settings_app.models import Branch
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class HousingError(ValueError):
    pass


def _as_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return parse_date(str(value)[:10])


class HousingService:
    @staticmethod
    def _scope(qs, *, user=None, request=None, branch_id=None):
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs

    @staticmethod
    def _require_branch(*, branch_id, user=None, request=None) -> Branch:
        if not branch_id:
            raise HousingError("branch_id is required.")
        qs = apply_tenant_scope(Branch.active_objects(), user=user, request=request)
        branch = qs.filter(pk=branch_id).first()
        if not branch:
            branch = Branch.active_objects().filter(pk=branch_id).first()
        if not branch:
            raise HousingError("Branch not found for this tenant.")
        return branch

    @staticmethod
    def _next_lease_number(*, tenant_id) -> str:
        today = timezone.localdate().strftime("%Y%m%d")
        prefix = f"HL-{today}-"
        count = (
            Lease.objects.filter(
                tenant_id=tenant_id, lease_number__startswith=prefix
            ).count()
            + 1
        )
        return f"{prefix}{count:04d}"

    @staticmethod
    def summary(*, branch_id=None, user=None, request=None) -> dict:
        leases = HousingService.list_leases(
            branch_id=branch_id, user=user, request=request
        )
        charges = HousingService.list_charges(
            branch_id=branch_id, user=user, request=request
        )
        residential = PropertyService.list_units(
            branch_id=branch_id, user=user, request=request
        ).filter(kind=PropertyUnit.KIND_RESIDENTIAL, is_active=True)
        pending = charges.filter(
            status__in=[LeaseCharge.STATUS_PENDING, LeaseCharge.STATUS_INVOICED]
        )
        overdue = pending.filter(due_date__lt=timezone.localdate())
        return {
            "tenants": HousingService.list_tenants(
                branch_id=branch_id, user=user, request=request
            ).count(),
            "leases_active": leases.filter(status=Lease.STATUS_ACTIVE).count(),
            "leases_draft": leases.filter(status=Lease.STATUS_DRAFT).count(),
            "residential_units": residential.count(),
            "units_occupied": residential.filter(
                status=PropertyUnit.STATUS_OCCUPIED
            ).count(),
            "units_vacant": residential.filter(
                status=PropertyUnit.STATUS_VACANT
            ).count(),
            "charges_pending": pending.count(),
            "charges_overdue": overdue.count(),
            "rent_pending_amount": float(
                pending.filter(charge_type=LeaseCharge.TYPE_RENT).aggregate(
                    t=Sum("amount")
                )["t"]
                or 0
            ),
            "deposits_held": leases.filter(
                status=Lease.STATUS_ACTIVE, deposit_held=True
            ).count(),
        }

    # --- Tenants ---
    @staticmethod
    def list_tenants(*, branch_id=None, user=None, request=None):
        qs = HousingTenant.active_objects().select_related("branch", "customer")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(Q(branch_id=branch_id) | Q(branch_id__isnull=True))
        return qs.order_by("full_name")

    @staticmethod
    def get_tenant(*, pk, user=None, request=None):
        return HousingService.list_tenants(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_tenant(*, data, user=None, request=None) -> HousingTenant:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = None
        if payload.get("branch_id"):
            branch = HousingService._require_branch(
                branch_id=payload.get("branch_id"), user=user, request=request
            )
        name = (payload.get("full_name") or "").strip()
        if not name:
            raise HousingError("Tenant full_name is required.")
        customer_id = payload.get("customer_id") or None
        return HousingTenant.objects.create(
            tenant_id=payload.get("tenant_id")
            or (branch.tenant_id if branch else None),
            branch=branch,
            customer_id=customer_id,
            full_name=name,
            phone=(payload.get("phone") or "").strip(),
            email=(payload.get("email") or "").strip(),
            id_number=(payload.get("id_number") or "").strip(),
            notes=(payload.get("notes") or "").strip(),
            is_active=bool(payload.get("is_active", True)),
            created_by=user,
        )

    # --- Leases ---
    @staticmethod
    def list_leases(*, branch_id=None, status=None, user=None, request=None):
        qs = Lease.active_objects().select_related(
            "branch",
            "unit",
            "unit__building",
            "housing_tenant",
        )
        qs = HousingService._scope(qs, user=user, request=request, branch_id=branch_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-start_date", "-created_at")

    @staticmethod
    def get_lease(*, pk, user=None, request=None):
        return HousingService.list_leases(user=user, request=request).get(pk=pk)

    @staticmethod
    def _assert_unit_leaseable(*, unit: PropertyUnit, exclude_lease_id=None):
        if unit.kind not in (
            PropertyUnit.KIND_RESIDENTIAL,
            PropertyUnit.KIND_OTHER,
        ):
            # Allow residential primary; OTHER for studio/bedsitter demos
            if unit.kind == PropertyUnit.KIND_OFFICE:
                raise HousingError("Office units belong to office rental, not housing.")
        active = Lease.active_objects().filter(
            unit_id=unit.id,
            status__in=[Lease.STATUS_DRAFT, Lease.STATUS_ACTIVE],
        )
        if exclude_lease_id:
            active = active.exclude(pk=exclude_lease_id)
        if active.exists():
            raise HousingError(f"Unit {unit.code} already has an open lease.")

    @staticmethod
    @transaction.atomic
    def create_lease(*, data, user=None, request=None) -> Lease:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = HousingService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        tenant_id = payload.get("tenant_id") or branch.tenant_id

        if payload.get("housing_tenant_id"):
            person = HousingService.get_tenant(
                pk=payload.get("housing_tenant_id"),
                user=user,
                request=request,
            )
        else:
            person = HousingService.create_tenant(
                data={
                    "branch_id": branch.id,
                    "full_name": payload.get("tenant_name") or payload.get("full_name"),
                    "phone": payload.get("phone") or "",
                    "email": payload.get("email") or "",
                    "id_number": payload.get("id_number") or "",
                    "customer_id": payload.get("customer_id"),
                    "tenant_id": tenant_id,
                },
                user=user,
                request=request,
            )

        from django.core.exceptions import ObjectDoesNotExist

        try:
            unit = PropertyService.get_unit(
                pk=payload.get("unit_id"), user=user, request=request
            )
        except ObjectDoesNotExist as exc:
            raise HousingError("Unit not found.") from exc

        HousingService._assert_unit_leaseable(unit=unit)

        start = _as_date(payload.get("start_date")) or timezone.localdate()
        end = _as_date(payload.get("end_date"))
        if end and end <= start:
            raise HousingError("end_date must be after start_date.")

        rent = payload.get("rent_amount")
        if rent is None or str(rent).strip() == "":
            rent = unit.rent_amount
        deposit = payload.get("deposit_amount")
        if deposit is None or str(deposit).strip() == "":
            deposit = unit.deposit_amount

        lease = Lease.objects.create(
            tenant_id=tenant_id,
            branch=branch,
            unit=unit,
            housing_tenant=person,
            lease_number=HousingService._next_lease_number(tenant_id=tenant_id),
            status=Lease.STATUS_DRAFT,
            start_date=start,
            end_date=end,
            rent_amount=Decimal(str(rent or 0)),
            deposit_amount=Decimal(str(deposit or 0)),
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        if payload.get("activate"):
            lease = HousingService.activate_lease(lease=lease, user=user)
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
    def activate_lease(*, lease: Lease, user=None) -> Lease:
        if lease.status != Lease.STATUS_DRAFT:
            raise HousingError("Only draft leases can be activated.")
        HousingService._assert_unit_leaseable(
            unit=lease.unit, exclude_lease_id=lease.id
        )
        lease.status = Lease.STATUS_ACTIVE
        lease.activated_at = timezone.now()
        lease.updated_by = user
        lease.save(update_fields=["status", "activated_at", "updated_by", "updated_at"])
        PropertyService.set_unit_status(
            unit=lease.unit, status=PropertyUnit.STATUS_OCCUPIED, user=user
        )
        if lease.deposit_amount and lease.deposit_amount > 0 and not lease.deposit_held:
            HousingService.add_charge(
                lease=lease,
                data={
                    "charge_type": LeaseCharge.TYPE_DEPOSIT,
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
    def terminate_lease(*, lease: Lease, user=None, status=None) -> Lease:
        if lease.status != Lease.STATUS_ACTIVE:
            raise HousingError("Only active leases can be terminated.")
        new_status = status or Lease.STATUS_TERMINATED
        if new_status not in (Lease.STATUS_TERMINATED, Lease.STATUS_EXPIRED):
            raise HousingError("Invalid termination status.")
        lease.status = new_status
        lease.terminated_at = timezone.now()
        lease.updated_by = user
        lease.save(
            update_fields=["status", "terminated_at", "updated_by", "updated_at"]
        )
        # Free unit only if no other active lease
        other = (
            Lease.active_objects()
            .filter(unit_id=lease.unit_id, status=Lease.STATUS_ACTIVE)
            .exclude(pk=lease.pk)
            .exists()
        )
        if not other:
            PropertyService.set_unit_status(
                unit=lease.unit, status=PropertyUnit.STATUS_VACANT, user=user
            )
        return lease

    # --- Charges ---
    @staticmethod
    def list_charges(*, branch_id=None, lease_id=None, user=None, request=None):
        qs = LeaseCharge.active_objects().select_related(
            "lease", "lease__housing_tenant", "lease__unit", "invoice", "branch"
        )
        qs = HousingService._scope(qs, user=user, request=request, branch_id=branch_id)
        if lease_id:
            qs = qs.filter(lease_id=lease_id)
        return qs.order_by("-posted_at")

    @staticmethod
    @transaction.atomic
    def add_charge(*, lease: Lease, data, user=None) -> LeaseCharge:
        if lease.status not in (Lease.STATUS_ACTIVE, Lease.STATUS_DRAFT):
            raise HousingError("Cannot charge a closed lease.")
        description = (data.get("description") or "").strip()
        if not description:
            raise HousingError("Charge description is required.")
        charge_type = data.get("charge_type") or LeaseCharge.TYPE_RENT
        if charge_type not in dict(LeaseCharge.TYPE_CHOICES):
            raise HousingError(f"Invalid charge type: {charge_type}")
        amount = Decimal(str(data.get("amount") or 0))
        if amount <= 0:
            raise HousingError("Charge amount must be positive.")
        return LeaseCharge.objects.create(
            tenant_id=lease.tenant_id,
            lease=lease,
            branch_id=lease.branch_id,
            charge_type=charge_type,
            status=LeaseCharge.STATUS_PENDING,
            description=description,
            amount=amount,
            period_start=_as_date(data.get("period_start")),
            period_end=_as_date(data.get("period_end")),
            due_date=_as_date(data.get("due_date")) or timezone.localdate(),
            created_by=user,
        )

    @staticmethod
    @transaction.atomic
    def post_rent_charge(*, lease: Lease, user=None, period_start=None, period_end=None):
        if lease.status != Lease.STATUS_ACTIVE:
            raise HousingError("Rent can only be posted on active leases.")
        start = _as_date(period_start) or timezone.localdate().replace(day=1)
        if period_end:
            end = _as_date(period_end)
        else:
            # end of month-ish: start + ~1 month - 1 day
            if start.month == 12:
                end = date(start.year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(start.year, start.month + 1, 1) - timedelta(days=1)
        return HousingService.add_charge(
            lease=lease,
            data={
                "charge_type": LeaseCharge.TYPE_RENT,
                "description": f"Rent {start.isoformat()} → {end.isoformat()} · {lease.unit.code}",
                "amount": lease.rent_amount,
                "period_start": start,
                "period_end": end,
                "due_date": start,
            },
            user=user,
        )

    @staticmethod
    @transaction.atomic
    def invoice_charge(
        *,
        charge: LeaseCharge,
        payment_method: str = "on_account",
        payment_reference: str = "",
        user=None,
    ) -> LeaseCharge:
        from apps.property_management.services.rental_billing_service import (
            RentalBillingError,
            RentalBillingService,
        )

        lease = charge.lease
        tenant = lease.housing_tenant
        try:
            customer = RentalBillingService.ensure_customer(
                tenant_id=charge.tenant_id,
                branch=charge.branch,
                full_name=tenant.full_name,
                phone=tenant.phone or "",
                email=tenant.email or "",
                code_prefix="HSG",
                existing_customer=tenant.customer,
                user=user,
            )
            if not tenant.customer_id:
                tenant.customer = customer
                tenant.updated_by = user
                tenant.save(update_fields=["customer", "updated_by", "updated_at"])
            product = RentalBillingService.ensure_service_product(
                tenant_id=charge.tenant_id,
                sku="housing-rent",
                name="Housing Rent",
                category_name="Housing Rental",
                user=user,
            )
            RentalBillingService.create_invoice_for_charge(
                charge=charge,
                customer=customer,
                branch=charge.branch,
                product=product,
                vertical="housing",
                payment_method=payment_method,
                payment_reference=payment_reference,
                lease_label=lease.lease_number,
                user=user,
            )
        except RentalBillingError as exc:
            raise HousingError(str(exc)) from exc

        charge.refresh_from_db()
        if charge.charge_type == LeaseCharge.TYPE_DEPOSIT and charge.status == LeaseCharge.STATUS_PAID:
            lease.deposit_held = True
            lease.updated_by = user
            lease.save(update_fields=["deposit_held", "updated_by", "updated_at"])
        return charge

    @staticmethod
    @transaction.atomic
    def collect_charge(
        *,
        charge: LeaseCharge,
        payment_method: str = "cash",
        payment_reference: str = "",
        user=None,
    ) -> LeaseCharge:
        from apps.property_management.services.rental_billing_service import (
            RentalBillingError,
            RentalBillingService,
        )

        try:
            if charge.status == LeaseCharge.STATUS_PENDING:
                return HousingService.invoice_charge(
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
            raise HousingError(str(exc)) from exc

        charge.refresh_from_db()
        if charge.charge_type == LeaseCharge.TYPE_DEPOSIT and charge.status == LeaseCharge.STATUS_PAID:
            lease = charge.lease
            lease.deposit_held = True
            lease.updated_by = user
            lease.save(update_fields=["deposit_held", "updated_by", "updated_at"])
        return charge

    @staticmethod
    @transaction.atomic
    def mark_charge_paid(*, charge: LeaseCharge, user=None, data=None) -> LeaseCharge:
        """Collect payment (creates invoice if needed) — no silent status flip."""
        data = data or {}
        return HousingService.collect_charge(
            charge=charge,
            payment_method=data.get("payment_method") or "cash",
            payment_reference=(data.get("payment_reference") or "").strip(),
            user=user,
        )
