"""Re-runnable ledger backfill (migration plan §4.4 / M2, Phase 3).

The wave-M2 data migration (`inventory/0005_backfill_ledger_branch`) calls the same
function, so running this on an already-migrated database is a safe no-op.

    python3 manage.py backfill_ledger_branch [--dry-run] [--json]
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.organization.services.backfill_service import backfill_ledger_branch


class Command(BaseCommand):
    help = "Backfill StockMovement.branch and InventoryTransaction.branch from warehouse.branch."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", dest="dry_run", action="store_true")
        parser.add_argument("--json", dest="as_json", action="store_true")

    def handle(self, *args, **options):
        dry_run = options.get("dry_run")

        with transaction.atomic():
            result = backfill_ledger_branch()
            if dry_run:
                transaction.set_rollback(True)

        payload = {"dry_run": bool(dry_run), "result": result.as_dict()}

        if options.get("as_json"):
            self.stdout.write(json.dumps(payload, indent=2, default=str))
            return

        if options.get("verbosity", 1) == 0:
            return

        header = "Ledger branch backfill (dry run)" if dry_run else "Ledger branch backfill"
        style = self.style.WARNING if result.unresolved else self.style.SUCCESS
        self.stdout.write(self.style.MIGRATE_HEADING(header))
        self.stdout.write(style(str(result)))
        for detail in result.details[:25]:
            self.stdout.write(f"  - {detail}")
