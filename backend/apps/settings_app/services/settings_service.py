from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.audit.services.audit_write import write_audit
from apps.settings_app.models import Branch, Company, Setting


def _is_elevated(user) -> bool:
    if not user:
        return False
    if getattr(user, "is_platform_admin", False) or getattr(user, "is_superuser", False):
        return True
    role = getattr(user, "role", None)
    return bool(role and role.slug in ("super_admin", "platform_admin"))


class BranchService:
    @staticmethod
    def list_branches(*, user=None, is_active=None):
        qs = Branch.active_objects().select_related("company").order_by("company__name", "name", "created_at")
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        # Non-elevated users only see their own company's branches.
        # Elevated users see all (so they can clean up orphan shop branches).
        if user and not _is_elevated(user):
            company_id = getattr(getattr(user, "branch", None), "company_id", None)
            if company_id:
                qs = qs.filter(company_id=company_id)
        return qs

    @staticmethod
    @transaction.atomic
    def create_branch(*, data, created_by=None, request=None):
        from apps.platform.services.entitlement_service import EntitlementError, EntitlementService
        from core.tenancy import resolve_acting_tenant

        if "company_id" not in data or not data.get("company_id"):
            company_id = getattr(getattr(created_by, "branch", None), "company_id", None)
            if company_id and not Company.active_objects().filter(pk=company_id).exists():
                company_id = None
            if not company_id:
                acting_tenant = resolve_acting_tenant(request=request, user=created_by)
                if acting_tenant is not None:
                    company_id = SettingsService.ensure_company(tenant=acting_tenant, user=created_by).id
                else:
                    company = Company.active_objects().first()
                    company_id = company.id if company else None
            if not company_id:
                raise ValueError("No company available for this branch.")
            data = {**data, "company_id": company_id}

        company = Company.active_objects().filter(pk=data["company_id"]).first()
        if company is None:
            raise ValueError("Company profile not found.")
        tenant = company.tenant
        try:
            EntitlementService.assert_can_add_branch(tenant=tenant, user=created_by)
        except EntitlementError as exc:
            raise ValueError(str(exc)) from exc

        if tenant is not None:
            data = {**data, "tenant_id": tenant.pk}
        return Branch.objects.create(**data, created_by=created_by)

    @staticmethod
    @transaction.atomic
    def update_branch(*, branch, data, updated_by=None):
        for key, value in data.items():
            setattr(branch, key, value)
        branch.updated_by = updated_by
        branch.save()
        return branch

    @staticmethod
    @transaction.atomic
    def set_default(*, branch, updated_by=None):
        Branch.objects.filter(company=branch.company).update(is_default=False)
        branch.is_default = True
        branch.updated_by = updated_by
        branch.save(update_fields=["is_default", "updated_by", "updated_at"])
        return branch

    @staticmethod
    @transaction.atomic
    def archive_branch(*, branch, user=None, status=None):
        """Close a branch for trading. Refuses while a cashier session is still open.

        Archiving is reversible (set the status back) and is *not* a delete: the row
        stays so that every historical invoice, movement and journal line that points
        at it keeps resolving.
        """
        from apps.sales.models import CashierSession

        target_status = status or Branch.STATUS_ARCHIVED
        if target_status not in Branch.INACTIVE_STATUSES:
            raise ValidationError({"status": "Use set_default/update to re-activate a branch."})

        open_sessions = CashierSession.objects.filter(
            branch=branch, status=CashierSession.STATUS_OPEN, deleted_at__isnull=True
        ).count()
        if open_sessions:
            raise ValidationError(
                {
                    "detail": (
                        f"Cannot close this branch: {open_sessions} cashier session(s) are "
                        "still open. Close the tills first."
                    )
                }
            )

        old_status = branch.status
        branch.status = target_status
        branch.updated_by = user
        branch.save(update_fields=["status", "updated_by", "updated_at"])
        write_audit(
            action="update",
            module="branches",
            entity=branch,
            branch=branch,
            user=user,
            old_values={"status": old_status},
            new_values={"status": branch.status},
        )
        return branch

    @staticmethod
    @transaction.atomic
    def delete_branch(*, branch, user=None):
        """Soft-delete a branch. Refuses if it is the company's only branch (unless elevated orphan cleanup)."""
        siblings = list(
            Branch.active_objects().filter(company=branch.company).exclude(pk=branch.pk)
        )
        user_branch_id = getattr(user, "branch_id", None) if user else None

        if user_branch_id and str(user_branch_id) == str(branch.id) and not siblings:
            raise ValueError("Cannot delete the branch you are currently using.")

        if not siblings:
            if not _is_elevated(user):
                raise ValueError("Cannot delete the only branch for this company.")
            # Elevated cleanup of an unused shop/company branch
            from apps.inventory.models import Warehouse

            for wh in Warehouse.active_objects().filter(branch=branch):
                wh.soft_delete(user=user)
            branch.soft_delete(user=user)
            return None

        fallback = next((b for b in siblings if b.is_default), siblings[0])
        if branch.is_default or not any(b.is_default for b in siblings):
            Branch.objects.filter(company=branch.company).update(is_default=False)
            fallback.is_default = True
            fallback.save(update_fields=["is_default", "updated_at"])

        from apps.authentication.models import User

        User.objects.filter(branch=branch).update(branch=fallback)

        from apps.inventory.models import Warehouse

        for wh in Warehouse.active_objects().filter(branch=branch):
            wh.soft_delete(user=user)

        branch.soft_delete(user=user)
        return fallback


class SettingsService:
    @staticmethod
    def list_settings(*, category=None, branch=None, company=None):
        qs = Setting.active_objects().all()
        if category:
            qs = qs.filter(category=category)
        if branch:
            qs = qs.filter(branch=branch)
        if company:
            qs = qs.filter(company=company)
        return qs

    @staticmethod
    def get_by_key(*, key, branch=None, company=None):
        return Setting.active_objects().filter(
            key=key, branch=branch, company=company
        ).first()

    @staticmethod
    @transaction.atomic
    def upsert(*, key, value, category="general", branch=None, company=None, user=None):
        setting, _ = Setting.active_objects().get_or_create(
            key=key,
            branch=branch,
            company=company,
            defaults={"value": value, "category": category, "created_by": user},
        )
        setting.value = value
        setting.category = category
        setting.updated_by = user
        setting.save()
        return setting

    @staticmethod
    def get_company_profile(*, user=None, request=None):
        from core.tenancy import resolve_acting_tenant

        tenant = resolve_acting_tenant(request=request, user=user)
        qs = Company.active_objects().all()
        if tenant is not None:
            company = qs.filter(tenant_id=tenant.pk).order_by("created_at").first()
            if company is not None:
                return company
        # Prefer the company linked to the user's branch when host/tenant context is thin.
        branch = getattr(user, "branch", None) if user is not None else None
        if branch is not None and getattr(branch, "company_id", None):
            company = qs.filter(pk=branch.company_id).first()
            if company is not None:
                return company
        if tenant is not None:
            return None
        return qs.order_by("created_at").first()

    @staticmethod
    @transaction.atomic
    def ensure_company(*, tenant, user=None, name=None):
        """Return the tenant's active Company, reviving a soft-deleted one or creating it.

        A tenant's Company can be soft-deleted while its branches still reference it, which
        leaves the shop with no active profile. Reviving keeps those branches attached to it.
        """
        company = (
            Company.active_objects().filter(tenant_id=tenant.pk).order_by("created_at").first()
        )
        if company is not None:
            return company
        deleted = (
            Company.objects.filter(tenant_id=tenant.pk, deleted_at__isnull=False)
            .order_by("-deleted_at")
            .first()
        )
        if deleted is not None:
            deleted.restore()
            return deleted
        return Company.objects.create(
            name=name or getattr(tenant, "name", None) or "My Company",
            tenant_id=tenant.pk,
            created_by=user,
        )

    ALLOWED_COMPANY_FIELDS = (
        "name",
        "legal_name",
        "tax_id",
        "email",
        "phone",
        "address",
        "logo",
    )

    @staticmethod
    @transaction.atomic
    def update_company_profile(*, data, user=None, request=None):
        from core.tenancy import resolve_acting_tenant

        company = SettingsService.get_company_profile(user=user, request=request)
        tenant = resolve_acting_tenant(request=request, user=user)
        if not company:
            if tenant is not None:
                company = SettingsService.ensure_company(
                    tenant=tenant, user=user, name=data.get("name")
                )
            else:
                company = Company.objects.create(
                    name=(data.get("name") or "My Company"), created_by=user
                )
        elif company.tenant_id is None and tenant is not None:
            company.tenant_id = tenant.pk
        for key in SettingsService.ALLOWED_COMPANY_FIELDS:
            if key in data:
                setattr(company, key, data[key] if data[key] is not None else "")
        company.updated_by = user
        company.save()
        # Keep tenant display name aligned with company trading name when updated.
        if tenant is not None and "name" in data and (data.get("name") or "").strip():
            new_name = str(data["name"]).strip()
            if getattr(tenant, "name", None) != new_name:
                tenant.name = new_name
                update_fields = ["name"]
                if hasattr(tenant, "updated_at"):
                    from django.utils import timezone

                    tenant.updated_at = timezone.now()
                    update_fields.append("updated_at")
                tenant.save(update_fields=update_fields)
        return company
