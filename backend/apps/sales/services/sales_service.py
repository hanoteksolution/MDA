from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.sales.models import Invoice, InvoiceItem, Quotation, QuotationItem
from apps.settings_app.models import Branch


class QuotationService:
    @staticmethod
    def list(*, search=None, status=None, customer_id=None, branch_id=None):
        qs = Quotation.active_objects().select_related("customer", "branch", "created_by_user").prefetch_related("items__product")
        if search:
            qs = qs.filter(
                Q(quotation_number__icontains=search) | Q(customer__full_name__icontains=search)
            )
        if status:
            qs = qs.filter(status=status)
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs.order_by("-created_at")

    @staticmethod
    def _next_number(*, branch: Branch) -> str:
        count = Quotation.objects.filter(branch=branch).count() + 1
        return f"QT-{branch.code}-{count:05d}"

    @staticmethod
    def _recalculate(*, quotation: Quotation):
        agg = quotation.items.aggregate(subtotal=Sum("line_total"))
        subtotal = agg["subtotal"] or Decimal("0")
        quotation.subtotal = subtotal
        quotation.tax_amount = Decimal("0")
        quotation.total_amount = subtotal - quotation.discount_amount + quotation.tax_amount
        quotation.save(update_fields=["subtotal", "tax_amount", "total_amount", "updated_at"])

    @staticmethod
    @transaction.atomic
    def create(*, data, items, user=None):
        branch_id = data.pop("branch_id", None)
        customer_id = data.pop("customer_id")
        branch = _resolve_branch(branch_id)
        quotation = Quotation.objects.create(
            quotation_number=QuotationService._next_number(branch=branch),
            customer_id=customer_id,
            branch=branch,
            created_by_user=user,
            created_by=user,
            **data,
        )
        for item in items or []:
            QuotationItem.objects.create(
                quotation=quotation,
                product_id=item["product_id"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                created_by=user,
            )
        QuotationService._recalculate(quotation=quotation)
        return QuotationService.list().get(pk=quotation.pk)

    @staticmethod
    @transaction.atomic
    def update(*, instance, data, items=None, user=None):
        customer_id = data.pop("customer_id", None)
        branch_id = data.pop("branch_id", None)
        if customer_id:
            instance.customer_id = customer_id
        if branch_id:
            instance.branch_id = branch_id
        for key, value in data.items():
            if key not in ("quotation_number",):
                setattr(instance, key, value)
        instance.updated_by = user
        instance.save()
        if items is not None:
            instance.items.all().delete()
            for item in items:
                QuotationItem.objects.create(
                    quotation=instance,
                    product_id=item["product_id"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    created_by=user,
                )
            QuotationService._recalculate(quotation=instance)
        return QuotationService.list().get(pk=instance.pk)


class InvoiceService:
    @staticmethod
    def list(*, search=None, status=None, customer_id=None, branch_id=None):
        qs = Invoice.active_objects().select_related("customer", "branch", "created_by_user").prefetch_related("items__product")
        if search:
            qs = qs.filter(
                Q(invoice_number__icontains=search) | Q(customer__full_name__icontains=search)
            )
        if status:
            qs = qs.filter(status=status)
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs.order_by("-issue_date", "-created_at")

    @staticmethod
    def _next_number(*, branch: Branch) -> str:
        count = Invoice.objects.filter(branch=branch).count() + 1
        return f"INV-{branch.code}-{count:05d}"

    @staticmethod
    def _recalculate(*, invoice: Invoice):
        agg = invoice.items.aggregate(subtotal=Sum("line_total"))
        subtotal = agg["subtotal"] or Decimal("0")
        invoice.subtotal = subtotal
        invoice.tax_amount = Decimal("0")
        invoice.total_amount = subtotal - invoice.discount_amount + invoice.tax_amount
        invoice.save(update_fields=["subtotal", "tax_amount", "total_amount", "updated_at"])

    @staticmethod
    @transaction.atomic
    def create(*, data, items, user=None):
        branch_id = data.pop("branch_id", None)
        customer_id = data.pop("customer_id")
        branch = _resolve_branch(branch_id)
        invoice = Invoice.objects.create(
            invoice_number=InvoiceService._next_number(branch=branch),
            customer_id=customer_id,
            branch=branch,
            created_by_user=user,
            created_by=user,
            **data,
        )
        for item in items or []:
            InvoiceItem.objects.create(
                invoice=invoice,
                product_id=item["product_id"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                created_by=user,
            )
        InvoiceService._recalculate(invoice=invoice)
        return InvoiceService.list().get(pk=invoice.pk)

    @staticmethod
    @transaction.atomic
    def update(*, instance, data, items=None, user=None):
        customer_id = data.pop("customer_id", None)
        branch_id = data.pop("branch_id", None)
        if customer_id:
            instance.customer_id = customer_id
        if branch_id:
            instance.branch_id = branch_id
        for key, value in data.items():
            if key not in ("invoice_number",):
                setattr(instance, key, value)
        instance.updated_by = user
        instance.save()
        if items is not None:
            instance.items.all().delete()
            for item in items:
                InvoiceItem.objects.create(
                    invoice=instance,
                    product_id=item["product_id"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    created_by=user,
                )
            InvoiceService._recalculate(invoice=instance)
        return InvoiceService.list().get(pk=instance.pk)

    @staticmethod
    def summary():
        qs = Invoice.active_objects()
        by_status = qs.values("status").annotate(count=Count("id"))
        status_map = {row["status"]: row["count"] for row in by_status}
        today = timezone.localdate()
        month_start = today.replace(day=1)
        today_total = float(
            qs.filter(issue_date=today, status=Invoice.STATUS_PAID).aggregate(t=Sum("total_amount"))["t"] or 0
        )
        month_total = float(
            qs.filter(issue_date__gte=month_start, status=Invoice.STATUS_PAID).aggregate(t=Sum("total_amount"))["t"] or 0
        )
        return {
            "today_sales": today_total,
            "month_sales": month_total,
            "open_invoices": status_map.get(Invoice.STATUS_SENT, 0) + status_map.get(Invoice.STATUS_DRAFT, 0),
            "quotations_count": Quotation.active_objects().count(),
        }


def _resolve_branch(branch_id):
    if branch_id:
        return Branch.active_objects().get(pk=branch_id)
    branch = Branch.active_objects().filter(is_default=True).first()
    return branch or Branch.active_objects().first()
