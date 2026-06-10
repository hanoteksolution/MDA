from calendar import month_abbr
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, F, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.inventory.services.inventory_service import InventoryService
from apps.purchases.models import PurchaseOrder
from apps.sales.models import Invoice, InvoiceItem


class AnalyticsService:
    @staticmethod
    def _period_start(period: str):
        today = timezone.localdate()
        if period == "week":
            return today - timedelta(days=today.weekday())
        if period == "month":
            return today.replace(day=1)
        if period == "year":
            return today.replace(month=1, day=1)
        return today

    @staticmethod
    def _invoice_qs(*, branch_id=None, period="today", date_from=None, date_to=None):
        qs = Invoice.active_objects().select_related("customer", "branch")
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        qs = qs.exclude(status=Invoice.STATUS_CANCELLED)
        if date_from:
            qs = qs.filter(issue_date__gte=date_from)
        if date_to:
            qs = qs.filter(issue_date__lte=date_to)
        if not date_from and not date_to:
            qs = qs.filter(issue_date__gte=AnalyticsService._period_start(period))
        return qs

    @staticmethod
    def _purchase_qs(*, branch_id=None, period="today", date_from=None, date_to=None):
        qs = PurchaseOrder.active_objects().select_related("supplier", "branch")
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        qs = qs.filter(status__in=[PurchaseOrder.STATUS_ORDERED, PurchaseOrder.STATUS_RECEIVED])
        if date_from:
            qs = qs.filter(order_date__gte=date_from)
        if date_to:
            qs = qs.filter(order_date__lte=date_to)
        if not date_from and not date_to:
            qs = qs.filter(order_date__gte=AnalyticsService._period_start(period))
        return qs

    @staticmethod
    def get_kpis(*, branch_id=None, period="today"):
        inv_qs = AnalyticsService._invoice_qs(branch_id=branch_id, period=period)
        po_qs = AnalyticsService._purchase_qs(branch_id=branch_id, period=period)
        inv_agg = inv_qs.aggregate(
            total_sales=Sum("total_amount"),
            cash_collected=Sum("amount_paid"),
        )
        total_sales = float(inv_agg["total_sales"] or 0)
        cash_collected = float(inv_agg["cash_collected"] or 0)
        # Invoiced revenue drives P&L; cash collected is tracked separately.
        revenue = total_sales
        expenses = float(po_qs.aggregate(t=Sum("total_amount"))["t"] or 0)
        profit = revenue - expenses
        summary = InventoryService.get_summary(branch_id=branch_id)
        return {
            "total_sales": total_sales,
            "revenue": revenue,
            "cash_collected": cash_collected,
            "profit": profit,
            "expenses": expenses,
            "inventory_value": summary["inventory_value"],
            "low_stock_count": summary["low_stock_count"],
            "out_of_stock_count": summary["out_of_stock_count"],
            "period": period,
        }

    @staticmethod
    def get_recent_sales(*, branch_id=None, limit=10):
        qs = Invoice.active_objects().select_related("customer").order_by("-issue_date", "-created_at")
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        results = []
        for inv in qs[:limit]:
            status = "completed" if inv.status == Invoice.STATUS_PAID else inv.status
            results.append({
                "id": inv.invoice_number,
                "customer": inv.customer.full_name,
                "amount": float(inv.total_amount),
                "status": status,
                "date": inv.issue_date.isoformat(),
            })
        return results

    @staticmethod
    def get_low_stock(*, branch_id=None, limit=20):
        qs = InventoryService.get_low_stock()
        if branch_id:
            qs = qs.filter(warehouse__branch_id=branch_id)
        results = []
        for inv in qs[:limit]:
            results.append({
                "id": str(inv.id),
                "product": inv.product.name,
                "sku": inv.product.sku,
                "current": float(inv.quantity),
                "minimum": inv.product.minimum_stock,
                "warehouse": inv.warehouse.name,
            })
        out_qs = InventoryService.get_out_of_stock()
        if branch_id:
            out_qs = out_qs.filter(warehouse__branch_id=branch_id)
        for inv in out_qs[: max(0, limit - len(results))]:
            results.append({
                "id": str(inv.id),
                "product": inv.product.name,
                "sku": inv.product.sku,
                "current": 0,
                "minimum": inv.product.minimum_stock,
                "warehouse": inv.warehouse.name,
            })
        return results

    @staticmethod
    def get_top_products(*, branch_id=None, period="month", limit=10):
        qs = InvoiceItem.objects.filter(
            invoice__deleted_at__isnull=True,
            invoice__issue_date__gte=AnalyticsService._period_start(period),
        ).exclude(invoice__status=Invoice.STATUS_CANCELLED)
        if branch_id:
            qs = qs.filter(invoice__branch_id=branch_id)
        rows = (
            qs.values("product_id", "product__name", "product__sku")
            .annotate(sold=Sum("quantity"), revenue=Sum("line_total"))
            .order_by("-revenue")[:limit]
        )
        return [
            {
                "id": str(r["product_id"]),
                "name": r["product__name"],
                "sku": r["product__sku"],
                "sold": float(r["sold"] or 0),
                "revenue": float(r["revenue"] or 0),
            }
            for r in rows
        ]

    @staticmethod
    def _monthly_series(*, branch_id=None, months=12, value_field="total_amount", model="invoice"):
        today = timezone.localdate()
        start = (today.replace(day=1) - timedelta(days=months * 31)).replace(day=1)
        if model == "invoice":
            qs = Invoice.active_objects().filter(issue_date__gte=start).exclude(status=Invoice.STATUS_CANCELLED)
            date_field = "issue_date"
        else:
            qs = PurchaseOrder.active_objects().filter(
                order_date__gte=start,
                status__in=[PurchaseOrder.STATUS_ORDERED, PurchaseOrder.STATUS_RECEIVED],
            )
            date_field = "order_date"
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        rows = (
            qs.annotate(month=TruncMonth(date_field))
            .values("month")
            .annotate(total=Sum(value_field))
            .order_by("month")
        )
        return {r["month"].strftime("%Y-%m"): float(r["total"] or 0) for r in rows if r["month"]}

    @staticmethod
    def get_chart_data(*, branch_id=None):
        sales_map = AnalyticsService._monthly_series(branch_id=branch_id, months=12, model="invoice")
        expense_map = AnalyticsService._monthly_series(branch_id=branch_id, months=12, model="purchase")
        today = timezone.localdate()
        sales_trend = []
        revenue_chart = []
        profit_chart = []
        for i in range(11, -1, -1):
            d = today.replace(day=1)
            month = d.month - i
            year = d.year
            while month <= 0:
                month += 12
                year -= 1
            key = f"{year}-{month:02d}"
            label = month_abbr[month]
            sales = sales_map.get(key, 0)
            expenses = expense_map.get(key, 0)
            sales_trend.append({"month": label, "sales": sales, "revenue": sales})
            if i < 6:
                revenue_chart.append({"month": label, "revenue": sales})
                profit_chart.append({"month": label, "profit": sales - expenses, "expenses": expenses})
        return {
            "sales_trend": sales_trend,
            "revenue": revenue_chart,
            "profit": profit_chart,
        }

    @staticmethod
    def get_finance_summary(*, branch_id=None, period="month"):
        kpis = AnalyticsService.get_kpis(branch_id=branch_id, period=period)
        inv_qs = AnalyticsService._invoice_qs(branch_id=branch_id, period=period).order_by("-issue_date")[:5]
        po_qs = AnalyticsService._purchase_qs(branch_id=branch_id, period=period).order_by("-order_date")[:5]
        activity = []
        for inv in inv_qs:
            activity.append({
                "id": str(inv.id),
                "label": f"Invoice {inv.invoice_number}",
                "amount": float(inv.total_amount),
                "type": "in",
                "date": inv.issue_date.isoformat(),
            })
        for po in po_qs:
            activity.append({
                "id": str(po.id),
                "label": f"Purchase {po.order_number}",
                "amount": float(po.total_amount),
                "type": "out",
                "date": po.order_date.isoformat(),
            })
        activity.sort(key=lambda x: x["date"], reverse=True)
        inv_summary = InventoryService.get_summary(branch_id=branch_id)
        unpaid = Invoice.active_objects().exclude(status__in=[Invoice.STATUS_PAID, Invoice.STATUS_CANCELLED])
        if branch_id:
            unpaid = unpaid.filter(branch_id=branch_id)
        receivables = float(unpaid.aggregate(t=Sum(F("total_amount") - F("amount_paid")))["t"] or 0)
        payables_qs = PurchaseOrder.active_objects().filter(status=PurchaseOrder.STATUS_ORDERED)
        if branch_id:
            payables_qs = payables_qs.filter(branch_id=branch_id)
        payables = float(payables_qs.aggregate(t=Sum("total_amount"))["t"] or 0)
        accounts = [
            {"id": "cash", "name": "Cash & Bank", "type": "Asset", "balance": kpis["cash_collected"] - kpis["expenses"]},
            {"id": "ar", "name": "Accounts Receivable", "type": "Asset", "balance": receivables},
            {"id": "inventory", "name": "Inventory Asset", "type": "Asset", "balance": inv_summary["inventory_value"]},
            {"id": "ap", "name": "Accounts Payable", "type": "Liability", "balance": payables},
            {"id": "revenue", "name": "Sales Revenue", "type": "Revenue", "balance": kpis["revenue"]},
            {"id": "cogs", "name": "Cost of Goods Sold", "type": "Expense", "balance": kpis["expenses"]},
        ]
        expenses = []
        for po in AnalyticsService._purchase_qs(branch_id=branch_id, period=period).order_by("-order_date")[:20]:
            expenses.append({
                "id": str(po.id),
                "description": f"PO {po.order_number} — {po.supplier.company_name}",
                "category": "Purchases",
                "date": po.order_date.isoformat(),
                "amount": float(po.total_amount),
                "status": "paid" if po.status == PurchaseOrder.STATUS_RECEIVED else "approved",
            })
        return {
            "kpis": {
                "revenue": kpis["revenue"],
                "expenses": kpis["expenses"],
                "net_profit": kpis["profit"],
                "cash_collected": kpis["cash_collected"],
                "cash_balance": kpis["cash_collected"] - kpis["expenses"],
            },
            "activity": activity[:8],
            "accounts": accounts,
            "expenses": expenses,
            "chart": AnalyticsService.get_chart_data(branch_id=branch_id)["profit"],
        }

    @staticmethod
    def get_report(*, category: str, report: str, branch_id=None, date_from=None, date_to=None):
        if category == "sales":
            if report == "Daily Sales":
                rows = []
                for inv in AnalyticsService._invoice_qs(
                    branch_id=branch_id, date_from=date_from, date_to=date_to
                ).order_by("-issue_date")[:50]:
                    rows.append({
                        "date": inv.issue_date.isoformat(),
                        "invoice": inv.invoice_number,
                        "customer": inv.customer.full_name,
                        "amount": float(inv.total_amount),
                        "status": inv.status,
                    })
                return {"columns": ["date", "invoice", "customer", "amount", "status"], "rows": rows}
            if report == "Sales by Product":
                rows = AnalyticsService.get_top_products(branch_id=branch_id, period="year", limit=25)
                return {"columns": ["name", "sku", "sold", "revenue"], "rows": rows}
            if report == "Sales by Customer":
                qs = AnalyticsService._invoice_qs(branch_id=branch_id, date_from=date_from, date_to=date_to)
                rows = list(
                    qs.values("customer__full_name")
                    .annotate(total=Sum("total_amount"), count=Count("id"))
                    .order_by("-total")[:25]
                )
                return {
                    "columns": ["customer", "orders", "total"],
                    "rows": [
                        {
                            "customer": r["customer__full_name"],
                            "orders": r["count"],
                            "total": float(r["total"] or 0),
                        }
                        for r in rows
                    ],
                }
            if report == "Tax Summary":
                qs = AnalyticsService._invoice_qs(branch_id=branch_id, date_from=date_from, date_to=date_to)
                total_tax = float(qs.aggregate(t=Sum("tax_amount"))["t"] or 0)
                total_sales = float(qs.aggregate(t=Sum("total_amount"))["t"] or 0)
                return {
                    "columns": ["metric", "value"],
                    "rows": [
                        {"metric": "Taxable Sales", "value": total_sales},
                        {"metric": "Total Tax Collected", "value": total_tax},
                    ],
                }
        if category == "inventory":
            if report == "Stock Valuation":
                qs = InventoryService.list_inventory()
                if branch_id:
                    qs = qs.filter(warehouse__branch_id=branch_id)
                rows = []
                for inv in qs[:50]:
                    rows.append({
                        "product": inv.product.name,
                        "sku": inv.product.sku,
                        "qty": float(inv.quantity),
                        "unit_cost": float(inv.product.cost_price),
                        "value": float(inv.quantity * inv.product.cost_price),
                        "warehouse": inv.warehouse.name,
                    })
                return {"columns": ["product", "sku", "qty", "unit_cost", "value", "warehouse"], "rows": rows}
            if report == "Low Stock":
                rows = AnalyticsService.get_low_stock(branch_id=branch_id, limit=50)
                return {"columns": ["product", "sku", "current", "minimum", "warehouse"], "rows": rows}
        if category == "purchases":
            if report == "Purchase Summary":
                rows = []
                for po in AnalyticsService._purchase_qs(
                    branch_id=branch_id, date_from=date_from, date_to=date_to
                ).order_by("-order_date")[:50]:
                    rows.append({
                        "order": po.order_number,
                        "supplier": po.supplier.company_name,
                        "date": po.order_date.isoformat(),
                        "amount": float(po.total_amount),
                        "status": po.status,
                    })
                return {"columns": ["order", "supplier", "date", "amount", "status"], "rows": rows}
            if report == "Supplier Analysis":
                qs = AnalyticsService._purchase_qs(branch_id=branch_id, date_from=date_from, date_to=date_to)
                rows = list(
                    qs.values("supplier__company_name")
                    .annotate(total=Sum("total_amount"), orders=Count("id"))
                    .order_by("-total")[:25]
                )
                return {
                    "columns": ["supplier", "orders", "total"],
                    "rows": [
                        {
                            "supplier": r["supplier__company_name"],
                            "orders": r["orders"],
                            "total": float(r["total"] or 0),
                        }
                        for r in rows
                    ],
                }
        if category == "finance":
            fin = AnalyticsService.get_finance_summary(branch_id=branch_id, period="year")
            if report == "Profit & Loss":
                return {
                    "columns": ["line", "amount"],
                    "rows": [
                        {"line": "Revenue", "amount": fin["kpis"]["revenue"]},
                        {"line": "Expenses", "amount": fin["kpis"]["expenses"]},
                        {"line": "Net Profit", "amount": fin["kpis"]["net_profit"]},
                    ],
                }
            if report == "Expense Breakdown":
                return {"columns": ["description", "category", "date", "amount", "status"], "rows": fin["expenses"]}
        if category == "customers":
            from apps.customers.models import Customer

            qs = Customer.active_objects()
            if branch_id:
                qs = qs.filter(branch_id=branch_id)
            rows = []
            for c in qs[:30]:
                inv_qs = Invoice.active_objects().filter(customer=c)
                inv_total = inv_qs.aggregate(t=Sum("total_amount"))["t"]
                order_count = inv_qs.count()
                rows.append({
                    "customer": c.full_name,
                    "type": c.customer_type,
                    "orders": order_count,
                    "total_spent": float(inv_total or 0),
                    "credit_limit": float(c.credit_limit),
                })
            return {"columns": ["customer", "type", "orders", "total_spent", "credit_limit"], "rows": rows}
        return {"columns": [], "rows": []}
