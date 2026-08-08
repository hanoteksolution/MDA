"""Run accounting health scan (same as Celery beat job).

  python manage.py accounting_health_scan
"""

from django.core.management.base import BaseCommand

from apps.finance.tasks.accounting_alerts import scan_accounting_health


class Command(BaseCommand):
    help = "Scan accounting health for all tenants and notify on issues"

    def handle(self, *args, **options):
        result = scan_accounting_health()
        self.stdout.write(
            self.style.SUCCESS(
                f"Scanned {result['tenants_scanned']} tenant(s); "
                f"{result['tenants_with_issues']} with issues; "
                f"{result['notifications_created']} notification(s)."
            )
        )
        if result["critical_tenants"]:
            self.stdout.write(
                self.style.ERROR(
                    f"Critical: {', '.join(result['critical_tenants'])}"
                )
            )
