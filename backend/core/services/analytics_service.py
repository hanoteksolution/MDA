from calendar import month_abbr
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import ExtractHour, TruncMonth
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

    @staticmethod
    def get_sales_report_print(*, branch_id=None, date_from=None, date_to=None):
        """Aggregated payload for the premium printable sales report layout."""
        today = timezone.localdate()
        start = date_from or today.isoformat()
        end = date_to or today.isoformat()
        qs = AnalyticsService._invoice_qs(
            branch_id=branch_id, date_from=start, date_to=end, period="today"
        )
        total_sales = float(qs.aggregate(t=Sum("total_amount"))["t"] or 0)
        total_orders = qs.count()
        total_customers = qs.values("customer_id").distinct().count()
        total_discount = float(qs.aggregate(t=Sum("discount_amount"))["t"] or 0)
        total_tax = float(qs.aggregate(t=Sum("tax_amount"))["t"] or 0)
        returns = float(
            Invoice.active_objects()
            .filter(status=Invoice.STATUS_CANCELLED)
            .filter(**({"branch_id": branch_id} if branch_id else {}))
            .aggregate(t=Sum("total_amount"))["t"]
            or 0
        )

        items_qs = InvoiceItem.objects.filter(
            invoice__in=qs,
            invoice__deleted_at__isnull=True,
        ).select_related("product", "product__category")

        cost_expr = ExpressionWrapper(
            F("quantity") * F("product__cost_price"),
            output_field=DecimalField(max_digits=18, decimal_places=4),
        )
        total_cost = float(items_qs.aggregate(t=Sum(cost_expr))["t"] or 0)
        total_profit = total_sales - total_cost
        profit_margin = (total_profit / total_sales * 100) if total_sales > 0 else 0

        hourly_map = {h: 0.0 for h in range(24)}
        for row in (
            qs.annotate(hour=ExtractHour("created_at"))
            .values("hour")
            .annotate(total=Sum("total_amount"))
        ):
            hour = int(row["hour"] or 0)
            hourly_map[hour] = float(row["total"] or 0)
        hourly_sales = [
            {"hour": f"{h:02d}:00", "value": hourly_map[h]} for h in range(24)
        ]

        category_rows = (
            items_qs.values("product__category__name")
            .annotate(revenue=Sum("line_total"))
            .order_by("-revenue")
        )
        category_total = sum(float(r["revenue"] or 0) for r in category_rows) or 1
        sales_by_category = []
        for r in category_rows[:6]:
            revenue = float(r["revenue"] or 0)
            pct = round(revenue / category_total * 100, 1)
            sales_by_category.append({
                "label": r["product__category__name"] or "Uncategorized",
                "revenue": revenue,
                "pct": pct,
            })

        top_rows = (
            items_qs.values("product__name", "product__sku", "product__cost_price")
            .annotate(sold=Sum("quantity"), revenue=Sum("line_total"))
            .order_by("-revenue")[:10]
        )
        top_products = []
        for i, r in enumerate(top_rows, start=1):
            sold = float(r["sold"] or 0)
            revenue = float(r["revenue"] or 0)
            cost = sold * float(r["product__cost_price"] or 0)
            top_products.append({
                "index": i,
                "name": r["product__name"],
                "sku": r["product__sku"] or "",
                "sold": sold,
                "revenue": revenue,
                "profit": revenue - cost,
            })

        return {
            "date_from": start,
            "date_to": end,
            "kpis": {
                "total_sales": total_sales,
                "total_orders": total_orders,
                "total_customers": total_customers,
                "total_profit": total_profit,
            },
            "hourly_sales": hourly_sales,
            "sales_by_category": sales_by_category,
            "top_products": top_products,
            "summary": {
                "total_sales": total_sales,
                "total_cost": total_cost,
                "total_profit": total_profit,
                "profit_margin": round(profit_margin, 2),
                "discounts": total_discount,
                "returns": returns,
                "tax_collected": total_tax,
            },
        }

    @staticmethod
    def get_customers_report_print(
        *,
        branch_id=None,
        search=None,
        customer_type=None,
        user=None,
    ):
        """Aggregated payload for the premium printable customers report layout."""
        from apps.customers.models import Customer

        qs = Customer.active_objects().select_related("branch")
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if search:
            qs = qs.filter(
                Q(full_name__icontains=search)
                | Q(customer_code__icontains=search)
                | Q(email__icontains=search)
                | Q(phone__icontains=search)
            )
        if customer_type:
            qs = qs.filter(customer_type=customer_type)

        customers = list(qs.order_by("full_name"))
        total = len(customers)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)

        active = sum(1 for c in customers if c.is_active)
        corporate = sum(1 for c in customers if c.customer_type == "corporate")
        retail = sum(1 for c in customers if c.customer_type == "retail")
        wholesale = sum(1 for c in customers if c.customer_type == "wholesale")
        with_credit = sum(1 for c in customers if float(c.credit_limit) > 0)
        outstanding_total = sum(float(c.outstanding_balance) for c in customers)
        new_customers = sum(1 for c in customers if c.created_at.date() >= month_start)
        total_credit_limit = sum(float(c.credit_limit) for c in customers)

        type_total = max(total, 1)
        distribution = []
        for ctype, label in [("retail", "Retail"), ("corporate", "Corporate"), ("wholesale", "Wholesale")]:
            count = sum(1 for c in customers if c.customer_type == ctype)
            distribution.append({
                "label": label,
                "count": count,
                "pct": round(count / type_total * 100, 1),
            })

        growth_qs = Customer.active_objects().filter(created_at__date__gte=year_start)
        if branch_id:
            growth_qs = growth_qs.filter(branch_id=branch_id)
        monthly_rows = (
            growth_qs.annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
        )
        growth_map = {}
        for row in monthly_rows:
            if row["month"]:
                growth_map[int(row["month"].month)] = row["count"]
        monthly_growth = [
            {"month": month_abbr[m], "value": growth_map.get(m, 0)} for m in range(1, 13)
        ]

        inv_qs = Invoice.active_objects().exclude(status=Invoice.STATUS_CANCELLED)
        if branch_id:
            inv_qs = inv_qs.filter(branch_id=branch_id)

        sales_by_customer: dict[str, float] = {}
        last_tx_by_customer: dict[str, str] = {}
        for inv in inv_qs.select_related("customer"):
            cid = str(inv.customer_id)
            sales_by_customer[cid] = sales_by_customer.get(cid, 0) + float(inv.total_amount)
            issue = inv.issue_date.isoformat()
            if cid not in last_tx_by_customer or issue > last_tx_by_customer[cid]:
                last_tx_by_customer[cid] = issue

        items_qs = InvoiceItem.objects.filter(
            invoice__in=inv_qs,
            invoice__deleted_at__isnull=True,
        ).select_related("product", "invoice__customer")
        profit_by_customer: dict[str, float] = {}
        for item in items_qs:
            cid = str(item.invoice.customer_id)
            revenue = float(item.line_total)
            cost = float(item.quantity) * float(item.product.cost_price or 0)
            profit_by_customer[cid] = profit_by_customer.get(cid, 0) + (revenue - cost)

        with_email = sum(1 for c in customers if c.email)
        with_phone = sum(1 for c in customers if c.phone)
        with_both = sum(1 for c in customers if c.email and c.phone)
        missing_info = sum(1 for c in customers if not c.email and not c.phone)

        directory = []
        for i, c in enumerate(customers, start=1):
            cid = str(c.id)
            directory.append({
                "index": i,
                "name": c.full_name,
                "code": c.customer_code,
                "phone": c.phone or "—",
                "email": c.email or "—",
                "type": c.customer_type,
                "credit_limit": float(c.credit_limit),
                "balance": float(c.outstanding_balance),
                "last_transaction": last_tx_by_customer.get(cid, "—"),
                "status": "Active" if c.is_active else "Inactive",
                "is_active": c.is_active,
            })

        sales_total_all = sum(sales_by_customer.values()) or 1
        profit_total_all = sum(profit_by_customer.values()) or 1
        outstanding_total_all = outstanding_total or 1

        def top_rows(metric_map: dict[str, float], fallback_balance=False, limit=5):
            if fallback_balance:
                ranked = sorted(
                    ((str(c.id), float(c.outstanding_balance), c.full_name) for c in customers),
                    key=lambda x: x[1],
                    reverse=True,
                )
            else:
                name_map = {str(c.id): c.full_name for c in customers}
                ranked = sorted(
                    ((cid, amt, name_map.get(cid, "Customer")) for cid, amt in metric_map.items()),
                    key=lambda x: x[1],
                    reverse=True,
                )
            total_metric = sum(r[1] for r in ranked) or 1
            rows = []
            for rank, (_, amount, name) in enumerate(ranked[:limit], start=1):
                pct = round(amount / total_metric * 100, 1) if total_metric else 0
                rows.append({
                    "rank": rank,
                    "name": name,
                    "amount": amount,
                    "pct": pct,
                })
            return rows

        highest_balance = max((float(c.outstanding_balance) for c in customers), default=0)
        avg_value = sales_total_all / max(total, 1)

        username = "MDA ERP"
        if user:
            username = user.get_full_name() or user.username

        branch_name = None
        if branch_id and customers:
            branch_name = customers[0].branch.name if customers[0].branch else None

        return {
            "report_id": f"CUS-{today.strftime('%d%m%Y')}-{total:04d}",
            "report_date": today.isoformat(),
            "generated_by": username,
            "branch": branch_name,
            "growth_year": today.year,
            "kpis": {
                "total": total,
                "active": active,
                "corporate": corporate,
                "retail": retail,
                "wholesale": wholesale,
                "with_credit": with_credit,
                "outstanding": outstanding_total,
                "new_customers": new_customers,
            },
            "distribution": distribution,
            "monthly_growth": monthly_growth,
            "directory": directory,
            "financial_summary": {
                "total_credit_limit": total_credit_limit,
                "total_outstanding": outstanding_total,
                "avg_customer_value": avg_value,
                "highest_balance": highest_balance,
            },
            "contact_summary": {
                "with_email": with_email,
                "with_phone": with_phone,
                "with_both": with_both,
                "missing_info": missing_info,
            },
            "top_by_sales": top_rows(sales_by_customer),
            "top_by_profit": top_rows(profit_by_customer),
            "top_by_outstanding": top_rows({}, fallback_balance=True),
        }

    @staticmethod
    def get_staff_performance(*, branch_id=None, tenant_id=None, period="month", date_from=None, date_to=None):
        from apps.audit.models import AuditLog
        from apps.authentication.models import User

        inv_qs = AnalyticsService._invoice_qs(
            branch_id=branch_id,
            period=period,
            date_from=date_from,
            date_to=date_to,
        )
        if tenant_id:
            inv_qs = inv_qs.filter(branch__company__tenant_id=tenant_id)

        agg = (
            inv_qs.filter(created_by_user_id__isnull=False)
            .values("created_by_user_id")
            .annotate(
                sales_count=Count("id"),
                total_sales=Sum("total_amount"),
                cash_collected=Sum("amount_paid"),
            )
            .order_by("-total_sales")
        )

        user_ids = [row["created_by_user_id"] for row in agg]
        users = {
            u.id: u
            for u in User.objects.filter(id__in=user_ids).select_related("role", "branch")
        }

        period_start = date_from or AnalyticsService._period_start(period)
        login_counts = {
            row["user_id"]: row["c"]
            for row in AuditLog.objects.filter(
                action="login",
                module="auth",
                user_id__in=user_ids,
                timestamp__date__gte=period_start,
            )
            .values("user_id")
            .annotate(c=Count("id"))
        }

        results = []
        for row in agg:
            user = users.get(row["created_by_user_id"])
            if not user:
                continue
            sales_count = row["sales_count"] or 0
            total_sales = float(row["total_sales"] or 0)
            cash = float(row["cash_collected"] or 0)
            results.append({
                "user_id": str(user.id),
                "username": user.username,
                "full_name": user.get_full_name() or user.username,
                "role": user.role.name if user.role else "—",
                "branch": user.branch.name if user.branch else "—",
                "sales_count": sales_count,
                "total_sales": total_sales,
                "cash_collected": cash,
                "average_sale": round(total_sales / sales_count, 2) if sales_count else 0,
                "login_sessions": login_counts.get(user.id, 0),
            })

        if not results and branch_id:
            staff = User.objects.filter(
                branch_id=branch_id,
                is_active=True,
                deleted_at__isnull=True,
            ).exclude(role__slug="super_admin")
            for user in staff.select_related("role", "branch")[:20]:
                results.append({
                    "user_id": str(user.id),
                    "username": user.username,
                    "full_name": user.get_full_name() or user.username,
                    "role": user.role.name if user.role else "—",
                    "branch": user.branch.name if user.branch else "—",
                    "sales_count": 0,
                    "total_sales": 0,
                    "cash_collected": 0,
                    "average_sale": 0,
                    "login_sessions": login_counts.get(user.id, 0),
                })

        return results

    @staticmethod
    def get_staff_performance_for_tenants(*, tenant_ids, period="month", date_from=None, date_to=None):
        from apps.platform.models import Tenant

        combined = []
        for tid in tenant_ids:
            tenant = Tenant.objects.filter(pk=tid).first()
            if not tenant:
                continue
            rows = AnalyticsService.get_staff_performance(
                tenant_id=str(tid),
                period=period,
                date_from=date_from,
                date_to=date_to,
            )
            for row in rows:
                row["tenant_id"] = str(tid)
                row["shop_name"] = tenant.name
                combined.append(row)
        combined.sort(key=lambda r: r.get("total_sales", 0), reverse=True)
        return combined
