"""Accounting integrity health checks — journals, events, sub-ledger reconcile."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from apps.finance.models import AccountingEvent, JournalEntry, JournalLine
from apps.finance.selectors.payables import PayablesAgingSelector
from apps.finance.selectors.receivables import ReceivablesAgingSelector
from apps.finance.services.chart_service import ChartService
from apps.finance.services.mapping_service import MappingService
from apps.inventory.models import Inventory
from apps.platform.models import TenantSettings
from apps.sales.models import Invoice
from core.tenancy import stamp_tenant_id


class AccountingHealthService:
    @staticmethod
    def check(*, user=None, request=None) -> dict:
        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id")
        checks = []
        warnings = 0
        errors = 0

        if not tenant_id:
            return {
                "status": "unknown",
                "checks": [{"id": "tenant", "ok": False, "message": "No tenant resolved."}],
                "summary": {"ok": 0, "warnings": 0, "errors": 1},
            }

        ChartService.ensure_default_chart(tenant_id=tenant_id, user=user, request=request)
        MappingService.seed_defaults(tenant_id=tenant_id, user=user)

        # Balanced journals
        unbalanced = []
        for entry in JournalEntry.active_objects().filter(
            tenant_id=tenant_id, status=JournalEntry.STATUS_POSTED
        ).prefetch_related("lines")[:500]:
            lines = [ln for ln in entry.lines.all() if ln.deleted_at is None]
            d = sum((ln.debit for ln in lines), Decimal("0"))
            c = sum((ln.credit for ln in lines), Decimal("0"))
            if d != c:
                unbalanced.append(str(entry.entry_number))
        if unbalanced:
            errors += 1
            checks.append(
                {
                    "id": "journals_balanced",
                    "ok": False,
                    "severity": True,
                    "message": f"{len(unbalanced)} unbalanced journal(s): {', '.join(unbalanced[:5])}",
                }
            )
        else:
            checks.append(
                {
                    "id": "journals_balanced",
                    "ok": True,
                    "severity": False,
                    "message": "All posted journals are balanced.",
                }
            )

        # Failed events
        failed = AccountingEvent.active_objects().filter(
            tenant_id=tenant_id, status=AccountingEvent.STATUS_FAILED
        ).count()
        if failed:
            warnings += 1
            checks.append(
                {
                    "id": "failed_events",
                    "ok": False,
                    "severity": False,
                    "message": f"{failed} failed posting event(s).",
                }
            )
        else:
            checks.append(
                {
                    "id": "failed_events",
                    "ok": True,
                    "severity": False,
                    "message": "No failed posting events.",
                }
            )

        # Pending events
        pending = AccountingEvent.active_objects().filter(
            tenant_id=tenant_id,
            status__in=[AccountingEvent.STATUS_PENDING, AccountingEvent.STATUS_PROCESSING],
        ).count()
        if pending:
            warnings += 1
            checks.append(
                {
                    "id": "pending_events",
                    "ok": False,
                    "severity": False,
                    "message": f"{pending} pending/processing event(s).",
                }
            )
        else:
            checks.append(
                {
                    "id": "pending_events",
                    "ok": True,
                    "severity": False,
                    "message": "No pending posting events.",
                }
            )

        # Duplicate idempotency
        dupes = (
            JournalEntry.active_objects()
            .filter(tenant_id=tenant_id)
            .exclude(idempotency_key="")
            .values("idempotency_key")
            .annotate(c=Count("id"))
            .filter(c__gt=1)
            .count()
        )
        if dupes:
            errors += 1
            checks.append(
                {
                    "id": "no_duplicates",
                    "ok": False,
                    "severity": True,
                    "message": f"{dupes} duplicate idempotency key group(s).",
                }
            )
        else:
            checks.append(
                {
                    "id": "no_duplicates",
                    "ok": True,
                    "severity": False,
                    "message": "No duplicate postings detected.",
                }
            )

        # Required mappings present
        required_keys = (
            "DEFAULT_CASH",
            "DEFAULT_BANK",
            "DEFAULT_MOBILE_MONEY",
            "DEFAULT_RECEIVABLE",
            "DEFAULT_INVENTORY",
            "DEFAULT_PAYABLE",
            "DEFAULT_TAX_PAYABLE",
            "DEFAULT_SALES_REVENUE",
            "DEFAULT_COGS",
        )
        missing_maps = []
        for key in required_keys:
            try:
                MappingService.resolve(key=key, tenant_id=tenant_id, user=user)
            except Exception:
                missing_maps.append(key)
        if missing_maps:
            errors += 1
            checks.append(
                {
                    "id": "account_mappings",
                    "ok": False,
                    "severity": True,
                    "message": f"Missing mappings: {', '.join(missing_maps)}",
                }
            )
        else:
            checks.append(
                {
                    "id": "account_mappings",
                    "ok": True,
                    "severity": False,
                    "message": "Required account mappings present.",
                }
            )

        # AR aging vs control
        ar_report = ReceivablesAgingSelector.run(user=user, request=request)
        if ar_report.get("reconciled"):
            checks.append(
                {
                    "id": "ar_control",
                    "ok": True,
                    "severity": False,
                    "message": (
                        f"AR sub-ledger reconciles "
                        f"({ar_report['totals']['outstanding']:.2f})."
                    ),
                }
            )
        else:
            warnings += 1
            checks.append(
                {
                    "id": "ar_control",
                    "ok": False,
                    "severity": False,
                    "message": (
                        f"AR variance {ar_report['totals']['difference']:.2f} "
                        f"(sub={ar_report['totals']['outstanding']:.2f}, "
                        f"ctrl={ar_report['totals']['control_balance']:.2f})."
                    ),
                }
            )

        # AP aging vs control
        ap_report = PayablesAgingSelector.run(user=user, request=request)
        if ap_report.get("reconciled"):
            checks.append(
                {
                    "id": "ap_control",
                    "ok": True,
                    "severity": False,
                    "message": (
                        f"AP sub-ledger reconciles "
                        f"({ap_report['totals']['outstanding']:.2f})."
                    ),
                }
            )
        else:
            warnings += 1
            checks.append(
                {
                    "id": "ap_control",
                    "ok": False,
                    "severity": False,
                    "message": (
                        f"AP variance {ap_report['totals']['difference']:.2f} "
                        f"(sub={ap_report['totals']['outstanding']:.2f}, "
                        f"ctrl={ap_report['totals']['control_balance']:.2f})."
                    ),
                }
            )

        # Inventory valuation vs GL (approx at current cost)
        inv_check = AccountingHealthService._inventory_reconcile(tenant_id=tenant_id, user=user)
        if inv_check["ok"]:
            checks.append(inv_check)
        else:
            warnings += 1
            checks.append(inv_check)

        # Dual-run: invoice totals vs revenue credits (from cutover if set)
        rev_check = AccountingHealthService._revenue_dual_run(tenant_id=tenant_id, user=user)
        if rev_check["ok"]:
            checks.append(rev_check)
        else:
            warnings += 1
            checks.append(rev_check)

        # Accounting equation (Assets = L + E incl. retained earnings)
        from apps.finance.services.equation_service import AccountingEquationService

        eq = AccountingEquationService.evaluate(tenant_id=tenant_id, user=user, request=request)
        if eq["ok"]:
            checks.append(
                {
                    "id": "accounting_equation",
                    "ok": True,
                    "severity": False,
                    "message": (
                        f"Equation OK — assets {eq['assets']} = L+E "
                        f"{eq['liabilities_plus_equity']}."
                    ),
                }
            )
        else:
            errors += 1
            checks.append(
                {
                    "id": "accounting_equation",
                    "ok": False,
                    "severity": True,
                    "message": (
                        f"Equation broken — assets {eq['assets']} vs L+E "
                        f"{eq['liabilities_plus_equity']} "
                        f"(diff {eq['difference_balance_sheet']})."
                    ),
                }
            )

        # Cutover configured?
        settings = TenantSettings.objects.filter(
            tenant_id=tenant_id, deleted_at__isnull=True
        ).first()
        if settings and settings.accounting_cutover_date:
            checks.append(
                {
                    "id": "cutover_date",
                    "ok": True,
                    "severity": False,
                    "message": f"Accounting cutover set to {settings.accounting_cutover_date.isoformat()}.",
                }
            )
        else:
            checks.append(
                {
                    "id": "cutover_date",
                    "ok": True,
                    "severity": False,
                    "message": "No accounting cutover date set (optional).",
                }
            )

        ok = sum(1 for c in checks if c["ok"])
        status = "healthy"
        if errors:
            status = "unhealthy"
        elif warnings:
            status = "degraded"

        return {
            "status": status,
            "checks": checks,
            "summary": {"ok": ok, "warnings": warnings, "errors": errors},
        }

    @staticmethod
    def _inventory_reconcile(*, tenant_id, user=None) -> dict:
        try:
            inv_acct = MappingService.resolve(key="DEFAULT_INVENTORY", tenant_id=tenant_id, user=user)
            gl_balance = ChartService.account_balance(account=inv_acct)
        except Exception:
            return {
                "id": "inventory_gl",
                "ok": False,
                "severity": False,
                "message": "Inventory account mapping missing.",
            }

        valuation = Decimal("0")
        for row in (
            Inventory.active_objects()
            .filter(tenant_id=tenant_id)
            .select_related("product")
        ):
            qty = Decimal(str(row.quantity or 0))
            cost = Decimal(str(getattr(row.product, "cost_price", 0) or 0))
            valuation += qty * cost

        diff = abs(valuation - gl_balance)
        # Soft check — valuation uses current cost, GL may use historical
        if diff < Decimal("0.01"):
            return {
                "id": "inventory_gl",
                "ok": True,
                "severity": False,
                "message": f"Inventory GL matches valuation ({float(gl_balance):.2f}).",
            }
        if diff < Decimal("1.00") or (gl_balance == 0 and valuation == 0):
            return {
                "id": "inventory_gl",
                "ok": True,
                "severity": False,
                "message": (
                    f"Inventory approx OK (GL={float(gl_balance):.2f}, "
                    f"valuation={float(valuation):.2f}, diff={float(diff):.2f})."
                ),
            }
        return {
            "id": "inventory_gl",
            "ok": False,
            "severity": False,
            "message": (
                f"Inventory variance {float(diff):.2f} "
                f"(GL={float(gl_balance):.2f}, valuation@cost={float(valuation):.2f})."
            ),
        }

    @staticmethod
    def _revenue_dual_run(*, tenant_id, user=None) -> dict:
        """Compare operational invoice net (ex-tax) to revenue account credits after cutover."""
        settings = TenantSettings.objects.filter(
            tenant_id=tenant_id, deleted_at__isnull=True
        ).first()
        cutover = settings.accounting_cutover_date if settings else None

        inv_qs = Invoice.active_objects().filter(
            tenant_id=tenant_id,
            status__in=[Invoice.STATUS_PAID, Invoice.STATUS_SENT, Invoice.STATUS_OVERDUE],
        )
        if cutover:
            inv_qs = inv_qs.filter(issue_date__gte=cutover)

        invoice_net = Decimal("0")
        for inv in inv_qs.only("total_amount", "tax_amount"):
            invoice_net += Decimal(str(inv.total_amount or 0)) - Decimal(str(inv.tax_amount or 0))

        try:
            rev = MappingService.resolve(key="DEFAULT_SALES_REVENUE", tenant_id=tenant_id, user=user)
        except Exception:
            return {
                "id": "revenue_dual_run",
                "ok": False,
                "severity": False,
                "message": "Sales revenue mapping missing.",
            }

        lines = JournalLine.active_objects().filter(
            account=rev,
            entry__status=JournalEntry.STATUS_POSTED,
            entry__deleted_at__isnull=True,
            entry__tenant_id=tenant_id,
        )
        if cutover:
            lines = lines.filter(entry__entry_date__gte=cutover)
        # Net credit on revenue (credits − debits for returns on same account)
        agg = lines.aggregate(
            c=Coalesce(Sum("credit"), Decimal("0")),
            d=Coalesce(Sum("debit"), Decimal("0")),
        )
        gl_net = Decimal(str(agg["c"] or 0)) - Decimal(str(agg["d"] or 0))
        diff = abs(invoice_net - gl_net)

        scope = f"since {cutover.isoformat()}" if cutover else "all time"
        if diff < Decimal("0.05"):
            return {
                "id": "revenue_dual_run",
                "ok": True,
                "severity": False,
                "message": (
                    f"Revenue dual-run OK {scope} "
                    f"(invoices={float(invoice_net):.2f}, GL={float(gl_net):.2f})."
                ),
            }
        return {
            "id": "revenue_dual_run",
            "ok": False,
            "severity": False,
            "message": (
                f"Revenue variance {float(diff):.2f} {scope} "
                f"(invoices={float(invoice_net):.2f}, GL={float(gl_net):.2f})."
            ),
        }
