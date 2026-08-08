"""Gym member CRUD (STEP 14)."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.audit.services import write_audit
from apps.customers.models import Customer
from apps.gym.models import Member
from apps.settings_app.models import Branch
from core.tenancy import apply_tenant_scope, resolve_acting_tenant, stamp_tenant_id


class MemberError(ValueError):
    pass


class MemberService:
    _WRITABLE = (
        "membership_number",
        "full_name",
        "email",
        "phone",
        "date_of_birth",
        "gender",
        "address",
        "emergency_contact_name",
        "emergency_contact_phone",
        "status",
        "joined_at",
        "notes",
        "photo_url",
        "customer_id",
        "branch_id",
    )

    @staticmethod
    def list(*, search=None, status=None, branch_id=None, user=None, request=None):
        qs = Member.active_objects().select_related("customer", "branch")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if status:
            qs = qs.filter(status=status)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if search:
            qs = qs.filter(
                Q(full_name__icontains=search)
                | Q(membership_number__icontains=search)
                | Q(phone__icontains=search)
                | Q(email__icontains=search)
            )
        return qs.order_by("full_name")

    @staticmethod
    def get(*, pk, user=None, request=None):
        return MemberService.list(user=user, request=request).get(pk=pk)

    @staticmethod
    def summary(*, user=None, request=None):
        qs = apply_tenant_scope(Member.active_objects(), user=user, request=request)
        by_status = {
            row["status"]: row["c"]
            for row in qs.values("status").annotate(c=Count("id"))
        }
        return {
            "total": qs.count(),
            "active": by_status.get(Member.STATUS_ACTIVE, 0),
            "inactive": by_status.get(Member.STATUS_INACTIVE, 0),
            "suspended": by_status.get(Member.STATUS_SUSPENDED, 0),
        }

    @staticmethod
    def serialize(member: Member) -> dict:
        return {
            "id": str(member.id),
            "membership_number": member.membership_number,
            "full_name": member.full_name,
            "email": member.email or "",
            "phone": member.phone or "",
            "date_of_birth": member.date_of_birth.isoformat() if member.date_of_birth else None,
            "gender": member.gender or "",
            "address": member.address or "",
            "emergency_contact_name": member.emergency_contact_name or "",
            "emergency_contact_phone": member.emergency_contact_phone or "",
            "status": member.status,
            "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            "notes": member.notes or "",
            "photo_url": member.photo_url or "",
            "customer_id": str(member.customer_id) if member.customer_id else None,
            "customer_name": member.customer.full_name if member.customer_id else None,
            "branch_id": str(member.branch_id) if member.branch_id else None,
            "branch_name": member.branch.name if member.branch_id else None,
            "created_at": member.created_at.isoformat() if member.created_at else None,
        }

    @staticmethod
    def _next_membership_number(*, tenant_id) -> str:
        prefix = "MEM"
        count = Member.objects.filter(tenant_id=tenant_id).count() + 1
        candidate = f"{prefix}-{count:05d}"
        while Member.active_objects().filter(
            tenant_id=tenant_id, membership_number=candidate
        ).exists():
            count += 1
            candidate = f"{prefix}-{count:05d}"
        return candidate

    @staticmethod
    def _prepare(data, *, for_create: bool, user=None, request=None, member=None) -> dict:
        prepared = {}
        for key in MemberService._WRITABLE:
            if key not in data:
                continue
            value = data.get(key)
            if key in ("customer_id", "branch_id") and value in ("", None):
                prepared[key] = None
            elif key in ("date_of_birth", "joined_at") and value in ("", None):
                prepared[key] = None
            elif key == "membership_number" and isinstance(value, str):
                prepared[key] = value.strip()
            elif key == "full_name" and isinstance(value, str):
                prepared[key] = value.strip()
            else:
                prepared[key] = value

        if for_create:
            if data.get("tenant_id") and "tenant_id" not in prepared:
                prepared["tenant_id"] = data["tenant_id"]
            if data.get("tenant") and "tenant" not in prepared:
                prepared["tenant"] = data["tenant"]
            prepared = stamp_tenant_id(prepared, user=user, request=request)
            if not prepared.get("membership_number"):
                tenant = resolve_acting_tenant(user=user, request=request)
                tenant_id = prepared.get("tenant_id") or prepared.get("tenant")
                if hasattr(tenant_id, "pk"):
                    tenant_id = tenant_id.pk
                if tenant_id is None and tenant is not None:
                    tenant_id = tenant.pk
                if tenant_id is None:
                    raise MemberError("Tenant is required to create a member.")
                prepared["membership_number"] = MemberService._next_membership_number(
                    tenant_id=tenant_id
                )
            if not prepared.get("joined_at"):
                prepared["joined_at"] = timezone.localdate()
            if not prepared.get("status"):
                prepared["status"] = Member.STATUS_ACTIVE

        if for_create and not prepared.get("full_name"):
            raise MemberError("Full name is required.")
        if "full_name" in prepared and not prepared["full_name"]:
            raise MemberError("Full name is required.")

        # Validate optional FKs are in tenant scope
        tenant = resolve_acting_tenant(user=user, request=request)
        tenant_id = None
        if tenant is not None:
            tenant_id = tenant.pk
        elif prepared.get("tenant"):
            t = prepared["tenant"]
            tenant_id = getattr(t, "pk", t)
        elif prepared.get("tenant_id"):
            tenant_id = prepared["tenant_id"]
        elif member is not None:
            tenant_id = member.tenant_id

        if prepared.get("customer_id"):
            cqs = Customer.active_objects().filter(pk=prepared["customer_id"])
            if tenant_id:
                cqs = cqs.filter(tenant_id=tenant_id)
            if not cqs.exists():
                raise MemberError("Customer not found for this tenant.")

        if prepared.get("branch_id"):
            bqs = Branch.active_objects().filter(pk=prepared["branch_id"])
            if tenant_id:
                bqs = bqs.filter(tenant_id=tenant_id)
            if not bqs.exists():
                raise MemberError("Branch not found for this tenant.")

        valid_status = {c[0] for c in Member.STATUS_CHOICES}
        if prepared.get("status") and prepared["status"] not in valid_status:
            raise MemberError(f"Invalid status: {prepared['status']}")

        valid_gender = {c[0] for c in Member.GENDER_CHOICES} | {""}
        if "gender" in prepared and prepared["gender"] not in valid_gender:
            raise MemberError(f"Invalid gender: {prepared['gender']}")

        return prepared

    @staticmethod
    @transaction.atomic
    def create(*, data, user=None, request=None) -> Member:
        prepared = MemberService._prepare(
            data, for_create=True, user=user, request=request
        )
        # Uniqueness check
        tenant_id = prepared.get("tenant_id") or getattr(prepared.get("tenant"), "pk", None)
        number = prepared["membership_number"]
        if tenant_id and Member.active_objects().filter(
            tenant_id=tenant_id, membership_number=number
        ).exists():
            raise MemberError(f"Membership number '{number}' already exists.")
        member = Member.objects.create(**prepared, created_by=user)
        write_audit(
            action="create",
            module="gym",
            entity=member,
            user=user,
            request=request,
            new_values={"membership_number": member.membership_number},
        )
        return member

    @staticmethod
    @transaction.atomic
    def update(*, member: Member, data, user=None, request=None) -> Member:
        prepared = MemberService._prepare(
            data, for_create=False, user=user, request=request, member=member
        )
        prepared.pop("tenant_id", None)
        prepared.pop("tenant", None)
        if "membership_number" in prepared and prepared["membership_number"]:
            clash = (
                Member.active_objects()
                .filter(
                    tenant_id=member.tenant_id,
                    membership_number=prepared["membership_number"],
                )
                .exclude(pk=member.pk)
                .exists()
            )
            if clash:
                raise MemberError(
                    f"Membership number '{prepared['membership_number']}' already exists."
                )
        for key, value in prepared.items():
            setattr(member, key, value)
        member.updated_by = user
        member.save()
        write_audit(action="update", module="gym", entity=member, user=user, request=request)
        return member

    @staticmethod
    def soft_delete(*, member: Member, user=None, request=None) -> Member:
        member.soft_delete(user=user)
        write_audit(action="delete", module="gym", entity=member, user=user, request=request)
        return member
