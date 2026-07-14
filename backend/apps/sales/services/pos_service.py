import re
import json
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.authentication.models import User
from apps.customers.models import Customer
from apps.sales.models import Invoice
from apps.sales.serializers.sales_serializers import serialize_invoice
from apps.sales.services.sales_service import InvoiceService, _resolve_branch
from apps.settings_app.models import Branch, Company
from apps.settings_app.services.settings_service import SettingsService
from core.utils.media import resolve_product_image_url

DEFAULT_RETURN_POLICY = (
    "Items can be returned within 7 days with the original receipt. Terms and conditions apply."
)

PAYMENT_LABELS = {
    "cash": "Cash",
    "card": "Card",
    "mobile": "Mobile Money",
    "bank": "Bank Transfer",
    "split": "Split Payment",
    "on_account": "Pay Later / Account",
    "invoice": "Invoice",
}


def _parse_payment_from_notes(notes: str) -> tuple[str, str]:
    """Return (payment_method, payment_reference) parsed from invoice notes."""
    payment_method = "cash"
    payment_reference = ""
    if not notes:
        return payment_method, payment_reference

    method_match = re.search(r"Payment:\s*([a-z_]+)", notes, re.IGNORECASE)
    if method_match:
        payment_method = method_match.group(1).lower()

    ref_match = re.search(r"Ref:\s*([^|]+)", notes, re.IGNORECASE)
    if ref_match:
        payment_reference = ref_match.group(1).strip()

    return payment_method, payment_reference


def _pos_profile_key(user_id) -> str:
    return f"pos_profile_{user_id}"


def get_pos_profile(*, user):
    setting = SettingsService.get_by_key(key=_pos_profile_key(user.id))
    if setting:
        profile = setting.value if isinstance(setting.value, dict) else {}
    else:
        profile = {
            "merchants": [],
            "waiters": [],
            "default_payment_method": "cash",
            "receipt_footer": "Thank you for shopping with us! We appreciate your business.",
            "return_policy": DEFAULT_RETURN_POLICY,
        }

    # Merge shop-level waiters synced from cloud / shared across cashiers.
    shop_waiters_row = SettingsService.get_by_key(key="pos.waiters")
    shop_waiters = []
    if shop_waiters_row and shop_waiters_row.value:
        raw = shop_waiters_row.value
        if isinstance(raw, list):
            shop_waiters = raw
        elif isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    shop_waiters = parsed
            except (json.JSONDecodeError, TypeError):
                shop_waiters = []

    if shop_waiters:
        by_id = {str(w.get("id")): w for w in (profile.get("waiters") or []) if w.get("id")}
        for w in shop_waiters:
            wid = str(w.get("id") or "")
            if wid and wid in by_id:
                by_id[wid] = {**by_id[wid], **w}
            elif wid:
                by_id[wid] = w
            else:
                by_id[f"name:{(w.get('name') or '').lower()}"] = w
        profile = {**profile, "waiters": list(by_id.values())}
    elif "waiters" not in profile:
        profile["waiters"] = []

    return profile


def save_pos_profile(*, user, data):
    SettingsService.upsert(
        key=_pos_profile_key(user.id),
        value=data,
        category="pos",
        user=user,
    )
    # Keep shop-level waiters in sync for cloud push/pull.
    waiters = data.get("waiters") if isinstance(data, dict) else None
    if isinstance(waiters, list):
        SettingsService.upsert(
            key="pos.waiters",
            value=waiters,
            category="pos",
            user=user,
        )
    return data


def _resolve_walkin_customer(*, branch: Branch) -> Customer:
    customer = Customer.active_objects().filter(full_name__iexact="Walk-in Customer").first()
    if customer:
        return customer
    return Customer.objects.create(
        customer_code=f"WALKIN-{branch.code}",
        full_name="Walk-in Customer",
        email="",
        phone="",
        customer_type="retail",
        branch=branch,
        is_active=True,
    )


class PosService:
    @staticmethod
    @transaction.atomic
    def checkout(*, data, user):
        branch_id = data.get("branch_id")
        branch = _resolve_branch(branch_id)
        customer_id = data.get("customer_id")
        if customer_id and customer_id != "walkin":
            customer = Customer.active_objects().get(pk=customer_id)
        else:
            customer = _resolve_walkin_customer(branch=branch)

        items = data.get("items") or []
        if not items:
            raise ValueError("Cart is empty.")

        discount_pct = Decimal(str(data.get("discount_pct") or 0))
        discount_amount_raw = data.get("discount_amount")
        tax_rate = Decimal(str(data.get("tax_rate") or 0))
        payment_method = data.get("payment_method") or "cash"
        merchant_id = data.get("merchant_id")
        order_notes = data.get("notes") or ""
        amount_tendered = data.get("amount_tendered")
        payment_reference = (data.get("payment_reference") or "").strip()
        waiter_id = data.get("waiter_id")
        waiter_name = (data.get("waiter_name") or "").strip()

        profile = get_pos_profile(user=user)
        merchant = None
        for m in profile.get("merchants") or []:
            if m.get("id") == merchant_id:
                merchant = m
                break
        if not merchant and profile.get("merchants"):
            merchant = next((m for m in profile["merchants"] if m.get("is_default")), profile["merchants"][0])

        served_by_user = None
        if waiter_id:
            for w in profile.get("waiters") or []:
                if w.get("id") == waiter_id:
                    waiter_name = w.get("name") or waiter_name
                    linked_user_id = w.get("user_id")
                    if linked_user_id:
                        served_by_user = User.objects.filter(pk=linked_user_id, is_active=True).first()
                    break

        if payment_method == "on_account" and (not customer_id or customer_id == "walkin"):
            raise ValueError("Select a registered customer for pay-later / account sales.")

        if not waiter_id and not waiter_name:
            raise ValueError("Select a waiter before checkout.")

        parsed_items = [
            {
                "product_id": item["product_id"],
                "quantity": Decimal(str(item["quantity"])),
                "unit_price": Decimal(str(item["unit_price"])),
            }
            for item in items
        ]

        subtotal = sum(i["quantity"] * i["unit_price"] for i in parsed_items)
        if discount_amount_raw is not None and str(discount_amount_raw).strip() != "":
            discount_amount = min(subtotal, Decimal(str(discount_amount_raw)))
        else:
            discount_amount = subtotal * (discount_pct / Decimal("100"))
        after_discount = subtotal - discount_amount
        tax_amount = after_discount * tax_rate
        total_amount = after_discount + tax_amount

        payment_note = f"Payment: {payment_method}"
        if merchant:
            payment_note += f" | Merchant: {merchant.get('merchant_number', '')} ({merchant.get('company_name', '')})"
        if payment_reference:
            payment_note += f" | Ref: {payment_reference}"
        if waiter_name:
            payment_note += f" | Waiter: {waiter_name}"
        notes = f"{order_notes}\n{payment_note}".strip() if order_notes else payment_note

        is_on_account = payment_method == "on_account"
        invoice_status = Invoice.STATUS_SENT if is_on_account else Invoice.STATUS_PAID
        amount_paid = Decimal("0") if is_on_account else total_amount
        due_date = timezone.localdate() + timedelta(days=30) if is_on_account else None

        invoice = InvoiceService.create(
            data={
                "customer_id": str(customer.id),
                "branch_id": str(branch.id),
                "status": invoice_status,
                "issue_date": timezone.localdate(),
                "due_date": due_date,
                "discount_amount": discount_amount,
                "amount_paid": amount_paid,
                "notes": notes,
                "served_by_user": served_by_user,
            },
            items=parsed_items,
            user=user,
        )
        invoice.tax_amount = tax_amount
        invoice.total_amount = total_amount
        invoice.save(update_fields=["tax_amount", "total_amount", "updated_at"])
        invoice = InvoiceService.list().get(pk=invoice.pk)

        company = Company.active_objects().first()
        change = None
        if amount_tendered is not None and payment_method == "cash":
            change = float(Decimal(str(amount_tendered)) - total_amount)

        receipt = PosService.build_receipt(
            invoice=invoice,
            company=company,
            branch=branch,
            user=user,
            payment_method=payment_method,
            merchant=merchant,
            profile=profile,
            amount_tendered=amount_tendered,
            change=change,
            payment_reference=payment_reference,
            tax_rate=tax_rate,
            waiter_name=waiter_name,
        )
        return {"invoice": serialize_invoice(invoice, include_items=True), "receipt": receipt}

    @staticmethod
    def list_waiter_sales(
        *,
        user,
        waiter_id=None,
        user_id=None,
        branch_id=None,
        days=30,
        date_from=None,
        date_to=None,
        waiter_name=None,
    ):
        """List invoices served by a waiter (linked user or name in notes)."""
        branch = _resolve_branch(branch_id)
        if date_from or date_to:
            start = date_from or (timezone.localdate() - timedelta(days=30))
            end = date_to or timezone.localdate()
            if isinstance(start, str):
                from datetime import date as date_cls
                start = date_cls.fromisoformat(start)
            if isinstance(end, str):
                from datetime import date as date_cls
                end = date_cls.fromisoformat(end)
        else:
            start = timezone.localdate() - timedelta(days=max(1, int(days or 30)))
            end = timezone.localdate()

        qs = (
            Invoice.active_objects()
            .filter(branch=branch, issue_date__gte=start, issue_date__lte=end)
            .exclude(status=Invoice.STATUS_CANCELLED)
            .select_related("customer", "served_by_user", "created_by_user")
            .prefetch_related("items__product")
            .order_by("-issue_date", "-created_at")
        )

        profile = get_pos_profile(user=user)
        resolved_name = (waiter_name or "").strip()
        linked_user_id = user_id

        if waiter_id:
            for w in profile.get("waiters") or []:
                if w.get("id") == waiter_id:
                    resolved_name = (w.get("name") or "").strip() or resolved_name
                    linked_user_id = w.get("user_id") or linked_user_id
                    break

        if linked_user_id and resolved_name:
            qs = qs.filter(
                Q(served_by_user_id=linked_user_id)
                | Q(notes__icontains=f"Waiter: {resolved_name}")
            )
        elif linked_user_id:
            qs = qs.filter(served_by_user_id=linked_user_id)
        elif resolved_name:
            qs = qs.filter(notes__icontains=f"Waiter: {resolved_name}")
        else:
            return []

        results = []
        for inv in qs[:200]:
            pm, pref = _parse_payment_from_notes(inv.notes or "")
            results.append({
                "invoice_id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "customer_name": inv.customer.full_name,
                "status": inv.status,
                "payment_method": pm,
                "payment_method_label": PAYMENT_LABELS.get(pm, pm.title()),
                "total_amount": float(inv.total_amount),
                "amount_paid": float(inv.amount_paid),
                "balance_due": float(inv.total_amount - inv.amount_paid),
                "issue_date": inv.issue_date.isoformat(),
                "waiter_name": resolved_name or (
                    (inv.served_by_user.get_full_name() or inv.served_by_user.username)
                    if inv.served_by_user
                    else ""
                ),
                "items": [
                    {
                        "name": i.product.name,
                        "sku": i.product.sku,
                        "quantity": float(i.quantity),
                        "line_total": float(i.line_total),
                    }
                    for i in inv.items.all()
                ],
            })
        return results

    @staticmethod
    def waiter_performance(*, user, branch_id=None, date_from=None, date_to=None, waiter_id=None, waiter_name=None):
        """Aggregate paid / unpaid / on-account performance per waiter."""
        from datetime import date as date_cls

        branch = _resolve_branch(branch_id)
        end = date_to or timezone.localdate()
        start = date_from or (end - timedelta(days=30))
        if isinstance(start, str):
            start = date_cls.fromisoformat(start)
        if isinstance(end, str):
            end = date_cls.fromisoformat(end)

        profile = get_pos_profile(user=user)
        profile_waiters = [
            {
                "id": str(w.get("id") or ""),
                "name": (w.get("name") or "").strip(),
                "user_id": w.get("user_id") or None,
                "is_active": w.get("is_active", True),
            }
            for w in (profile.get("waiters") or [])
            if (w.get("name") or "").strip()
        ]

        invoices = (
            Invoice.active_objects()
            .filter(branch=branch, issue_date__gte=start, issue_date__lte=end)
            .exclude(status=Invoice.STATUS_CANCELLED)
            .select_related("customer", "served_by_user")
            .prefetch_related("items__product")
            .order_by("-issue_date", "-created_at")
        )

        def resolve_waiter(inv):
            if inv.served_by_user_id:
                # Prefer profile name for linked user
                for w in profile_waiters:
                    if w["user_id"] and str(w["user_id"]) == str(inv.served_by_user_id):
                        return w["name"], w["id"], w["user_id"]
                name = inv.served_by_user.get_full_name() or inv.served_by_user.username
                return name, "", str(inv.served_by_user_id)
            match = re.search(r"Waiter:\s*([^|\n]+)", inv.notes or "", re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                for w in profile_waiters:
                    if w["name"].lower() == name.lower():
                        return w["name"], w["id"], w["user_id"]
                return name, "", None
            return "", "", None

        buckets: dict[str, dict] = {}

        def ensure_bucket(name, wid="", uid=None):
            key = name.lower() if name else "__unassigned__"
            if key not in buckets:
                buckets[key] = {
                    "waiter_id": wid or "",
                    "waiter_name": name or "Unassigned",
                    "user_id": uid,
                    "receipts_count": 0,
                    "paid_count": 0,
                    "unpaid_count": 0,
                    "on_account_count": 0,
                    "total_served": Decimal("0"),
                    "paid_total": Decimal("0"),
                    "unpaid_total": Decimal("0"),
                    "items_sold": Decimal("0"),
                }
            elif wid and not buckets[key]["waiter_id"]:
                buckets[key]["waiter_id"] = wid
            elif uid and not buckets[key]["user_id"]:
                buckets[key]["user_id"] = uid
            return buckets[key]

        # Seed profile waiters so they appear even with zero sales
        for w in profile_waiters:
            if w.get("is_active", True):
                ensure_bucket(w["name"], w["id"], w["user_id"])

        all_receipts = []
        for inv in invoices:
            name, wid, uid = resolve_waiter(inv)
            if not name:
                continue
            pm, _ = _parse_payment_from_notes(inv.notes or "")
            is_paid = inv.status == Invoice.STATUS_PAID
            balance = inv.total_amount - inv.amount_paid
            b = ensure_bucket(name, wid, uid)
            b["receipts_count"] += 1
            b["total_served"] += inv.total_amount
            b["items_sold"] += sum((i.quantity for i in inv.items.all()), Decimal("0"))
            if is_paid:
                b["paid_count"] += 1
                b["paid_total"] += inv.total_amount
            else:
                b["unpaid_count"] += 1
                b["unpaid_total"] += balance
            if pm == "on_account" or (not is_paid and pm in ("on_account", "invoice")):
                b["on_account_count"] += 1

            all_receipts.append({
                "invoice_id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "customer_name": inv.customer.full_name,
                "status": inv.status,
                "payment_method": pm,
                "payment_method_label": PAYMENT_LABELS.get(pm, pm.title()),
                "total_amount": float(inv.total_amount),
                "amount_paid": float(inv.amount_paid),
                "balance_due": float(balance),
                "issue_date": inv.issue_date.isoformat(),
                "waiter_name": name,
                "waiter_id": wid,
                "items": [
                    {
                        "name": i.product.name,
                        "sku": i.product.sku,
                        "quantity": float(i.quantity),
                        "line_total": float(i.line_total),
                    }
                    for i in inv.items.all()
                ],
            })

        waiters = []
        for b in buckets.values():
            waiters.append({
                **b,
                "total_served": float(b["total_served"]),
                "paid_total": float(b["paid_total"]),
                "unpaid_total": float(b["unpaid_total"]),
                "items_sold": float(b["items_sold"]),
            })
        waiters.sort(key=lambda x: (-x["total_served"], x["waiter_name"].lower()))

        # Optional filter for detail
        selected_name = (waiter_name or "").strip()
        selected_id = waiter_id or ""
        if selected_id:
            for w in profile_waiters:
                if w["id"] == selected_id:
                    selected_name = w["name"]
                    break
        receipts = all_receipts
        if selected_name:
            receipts = [r for r in all_receipts if r["waiter_name"].lower() == selected_name.lower()]
            waiters = [w for w in waiters if w["waiter_name"].lower() == selected_name.lower()]

        return {
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
            "summary": {
                "waiters_count": len([w for w in waiters if w["waiter_name"] != "Unassigned" or w["receipts_count"]]),
                "receipts_count": sum(w["receipts_count"] for w in waiters),
                "paid_total": sum(w["paid_total"] for w in waiters),
                "unpaid_total": sum(w["unpaid_total"] for w in waiters),
                "on_account_count": sum(w["on_account_count"] for w in waiters),
                "total_served": sum(w["total_served"] for w in waiters),
            },
            "waiters": waiters,
            "receipts": receipts if (selected_name or selected_id) else [],
        }

    @staticmethod
    def build_receipt(
        *,
        invoice,
        company,
        branch,
        user,
        payment_method,
        merchant,
        profile,
        amount_tendered=None,
        change=None,
        payment_reference="",
        tax_rate=Decimal("0"),
        waiter_name="",
    ):
        now = timezone.localtime()
        after_discount = invoice.subtotal - invoice.discount_amount
        computed_tax_rate = float(tax_rate)
        if computed_tax_rate <= 0 and after_discount > 0 and invoice.tax_amount > 0:
            computed_tax_rate = float(invoice.tax_amount / after_discount)

        payment_guide = []
        amount_str = f"{float(invoice.total_amount):.2f}"
        for m in (profile.get("merchants") or [])[:6]:
            label = (m.get("label") or m.get("company_name") or "").strip()
            number = (m.get("merchant_number") or "").strip()
            if not label or not number:
                continue
            if "{amount}" in number:
                number = number.replace("{amount}", amount_str)
            elif number.startswith("*") and number.endswith("#"):
                core = number[:-1]
                if core.endswith("*"):
                    number = f"{core}{amount_str}#"
                elif not re.search(r"\*[\d.]+$", core):
                    number = f"{core}*{amount_str}#"
                else:
                    number = re.sub(r"\*[\d.]+$", f"*{amount_str}", core) + "#"
            elif number.startswith("*") and "#" not in number:
                number = (
                    f"{number}{amount_str}#"
                    if number.endswith("*")
                    else f"{number}*{amount_str}#"
                )
            payment_guide.append({"label": label, "number": number})

        is_paid = invoice.status == Invoice.STATUS_PAID

        return {
            "invoice_number": invoice.invoice_number,
            "invoice_id": str(invoice.id),
            "status": invoice.status,
            "is_paid": is_paid,
            "date": invoice.issue_date.isoformat(),
            "time": now.strftime("%H:%M"),
            "datetime_display": now.strftime("%d/%m/%Y %I:%M %p"),
            "cashier": user.get_full_name() or user.username,
            "waiter": waiter_name or (
                invoice.served_by_user.get_full_name()
                if getattr(invoice, "served_by_user", None)
                else ""
            ),
            "terminal": "POS-001",
            "customer_name": invoice.customer.full_name,
            "customer_address": invoice.customer.address or "",
            "customer_phone": invoice.customer.phone or "",
            "customer_email": invoice.customer.email or "",
            "company": {
                "name": company.name if company else branch.name,
                "legal_name": company.legal_name if company else "",
                "tax_id": company.tax_id if company else "",
                "email": company.email if company else "",
                "phone": company.phone if company else branch.phone,
                "address": company.address if company else branch.address,
                "logo": company.logo if company else "",
            },
            "branch": {
                "name": branch.name,
                "code": branch.code,
                "phone": branch.phone,
                "address": branch.address,
            },
            "merchant": merchant,
            "merchant_reference": merchant.get("merchant_number", "") if merchant else "",
            "payment_reference": payment_reference,
            "payment_guide": payment_guide,
            "items": [
                {
                    "name": i.product.name,
                    "sku": i.product.sku,
                    "quantity": float(i.quantity),
                    "unit_price": float(i.unit_price),
                    "line_total": float(i.line_total),
                    "image": resolve_product_image_url(i.product.image),
                }
                for i in invoice.items.select_related("product")
            ],
            "subtotal": float(invoice.subtotal),
            "discount_amount": float(invoice.discount_amount),
            "tax_amount": float(invoice.tax_amount),
            "tax_rate": computed_tax_rate,
            "total_amount": float(invoice.total_amount),
            "payment_method": payment_method,
            "payment_method_label": PAYMENT_LABELS.get(payment_method, payment_method.title()),
            "amount_tendered": float(amount_tendered) if amount_tendered is not None else None,
            "change": change,
            "footer": profile.get("receipt_footer") or "Thank you for your purchase!",
            "return_policy": profile.get("return_policy") or DEFAULT_RETURN_POLICY,
            "verification_path": f"/receipt/verify/{invoice.id}",
        }

    @staticmethod
    def receipt_from_invoice(*, invoice, user):
        """Build a printable receipt payload for an existing sales invoice."""
        branch = invoice.branch
        company = Company.active_objects().first()
        profile = get_pos_profile(user=user)
        payment_method, payment_reference = _parse_payment_from_notes(invoice.notes or "")
        if invoice.status == Invoice.STATUS_PAID and payment_method in ("invoice", "on_account"):
            payment_method = "cash"
        elif invoice.status != Invoice.STATUS_PAID and payment_method == "cash":
            payment_method = "invoice"

        cashier = user
        if getattr(invoice, "created_by_user", None):
            cashier = invoice.created_by_user

        after_discount = invoice.subtotal - invoice.discount_amount
        tax_rate = Decimal("0")
        if after_discount > 0 and invoice.tax_amount > 0:
            tax_rate = invoice.tax_amount / after_discount

        receipt = PosService.build_receipt(
            invoice=invoice,
            company=company,
            branch=branch,
            user=cashier,
            payment_method=payment_method,
            merchant=None,
            profile=profile,
            payment_reference=payment_reference,
            tax_rate=tax_rate,
        )

        created = timezone.localtime(invoice.created_at)
        receipt["date"] = invoice.issue_date.isoformat()
        receipt["time"] = created.strftime("%H:%M")
        receipt["datetime_display"] = created.strftime("%b %d, %Y · %I:%M %p")
        receipt["terminal"] = "SALES"
        return receipt

    @staticmethod
    def delivery_note_from_invoice(*, invoice, user):
        """Build a printable delivery note payload for a sales invoice."""
        branch = invoice.branch
        company = Company.active_objects().first()
        cashier = user
        if getattr(invoice, "created_by_user", None):
            cashier = invoice.created_by_user

        suffix = invoice.invoice_number.split("-")[-1]
        date_part = invoice.issue_date.strftime("%d%m%Y")
        vehicle_no = ""
        for part in (invoice.notes or "").split("|"):
            part = part.strip()
            if part.lower().startswith("vehicle:"):
                vehicle_no = part.split(":", 1)[-1].strip()
                break

        return {
            "delivery_number": f"DN-{date_part}-{suffix}",
            "order_number": f"ORD-{date_part}-{suffix}",
            "invoice_number": invoice.invoice_number,
            "invoice_id": str(invoice.id),
            "delivery_date": invoice.issue_date.isoformat(),
            "sales_person": cashier.get_full_name() or cashier.username,
            "vehicle_no": vehicle_no or "—",
            "customer_name": invoice.customer.full_name,
            "customer_address": invoice.customer.address or "",
            "customer_phone": invoice.customer.phone or "",
            "company": {
                "name": company.name if company else branch.name,
                "phone": company.phone if company else branch.phone,
                "email": company.email if company else "",
                "website": "www.mdaretail.com",
                "address": company.address if company else branch.address,
            },
            "branch": {
                "name": branch.name,
                "code": branch.code,
                "address": branch.address,
            },
            "items": [
                {
                    "name": i.product.name,
                    "sku": i.product.sku,
                    "quantity_ordered": float(i.quantity),
                    "quantity_delivered": float(i.quantity),
                    "unit": i.product.unit.name if getattr(i.product, "unit", None) else "Pcs",
                }
                for i in invoice.items.select_related("product", "product__unit")
            ],
        }
