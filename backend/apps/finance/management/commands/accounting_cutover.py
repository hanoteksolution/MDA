"""Prepare / activate / inspect per-tenant accounting cutover.

Examples:
  python manage.py accounting_cutover --tenant=acme --status
  python manage.py accounting_cutover --tenant=acme --prepare
  python manage.py accounting_cutover --tenant=acme --activate --date=2026-09-01
  python manage.py accounting_cutover --tenant=acme --disable-posting
"""

from django.core.management.base import BaseCommand, CommandError

from apps.finance.services.cutover_service import AccountingCutoverService, CutoverError
from apps.platform.models import Tenant


class Command(BaseCommand):
    help = "Accounting cutover prepare / activate / status for a tenant"

    def add_arguments(self, parser):
        parser.add_argument("--tenant", required=True, help="Tenant slug or UUID")
        parser.add_argument("--status", action="store_true", help="Show cutover readiness")
        parser.add_argument("--prepare", action="store_true", help="Seed CoA, mappings, periods")
        parser.add_argument(
            "--activate",
            action="store_true",
            help="Set cutover date and enable posting (fails if critical health errors)",
        )
        parser.add_argument(
            "--date",
            default=None,
            help="Cutover date YYYY-MM-DD (default today, with --activate)",
        )
        parser.add_argument(
            "--disable-posting",
            action="store_true",
            help="Pilot rollback: disable CAE posting for this tenant",
        )

    def handle(self, *args, **options):
        key = options["tenant"]
        tenant = Tenant.objects.filter(deleted_at__isnull=True, slug=key).first()
        if tenant is None:
            tenant = Tenant.objects.filter(deleted_at__isnull=True, pk=key).first()
        if tenant is None:
            raise CommandError(f"Tenant not found: {key}")

        actions = [
            options["status"],
            options["prepare"],
            options["activate"],
            options["disable_posting"],
        ]
        if sum(1 for a in actions if a) != 1:
            # default to status
            if not any(actions):
                options["status"] = True
            else:
                raise CommandError(
                    "Choose one of: --status, --prepare, --activate, --disable-posting"
                )

        try:
            if options["prepare"]:
                data = AccountingCutoverService.prepare(tenant_id=tenant.id)
                self.stdout.write(self.style.SUCCESS("Prepared."))
            elif options["activate"]:
                data = AccountingCutoverService.activate(
                    tenant_id=tenant.id, cutover_date=options["date"]
                )
                self.stdout.write(self.style.SUCCESS("Cutover activated."))
            elif options["disable_posting"]:
                data = AccountingCutoverService.disable_posting(tenant_id=tenant.id)
                self.stdout.write(self.style.WARNING("Posting disabled for tenant."))
            else:
                data = AccountingCutoverService.status(tenant_id=tenant.id)
        except CutoverError as exc:
            raise CommandError(str(exc)) from exc

        for key, value in data.items():
            self.stdout.write(f"  {key}: {value}")
