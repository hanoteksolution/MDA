import re
from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.db.models import Count, Sum, Q
from django.utils import timezone

from apps.sales.models import Expense, Invoice, InvoiceItem
from apps.sales.services.sales_service import _resolve_branch


def _parse_waiter(notes: str) -> str:
    if not notes:
        return ""
    match = re.search(r"Waiter:\s*([^|\n]+)", notes, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _parse_payment_method(notes: str) -> str:
    if not notes:
        return ""
    match = re.search(r"Payment:\s*([a-z_]+)", notes, re.IGNORECASE)
    return match.group(1).lower() if match else ""


class DailyOpsService:
    @staticmethod
    def daily_summary(*, day: date | None = None, branch_id=None):
        day = day or timezone.localdate()
        branch = _resolve_branch(branch_id)

        invoices = (
            Invoice.active_objects()
            .filter(branch=branch, issue_date=day)
            .select_related("customer", "served_by_user")
            .prefetch_related("items__product")
        )

        paid = invoices.filter(status=Invoice.STATUS_PAID)
        unpaid = invoices.exclude(
            status__in=[Invoice.STATUS_PAID, Invoice.STATUS_CANCELLED, Invoice.STATUS_ON_HOLD]
        )

        # Products sold that day (all non-cancelled invoices)
        product_rows = (
            InvoiceItem.objects.filter(
                invoice__in=invoices.exclude(status=Invoice.STATUS_CANCELLED),
                invoice__deleted_at__isnull=True,
            )
            .values("product_id", "product__name", "product__sku")
            .annotate(
                quantity=Sum("quantity"),
                revenue=Sum("line_total"),
                lines=Count("id"),
            )
            .order_by("-quantity")
        )
        products_sold = [
            {
                "product_id": str(r["product_id"]),
                "name": r["product__name"],
                "sku": r["product__sku"],
                "quantity": float(r["quantity"] or 0),
                "revenue": float(r["revenue"] or 0),
            }
            for r in product_rows
        ]

        unpaid_receipts = []
        for inv in unpaid.order_by("-created_at"):
            waiter = ""
            if inv.served_by_user:
                waiter = inv.served_by_user.get_full_name() or inv.served_by_user.username
            if not waiter:
                waiter = _parse_waiter(inv.notes or "")
            unpaid_receipts.append({
                "invoice_id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "customer_name": inv.customer.full_name,
                "customer_id": str(inv.customer_id),
                "status": inv.status,
                "payment_method": _parse_payment_method(inv.notes or "") or "—",
                "waiter_name": waiter,
                "total_amount": float(inv.total_amount),
                "amount_paid": float(inv.amount_paid),
                "balance_due": float(inv.total_amount - inv.amount_paid),
                "items": [
                    {
                        "name": i.product.name,
                        "quantity": float(i.quantity),
                        "line_total": float(i.line_total),
                    }
                    for i in inv.items.all()
                ],
            })

        expenses = Expense.active_objects().filter(branch=branch, expense_date=day)
        expense_list = [
            {
                "id": str(e.id),
                "description": e.description,
                "category": e.category,
                "amount": float(e.amount),
                "notes": e.notes,
                "expense_date": e.expense_date.isoformat(),
            }
            for e in expenses
        ]

        paid_total = float(paid.aggregate(t=Sum("total_amount"))["t"] or 0)
        unpaid_total = float(
            sum(Decimal(str(r["balance_due"])) for r in unpaid_receipts)
        )
        expense_total = float(expenses.aggregate(t=Sum("amount"))["t"] or 0)

        return {
            "date": day.isoformat(),
            "summary": {
                "invoices_count": invoices.exclude(status=Invoice.STATUS_CANCELLED).count(),
                "paid_total": paid_total,
                "unpaid_count": len(unpaid_receipts),
                "unpaid_total": unpaid_total,
                "products_count": len(products_sold),
                "expense_total": expense_total,
            },
            "products_sold": products_sold,
            "unpaid_receipts": unpaid_receipts,
            "expenses": expense_list,
            "activity_dates": DailyOpsService._recent_activity_dates(branch=branch, around=day),
        }

    @staticmethod
    def _recent_activity_dates(*, branch, around: date, limit: int = 8):
        """Dates (near the selected day) that have invoices or expenses — for empty-state jumps."""
        inv_dates = (
            Invoice.active_objects()
            .filter(branch=branch)
            .exclude(status=Invoice.STATUS_CANCELLED)
            .order_by("-issue_date")
            .values_list("issue_date", flat=True)
            .distinct()[:40]
        )
        exp_dates = (
            Expense.active_objects()
            .filter(branch=branch)
            .order_by("-expense_date")
            .values_list("expense_date", flat=True)
            .distinct()[:40]
        )
        merged = sorted(set(list(inv_dates) + list(exp_dates)), reverse=True)
        # Prefer dates on/before the selected day, then any later ones
        before = [d for d in merged if d <= around]
        after = [d for d in merged if d > around]
        ordered = before + after
        return [d.isoformat() for d in ordered[:limit]]

    @staticmethod
    def customer_monthly_account(*, customer_id: str, year: int | None = None, month: int | None = None, branch_id=None):
        today = timezone.localdate()
        year = year or today.year
        month = month or today.month
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        branch = _resolve_branch(branch_id)

        qs = (
            Invoice.active_objects()
            .filter(
                branch=branch,
                customer_id=customer_id,
                issue_date__gte=start,
                issue_date__lte=end,
            )
            .exclude(status=Invoice.STATUS_CANCELLED)
            .select_related("customer", "served_by_user")
            .prefetch_related("items__product")
            .order_by("issue_date", "created_at")
        )

        receipts = []
        total_amount = Decimal("0")
        total_paid = Decimal("0")
        total_due = Decimal("0")
        waiters: dict[str, Decimal] = {}
        products: dict[str, dict] = {}

        customer_name = ""
        for inv in qs:
            customer_name = inv.customer.full_name
            waiter = ""
            if inv.served_by_user:
                waiter = inv.served_by_user.get_full_name() or inv.served_by_user.username
            if not waiter:
                waiter = _parse_waiter(inv.notes or "") or "—"

            balance = inv.total_amount - inv.amount_paid
            total_amount += inv.total_amount
            total_paid += inv.amount_paid
            if inv.status != Invoice.STATUS_PAID:
                total_due += balance
                waiters[waiter] = waiters.get(waiter, Decimal("0")) + balance

            item_rows = []
            for i in inv.items.all():
                item_rows.append({
                    "name": i.product.name,
                    "sku": i.product.sku,
                    "quantity": float(i.quantity),
                    "line_total": float(i.line_total),
                })
                key = str(i.product_id)
                if key not in products:
                    products[key] = {
                        "name": i.product.name,
                        "sku": i.product.sku,
                        "quantity": Decimal("0"),
                        "amount": Decimal("0"),
                    }
                products[key]["quantity"] += i.quantity
                products[key]["amount"] += i.line_total

            receipts.append({
                "invoice_id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "issue_date": inv.issue_date.isoformat(),
                "status": inv.status,
                "payment_method": _parse_payment_method(inv.notes or "") or "—",
                "waiter_name": waiter,
                "total_amount": float(inv.total_amount),
                "amount_paid": float(inv.amount_paid),
                "balance_due": float(balance),
                "items": item_rows,
            })

        return {
            "customer_id": customer_id,
            "customer_name": customer_name,
            "year": year,
            "month": month,
            "period_label": start.strftime("%B %Y"),
            "summary": {
                "receipts_count": len(receipts),
                "total_amount": float(total_amount),
                "total_paid": float(total_paid),
                "total_due": float(total_due),
            },
            "waiters": [
                {"name": name, "amount_due": float(amt)}
                for name, amt in sorted(waiters.items(), key=lambda x: -x[1])
            ],
            "products": [
                {
                    "name": p["name"],
                    "sku": p["sku"],
                    "quantity": float(p["quantity"]),
                    "amount": float(p["amount"]),
                }
                for p in sorted(products.values(), key=lambda x: -float(x["amount"]))
            ],
            "receipts": receipts,
        }

    @staticmethod
    def list_expenses(*, branch_id=None, date_from=None, date_to=None, category=None, search=None):
        branch = _resolve_branch(branch_id)
        qs = (
            Expense.active_objects()
            .filter(branch=branch)
            .select_related("branch", "created_by_user")
            .order_by("-expense_date", "-created_at")
        )
        if date_from:
            qs = qs.filter(expense_date__gte=date_from)
        if date_to:
            qs = qs.filter(expense_date__lte=date_to)
        if category and category != "all":
            qs = qs.filter(category=category)
        if search:
            qs = qs.filter(
                Q(description__icontains=search)
                | Q(notes__icontains=search)
                | Q(category__icontains=search)
            )
        rows = []
        total = Decimal("0")
        for e in qs[:500]:
            amount = Decimal(str(e.amount))
            total += amount
            created_by = ""
            if e.created_by_user_id:
                created_by = e.created_by_user.get_full_name() or e.created_by_user.username
            rows.append({
                "id": str(e.id),
                "description": e.description,
                "category": e.category,
                "amount": float(amount),
                "notes": e.notes,
                "expense_date": e.expense_date.isoformat(),
                "branch_id": str(e.branch_id),
                "branch_name": e.branch.name if e.branch_id else "",
                "created_by": created_by,
                "created_at": e.created_at.isoformat(),
            })
        return {
            "results": rows,
            "count": len(rows),
            "total_amount": float(total),
        }

    @staticmethod
    def _expense_payload(expense: Expense) -> dict:
        created_by = ""
        if expense.created_by_user_id:
            created_by = expense.created_by_user.get_full_name() or expense.created_by_user.username
        return {
            "id": str(expense.id),
            "description": expense.description,
            "category": expense.category,
            "amount": float(expense.amount),
            "notes": expense.notes,
            "expense_date": expense.expense_date.isoformat(),
            "branch_id": str(expense.branch_id),
            "branch_name": expense.branch.name if expense.branch_id else "",
            "created_by": created_by,
            "created_at": expense.created_at.isoformat() if expense.created_at else None,
        }

    @staticmethod
    def create_expense(*, data, user=None):
        branch = _resolve_branch(data.get("branch_id"))
        expense = Expense.objects.create(
            branch=branch,
            expense_date=data.get("expense_date") or timezone.localdate(),
            category=data.get("category") or "other",
            description=(data.get("description") or "").strip(),
            amount=Decimal(str(data.get("amount") or 0)),
            notes=(data.get("notes") or "").strip(),
            created_by_user=user,
            created_by=user,
        )
        if not expense.description:
            raise ValueError("Description is required.")
        if expense.amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        return DailyOpsService._expense_payload(expense)

    @staticmethod
    def update_expense(*, expense_id, data, user=None):
        expense = Expense.active_objects().select_related("branch", "created_by_user").get(pk=expense_id)
        if "description" in data:
            expense.description = (data.get("description") or "").strip()
        if "category" in data:
            expense.category = data.get("category") or expense.category
        if "amount" in data and data.get("amount") is not None:
            expense.amount = Decimal(str(data.get("amount")))
        if "notes" in data:
            expense.notes = (data.get("notes") or "").strip()
        if "expense_date" in data and data.get("expense_date"):
            expense.expense_date = data.get("expense_date")
        if data.get("branch_id"):
            expense.branch = _resolve_branch(data.get("branch_id"))
        if not expense.description:
            raise ValueError("Description is required.")
        if expense.amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        expense.updated_by = user
        expense.save()
        return DailyOpsService._expense_payload(expense)

    @staticmethod
    def delete_expense(*, expense_id, user=None):
        expense = Expense.active_objects().get(pk=expense_id)
        expense.soft_delete(user=user)
        return True