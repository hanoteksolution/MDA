from django.db import transaction

from apps.settings_app.models import Branch, Company, Setting


class BranchService:
    @staticmethod
    def list_branches(*, is_active=None):
        qs = Branch.active_objects().select_related("company")
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs

    @staticmethod
    @transaction.atomic
    def create_branch(*, data, created_by=None):
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

    @staticmethod
    @transaction.atomic
    def update_company_profile(*, data, user=None):
        company = Company.active_objects().first()
        if not company:
            company = Company.objects.create(name=data.get("name", "My Company"), created_by=user)
        for key, value in data.items():
            setattr(company, key, value)
        company.updated_by = user
        company.save()
        return company
