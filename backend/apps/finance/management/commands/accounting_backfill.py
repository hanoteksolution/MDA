"""Backfill missing accounting journals for a tenant.

Examples:
  python manage.py accounting_backfill --tenant=acme --dry-run
  python manage.py accounting_backfill --tenant=acme --commit --before=2026-09-01
"""

from django.core.management.base import BaseCommand, CommandError

from apps.finance.services.backfill_service import AccountingBackfillService, BackfillError
from apps.platform.models import Tenant


class Command(BaseCommand):
    help = "Preview or commit historical GL backfill for a tenant"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            required=True,
            help="Tenant slug or UUID",
        )
        parser.add_argument(
            "--before",
            default=None,
            help="Only documents before this date (YYYY-MM-DD). Defaults to accounting_cutover_date.",
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Actually post journals (default is dry-run).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=500,
            help="Max documents per type (default 500).",
        )
        parser.add_argument("--skip-invoices", action="store_true")
        parser.add_argument("--skip-expenses", action="store_true")
        parser.add_argument("--skip-purchases", action="store_true")

    def handle(self, *args, **options):
        key = options["tenant"]
        tenant = Tenant.objects.filter(deleted_at__isnull=True, slug=key).first()
        if tenant is None:
            tenant = Tenant.objects.filter(deleted_at__isnull=True, pk=key).first()
        if tenant is None:
            raise CommandError(f"Tenant not found: {key}")

        dry_run = not options["commit"]
        try:
            result = AccountingBackfillService.run(
                tenant_id=tenant.id,
                before_date=options["before"],
                dry_run=dry_run,
                limit=options["limit"],
                include_invoices=not options["skip_invoices"],
                include_expenses=not options["skip_expenses"],
                include_purchases=not options["skip_purchases"],
            )
        except BackfillError as exc:
            raise CommandError(str(exc)) from exc

        if dry_run:
            counts = result["counts"]
            self.stdout.write(
                self.style.WARNING(
                    f"DRY-RUN tenant={tenant.slug} before={result['before_date']} "
                    f"missing total={counts['total']} "
                    f"(invoices={counts['invoices']} expenses={counts['expenses']} "
                    f"POs={counts['purchase_orders']})"
                )
            )
            for kind, rows in result["missing"].items():
                for row in rows[:10]:
                    self.stdout.write(f"  {kind}: {row}")
                if len(rows) > 10:
                    self.stdout.write(f"  … +{len(rows) - 10} more {kind}")
            self.stdout.write("Re-run with --commit to post journals.")
            return

        posted = result["posted"]
        self.stdout.write(
            self.style.SUCCESS(
                f"COMMITTED tenant={tenant.slug} "
                f"invoices={posted['invoices']} expenses={posted['expenses']} "
                f"POs={posted['purchase_orders']} errors={len(posted['errors'])}"
            )
        )
        for err in posted["errors"][:20]:
            self.stdout.write(self.style.ERROR(f"  {err}"))
