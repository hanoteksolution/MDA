"""Re-runnable branch backfill (migration plan §4.1 – §4.3).

The wave-M1 data migrations call the same functions, so running this on a database
that has already migrated is a safe no-op. Use ``--dry-run`` to see the counts
without writing.

    python3 manage.py backfill_branch_access [--dry-run] [--json]
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.organization.services.backfill_service import run_all


class Command(BaseCommand):
    help = "Backfill default branches, warehouse stock locations and user branch access."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", dest="dry_run", action="store_true")
        parser.add_argument("--json", dest="as_json", action="store_true")

    def handle(self, *args, **options):
        dry_run = options.get("dry_run")

        with transaction.atomic():
            results = run_all()
            if dry_run:
                transaction.set_rollback(True)

        payload = {
            "dry_run": bool(dry_run),
            "results": [r.as_dict() for r in results],
            "review_required_total": sum(r.review_required for r in results),
            "unresolved_total": sum(r.unresolved for r in results),
        }

        if options.get("as_json"):
            self.stdout.write(json.dumps(payload, indent=2, default=str))
            return

        if options.get("verbosity", 1) == 0:
            return

        header = "Branch backfill (dry run)" if dry_run else "Branch backfill"
        self.stdout.write(self.style.MIGRATE_HEADING(header))
        for result in results:
            style = self.style.WARNING if result.review_required or result.unresolved else self.style.SUCCESS
            self.stdout.write(style(str(result)))
            for detail in result.details[:25]:
                self.stdout.write(f"  - {detail}")
            if len(result.details) > 25:
                self.stdout.write(f"  ... {len(result.details) - 25} more")
        self.stdout.write("")
        self.stdout.write(
            f"unresolved_total={payload['unresolved_total']} "
            f"review_required_total={payload['review_required_total']}"
        )
        if payload["review_required_total"]:
            self.stdout.write(
                self.style.WARNING(
                    "Rows flagged REVIEW_REQUIRED were NOT changed. Resolve them manually."
                )
            )
