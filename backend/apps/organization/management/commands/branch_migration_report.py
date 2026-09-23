"""Read-only validation of the multi-branch backfill.

Reports per check: total / resolved / unresolved / skipped / ambiguous /
review-required, and never modifies data. Checks whose columns do not exist yet
(later migration waves) are reported as SKIPPED rather than crashing, so the same
command is usable from Phase 2 onwards.

    python3 manage.py branch_migration_report [--tenant <slug-or-id>] [--json]
"""

from __future__ import annotations

import json
import uuid

from django.core.management.base import BaseCommand
from django.db.models import Count, F, Q


def _looks_like_uuid(value) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


STATUS_OK = "OK"
STATUS_REVIEW = "REVIEW_REQUIRED"
STATUS_SKIPPED = "SKIPPED"
STATUS_INFO = "INFO"


def _has_field(model, name: str) -> bool:
    return any(f.name == name for f in model._meta.get_fields())


class Check:
    def __init__(self, key, description):
        self.key = key
        self.description = description
        self.total = 0
        self.resolved = 0
        self.unresolved = 0
        self.skipped = 0
        self.ambiguous = 0
        self.review_required = 0
        self.status = STATUS_OK
        self.details: list[str] = []

    def as_dict(self):
        return {
            "check": self.key,
            "description": self.description,
            "status": self.status,
            "total": self.total,
            "resolved": self.resolved,
            "unresolved": self.unresolved,
            "skipped": self.skipped,
            "ambiguous": self.ambiguous,
            "review_required": self.review_required,
            "details": self.details,
        }


class Command(BaseCommand):
    help = "Validate the multi-branch migration/backfill. Read-only."

    def add_arguments(self, parser):
        parser.add_argument("--tenant", dest="tenant", default=None)
        parser.add_argument("--json", dest="as_json", action="store_true")

    def handle(self, *args, **options):
        tenant_filter = options.get("tenant")
        checks = []
        checks.extend(self._tenant_checks(tenant_filter))
        checks.extend(self._branch_checks(tenant_filter))
        checks.extend(self._warehouse_checks(tenant_filter))
        checks.extend(self._access_checks(tenant_filter))
        checks.extend(self._ledger_checks(tenant_filter))
        checks.extend(self._pos_checks(tenant_filter))
        checks.extend(self._finance_checks(tenant_filter))

        payload = {
            "checks": [c.as_dict() for c in checks],
            "review_required_total": sum(c.review_required for c in checks),
            "unresolved_total": sum(c.unresolved for c in checks),
            "clean": all(c.status in (STATUS_OK, STATUS_SKIPPED, STATUS_INFO) for c in checks),
        }

        if options.get("as_json"):
            self.stdout.write(json.dumps(payload, indent=2, default=str))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("Branch migration report"))
        for check in checks:
            style = self.style.SUCCESS
            if check.status == STATUS_REVIEW:
                style = self.style.WARNING
            elif check.status == STATUS_SKIPPED:
                style = self.style.NOTICE
            self.stdout.write(
                style(
                    f"[{check.status:<16}] {check.key:<34} "
                    f"total={check.total} resolved={check.resolved} "
                    f"unresolved={check.unresolved} skipped={check.skipped} "
                    f"ambiguous={check.ambiguous} review={check.review_required}"
                )
            )
            for detail in check.details[:25]:
                self.stdout.write(f"                     - {detail}")
            if len(check.details) > 25:
                self.stdout.write(f"                     ... {len(check.details) - 25} more")
        self.stdout.write("")
        self.stdout.write(
            f"unresolved_total={payload['unresolved_total']} "
            f"review_required_total={payload['review_required_total']} "
            f"clean={payload['clean']}"
        )

    # ------------------------------------------------------------------ #

    def _tenants(self, tenant_filter):
        from apps.platform.models import Tenant

        qs = Tenant.objects.all()
        if tenant_filter:
            # --tenant accepts a slug or a UUID pk. Only probe pk when the value can
            # actually be one — Q(pk=...) otherwise raises before the OR is evaluated,
            # since Django validates the UUID field eagerly.
            condition = Q(slug=tenant_filter)
            if _looks_like_uuid(tenant_filter):
                condition |= Q(pk=tenant_filter)
            qs = qs.filter(condition)
        return qs

    def _tenant_checks(self, tenant_filter):
        from apps.settings_app.models import Branch, Company

        check = Check("tenant.company_present", "Tenants skipped for having no Company")
        review = Check(
            "tenant.branch_data_without_company",
            "Tenants with branch-dependent data but no Company",
        )
        for tenant in self._tenants(tenant_filter):
            check.total += 1
            has_company = Company.objects.filter(
                tenant_id=tenant.pk, deleted_at__isnull=True
            ).exists()
            if has_company:
                check.resolved += 1
                continue
            check.skipped += 1
            check.details.append(f"{tenant.slug}: no Company — skipped, remediation: create a Company")
            review.total += 1
            if Branch.objects.filter(tenant_id=tenant.pk, deleted_at__isnull=True).exists():
                review.review_required += 1
                review.status = STATUS_REVIEW
                review.details.append(
                    f"{tenant.slug}: has Branch rows without a Company — REVIEW_REQUIRED"
                )
        return [check, review]

    def _branch_checks(self, tenant_filter):
        from apps.settings_app.models import Branch

        default_check = Check("branch.default_per_tenant", "Exactly one default branch per tenant")
        status_check = Check("branch.status_consistent", "Branch.status agrees with is_active")

        rows = (
            Branch.objects.filter(deleted_at__isnull=True, tenant__isnull=False)
            .values("tenant_id")
            .annotate(
                total=Count("pk"),
                defaults=Count("pk", filter=Q(is_default=True)),
            )
        )
        if tenant_filter:
            tenant_ids = list(self._tenants(tenant_filter).values_list("pk", flat=True))
            rows = rows.filter(tenant_id__in=tenant_ids)
        for row in rows:
            default_check.total += 1
            if row["defaults"] == 1:
                default_check.resolved += 1
            elif row["defaults"] == 0:
                default_check.unresolved += 1
                default_check.status = STATUS_REVIEW
                default_check.details.append(f"tenant {row['tenant_id']}: no default branch")
            else:
                default_check.ambiguous += 1
                default_check.status = STATUS_REVIEW
                default_check.details.append(
                    f"tenant {row['tenant_id']}: {row['defaults']} default branches"
                )

        if _has_field(Branch, "status"):
            branches = Branch.objects.filter(deleted_at__isnull=True)
            status_check.total = branches.count()
            mismatched = branches.filter(
                Q(is_active=True, status__in=["INACTIVE", "ARCHIVED"])
                | Q(is_active=False, status="ACTIVE")
            )
            status_check.unresolved = mismatched.count()
            status_check.resolved = status_check.total - status_check.unresolved
            if status_check.unresolved:
                status_check.status = STATUS_REVIEW
                status_check.details = [
                    f"branch {b.code}: is_active={b.is_active} status={b.status}"
                    for b in mismatched[:25]
                ]
        else:
            status_check.status = STATUS_SKIPPED
            status_check.details.append("Branch.status not migrated yet")

        return [default_check, status_check]

    def _warehouse_checks(self, tenant_filter):
        from apps.inventory.models import Warehouse
        from apps.organization.models import StockLocation

        location_check = Check("warehouse.default_location", "Every warehouse has a default location")
        tenant_check = Check("warehouse.tenant_matches_branch", "Warehouse tenant matches its branch")

        warehouses = Warehouse.objects.filter(deleted_at__isnull=True).select_related("branch")
        if tenant_filter:
            tenant_ids = list(self._tenants(tenant_filter).values_list("pk", flat=True))
            warehouses = warehouses.filter(tenant_id__in=tenant_ids)

        for warehouse in warehouses:
            location_check.total += 1
            tenant_check.total += 1
            has_default = StockLocation.objects.filter(
                warehouse=warehouse, is_default=True, deleted_at__isnull=True
            ).exists()
            if has_default:
                location_check.resolved += 1
            else:
                location_check.unresolved += 1
                location_check.status = STATUS_REVIEW
                location_check.details.append(f"warehouse {warehouse.code}: no default location")

            branch_tenant = getattr(warehouse.branch, "tenant_id", None)
            if warehouse.tenant_id and branch_tenant and str(warehouse.tenant_id) != str(branch_tenant):
                tenant_check.review_required += 1
                tenant_check.status = STATUS_REVIEW
                tenant_check.details.append(
                    f"warehouse {warehouse.code}: tenant {warehouse.tenant_id} != branch tenant {branch_tenant}"
                )
            else:
                tenant_check.resolved += 1
        return [location_check, tenant_check]

    def _access_checks(self, tenant_filter):
        from apps.authentication.models import User
        from apps.organization.models import UserBranchAccess

        check = Check("access.user_branch_backfilled", "Users with a legacy branch have access rows")
        default_check = Check("access.single_default", "At most one default branch access per user")

        users = User.objects.filter(deleted_at__isnull=True).exclude(branch__isnull=True)
        if tenant_filter:
            tenant_ids = list(self._tenants(tenant_filter).values_list("pk", flat=True))
            users = users.filter(tenant_id__in=tenant_ids)
        for user in users.only("id", "username", "branch_id"):
            check.total += 1
            if UserBranchAccess.objects.filter(
                user_id=user.pk, branch_id=user.branch_id, deleted_at__isnull=True
            ).exists():
                check.resolved += 1
            else:
                check.unresolved += 1
                check.status = STATUS_REVIEW
                check.details.append(f"user {user.username}: legacy branch has no UserBranchAccess row")

        dupes = (
            UserBranchAccess.objects.filter(deleted_at__isnull=True, is_default=True)
            .values("user_id")
            .annotate(n=Count("pk"))
            .filter(n__gt=1)
        )
        default_check.total = UserBranchAccess.objects.filter(deleted_at__isnull=True).count()
        for row in dupes:
            default_check.ambiguous += 1
            default_check.status = STATUS_REVIEW
            default_check.details.append(f"user {row['user_id']}: {row['n']} default branches")
        default_check.resolved = default_check.total - default_check.ambiguous
        return [check, default_check]

    def _ledger_checks(self, tenant_filter):
        from apps.inventory.models import InventoryTransaction, StockMovement

        movement_check = Check(
            "ledger.movement_branch", "StockMovement.branch matches warehouse.branch"
        )
        if not _has_field(StockMovement, "branch"):
            movement_check.status = STATUS_SKIPPED
            movement_check.details.append("StockMovement.branch arrives in migration wave M2 (Phase 3)")
            return [movement_check]

        movements = StockMovement.objects.filter(deleted_at__isnull=True)
        movement_check.total = movements.count()
        movement_check.unresolved = movements.filter(branch__isnull=True).count()
        mismatched = movements.exclude(branch__isnull=True).exclude(
            branch_id=models_F_warehouse_branch()
        ).count()
        movement_check.ambiguous = mismatched
        movement_check.resolved = movement_check.total - movement_check.unresolved - mismatched
        if movement_check.unresolved or mismatched:
            movement_check.status = STATUS_REVIEW

        txn_check = Check(
            "ledger.transaction_branch",
            "InventoryTransaction.branch matches inventory.warehouse.branch",
        )
        transactions = InventoryTransaction.objects.filter(deleted_at__isnull=True)
        txn_check.total = transactions.count()
        txn_check.unresolved = transactions.filter(branch__isnull=True).count()
        txn_mismatched = transactions.exclude(branch__isnull=True).exclude(
            branch_id=F("inventory__warehouse__branch_id")
        ).count()
        txn_check.ambiguous = txn_mismatched
        txn_check.resolved = txn_check.total - txn_check.unresolved - txn_mismatched
        if txn_check.unresolved or txn_mismatched:
            txn_check.status = STATUS_REVIEW

        return [movement_check, txn_check]

    def _finance_checks(self, tenant_filter):
        from apps.finance.models import JournalEntry

        check = Check("finance.entry_branch", "Journal entries without a branch (Unassigned bucket)")
        entries = JournalEntry.objects.all()
        check.total = entries.count()
        check.unresolved = entries.filter(branch__isnull=True).count()
        check.resolved = check.total - check.unresolved
        # Unassigned is an accepted, documented outcome (Open Question 3), not a failure.
        check.status = STATUS_INFO if check.unresolved else STATUS_OK
        if check.unresolved:
            check.details.append(
                f"{check.unresolved} entries report as 'Unassigned'; company totals still reconcile"
            )

        line_check = Check(
            "finance.line_branch",
            "JournalLine.branch is set wherever the entry has a branch; unassigned lines counted",
        )
        from apps.finance.models import JournalLine

        lines = JournalLine.objects.all()
        line_check.total = lines.count()
        line_check.unresolved = lines.filter(
            branch__isnull=True, entry__branch__isnull=False
        ).count()
        unassigned = lines.filter(entry__branch__isnull=True, branch__isnull=True).count()
        line_check.resolved = line_check.total - line_check.unresolved - unassigned
        line_check.skipped = unassigned
        if line_check.unresolved:
            line_check.status = STATUS_REVIEW
        if unassigned:
            line_check.details.append(f"{unassigned} lines are Unassigned (entry has no branch)")
        return [check, line_check]

    def _pos_checks(self, tenant_filter):
        from apps.sales.models import CashierSession, Invoice

        check = Check(
            "pos.session_terminal", "CashierSession on a POS-active branch has a terminal"
        )
        sessions = CashierSession.objects.filter(deleted_at__isnull=True)
        check.total = sessions.count()
        check.unresolved = sessions.filter(terminal__isnull=True).count()
        check.resolved = check.total - check.unresolved
        if check.unresolved:
            check.status = STATUS_REVIEW
            check.details.append(
                f"{check.unresolved} sessions have no terminal (extra concurrent open shifts "
                "or legacy rows); close or reassign them"
            )
        branches_with_invoices = set(
            Invoice.objects.filter(deleted_at__isnull=True).values_list("branch_id", flat=True)
        )
        from apps.organization.models import PosTerminal

        with_terminal = set(
            PosTerminal.objects.filter(deleted_at__isnull=True).values_list("branch_id", flat=True)
        )
        missing = branches_with_invoices - with_terminal
        terminal_check = Check(
            "pos.branch_terminal", "Branches with sales history have at least one terminal"
        )
        terminal_check.total = len(branches_with_invoices)
        terminal_check.unresolved = len(missing)
        terminal_check.resolved = terminal_check.total - terminal_check.unresolved
        if missing:
            # Legacy mode (no terminal configured) is valid and unenforced — informational.
            terminal_check.status = STATUS_INFO
            terminal_check.details.append(
                f"{len(missing)} branches have sales but no terminal (POS not enforced there)"
            )
        return [check, terminal_check]


def models_F_warehouse_branch():
    from django.db.models import F

    return F("warehouse__branch_id")
