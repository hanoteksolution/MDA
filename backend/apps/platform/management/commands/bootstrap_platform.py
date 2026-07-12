from django.core.management.base import BaseCommand

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.platform.services.platform_service import PlatformService
from apps.settings_app.models import Company


class Command(BaseCommand):
    help = "Link existing companies to tenants and ensure subscription plans exist"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-role-permissions",
            action="store_true",
            help="Wipe system roles back to built-in defaults (destroys custom Admin changes).",
        )

    def handle(self, *args, **options):
        bootstrap_roles_and_permissions(
            stdout=self.stdout,
            reset_role_permissions=options["reset_role_permissions"],
        )
        PlatformService.ensure_default_plans()
        PlatformService.ensure_subscription_payment_assets()
        linked = 0
        for company in Company.active_objects().filter(tenant__isnull=True):
            PlatformService.create_tenant_for_company(company=company, contact_email=company.email)
            linked += 1
        self.stdout.write(self.style.SUCCESS(f"Platform bootstrap done. Linked {linked} companies."))
