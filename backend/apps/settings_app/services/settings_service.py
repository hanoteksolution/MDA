from django.db import transaction

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
    def create_branch(*, data, created_by=None):
        if "company_id" not in data or not data.get("company_id"):
            company_id = getattr(getattr(created_by, "branch", None), "company_id", None)
            if not company_id:
                company = Company.active_objects().first()
                company_id = company.id if company else None
            if not company_id:
                raise ValueError("No company available for this branch.")
            data = {**data, "company_id": company_id}
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
    def get_company_profile():
        company = Company.active_objects().first()
        return company

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
    def update_company_profile(*, data, user=None):
        company = Company.active_objects().first()
        if not company:
            company = Company.objects.create(name=data.get("name", "My Company"), created_by=user)
        for key in SettingsService.ALLOWED_COMPANY_FIELDS:
            if key in data:
                setattr(company, key, data[key] if data[key] is not None else "")
        company.updated_by = user
        company.save()
        return company
