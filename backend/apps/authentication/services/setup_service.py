from django.db import transaction

from apps.authentication.models import Role, User
from apps.inventory.models import Warehouse
from apps.platform.services.platform_service import PlatformService
from apps.settings_app.models import Branch, Company


class SetupService:
    @staticmethod
    def needs_setup() -> bool:
        return not User.objects.filter(deleted_at__isnull=True).exists()

    @staticmethod
    @transaction.atomic
    def complete_setup(*, company_data: dict, user_data: dict, branch_data: dict | None = None):
        if not SetupService.needs_setup():
            raise ValueError("Setup has already been completed.")

        company = Company.objects.create(
            name=company_data.get("name", "My Company"),
            legal_name=company_data.get("legal_name", ""),
            tax_id=company_data.get("tax_id", ""),
            email=company_data.get("email", ""),
            phone=company_data.get("phone", ""),
            address=company_data.get("address", ""),
        )
        PlatformService.create_tenant_for_company(
            company=company,
            contact_email=company_data.get("email", ""),
        )

        branch_defaults = branch_data or {}
        branch = Branch.objects.create(
            company=company,
            name=branch_defaults.get("name", "Main Branch"),
            code=branch_defaults.get("code", "BR01"),
            address=branch_defaults.get("address", company.address),
            phone=branch_defaults.get("phone", company.phone),
            email=branch_defaults.get("email", company.email),
            is_default=True,
            is_active=True,
        )

        Warehouse.objects.create(
            branch=branch,
            code="WH01",
            name="Main Warehouse",
            is_default=True,
            is_active=True,
        )

        admin_role = Role.objects.get(slug="super_admin")
        password = user_data.pop("password")
        user = User.objects.create_user(
            **user_data,
            password=password,
            role=admin_role,
            branch=branch,
            tenant=company.tenant,
            is_staff=True,
            is_superuser=True,
            is_platform_admin=True,
        )
        return user, company, branch
