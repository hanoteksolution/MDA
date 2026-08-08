"""Finance dashboard KPIs — journals + operational sources (STEP 21)."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum

from apps.finance.services.chart_service import ChartService
from apps.finance.services.journal_service import JournalService
from apps.purchases.models import PurchaseOrder
from apps.sales.models import Expense, Invoice
from core.services.analytics_service import AnalyticsService
from core.tenancy import apply_tenant_scope, resolve_acting_tenant, stamp_tenant_id


class FinanceSummaryService:
    @staticmethod
    def get_summary(*, branch_id=None, period="month", user=None, request=None):
        tenant = resolve_acting_tenant(user=user, request=request)
        tenant_id = getattr(tenant, "pk", None) if tenant else stamp_tenant_id({}, user=user, request=request).get("tenant_id")

        if tenant_id:
            ChartService.ensure_default_chart(tenant_id=tenant_id, user=user, request=request)

        kpis_base = AnalyticsService.get_kpis(branch_id=branch_id, period=period)

        period_start = AnalyticsService._period_start(period)
        op_exp_qs = apply_tenant_scope(Expense.active_objects(), user=user, request=request)
        if branch_id:
            op_exp_qs = op_exp_qs.filter(branch_id=branch_id)
        op_exp_qs = op_exp_qs.filter(expense_date__gte=period_start)
        operating_expenses = float(op_exp_qs.aggregate(t=Sum("amount"))["t"] or 0)

        purchase_expenses = kpis_base["expenses"]
        total_expenses = operating_expenses + purchase_expenses
        net_profit = kpis_base["revenue"] - total_expenses

        accounts = ChartService.list_with_balances(user=user, request=request) if tenant_id else []

        cash_balance = kpis_base["cash_collected"] - operating_expenses
        if tenant_id and accounts:
            cash_row = next((a for a in accounts if a["code"] == "1000"), None)
            if cash_row is not None:
                cash_balance = cash_row["balance"]

        expenses_list = []
        for e in op_exp_qs.order_by("-expense_date")[:20]:
            expenses_list.append(
                {
                    "id": str(e.id),
                    "description": e.description,
                    "category": e.category,
                    "date": e.expense_date.isoformat(),
                    "amount": float(e.amount),
                    "status": "paid",
                    "source": "operating",
                }
            )
        for po in AnalyticsService._purchase_qs(branch_id=branch_id, period=period).order_by(
            "-order_date"
        )[:10]:
            expenses_list.append(
                {
                    "id": str(po.id),
                    "description": f"PO {po.order_number} — {po.supplier.company_name}",
                    "category": "purchases",
                    "date": po.order_date.isoformat(),
                    "amount": float(po.total_amount),
                    "status": "paid" if po.status == PurchaseOrder.STATUS_RECEIVED else "approved",
                    "source": "purchase",
                }
            )
        expenses_list.sort(key=lambda x: x["date"], reverse=True)

        activity = []
        inv_qs = AnalyticsService._invoice_qs(branch_id=branch_id, period=period).order_by(
            "-issue_date"
        )[:5]
        for inv in inv_qs:
            activity.append(
                {
                    "id": str(inv.id),
                    "label": f"Invoice {inv.invoice_number}",
                    "amount": float(inv.total_amount),
                    "type": "in",
                    "date": inv.issue_date.isoformat(),
                }
            )
        for e in op_exp_qs.order_by("-expense_date")[:5]:
            activity.append(
                {
                    "id": str(e.id),
                    "label": e.description,
                    "amount": float(e.amount),
                    "type": "out",
                    "date": e.expense_date.isoformat(),
                }
            )
        activity.sort(key=lambda x: x["date"], reverse=True)

        journal = []
        if tenant_id:
            for entry in JournalService.list(user=user, request=request)[:15]:
                journal.append(JournalService.serialize(entry))

        if not accounts:
            inv_summary = AnalyticsService.get_finance_summary(branch_id=branch_id, period=period)
            accounts = inv_summary.get("accounts", [])

        return {
            "kpis": {
                "revenue": kpis_base["revenue"],
                "expenses": total_expenses,
                "operating_expenses": operating_expenses,
                "purchase_expenses": purchase_expenses,
                "net_profit": net_profit,
                "cash_collected": kpis_base["cash_collected"],
                "cash_balance": cash_balance,
            },
            "activity": activity[:8],
            "accounts": accounts,
            "expenses": expenses_list[:20],
            "journal": journal,
            "chart": AnalyticsService.get_chart_data(branch_id=branch_id)["profit"],
            "has_ledger": bool(tenant_id and accounts),
        }
