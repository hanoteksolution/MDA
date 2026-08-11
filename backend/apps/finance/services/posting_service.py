"""Central Accounting Engine — event-driven posting to the general ledger."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from apps.finance.events import event_types
from apps.finance.models import AccountingEvent, JournalEntry
from apps.finance.services.chart_service import ChartService
from apps.finance.services.journal_service import JournalError, JournalService
from apps.finance.services.mapping_service import MappingService
from apps.finance.services.period_service import PeriodError, PeriodService


class PostingError(ValueError):
    pass


MONEY = Decimal("0.01")


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def _payment_mapping_key(method: str) -> str:
    method = (method or "cash").strip().lower()
    if method == "on_account":
        return "DEFAULT_RECEIVABLE"
    if method in ("card", "bank", "transfer"):
        return "DEFAULT_BANK"
    if method in ("mobile", "mobile_money"):
        return "DEFAULT_MOBILE_MONEY"
    return "DEFAULT_CASH"


def _compute_invoice_cost(invoice) -> Decimal:
    total = Decimal("0")
    for item in invoice.items.select_related("product"):
        cost = getattr(item.product, "cost_price", None) or Decimal("0")
        total += Decimal(str(cost)) * Decimal(str(item.quantity))
    return _money(total)


def _compute_refund_cost(refund) -> Decimal:
    total = Decimal("0")
    for item in refund.items.select_related("product"):
        cost = getattr(item.product, "cost_price", None) or Decimal("0")
        total += Decimal(str(cost)) * Decimal(str(item.quantity))
    return _money(total)


def _receive_idempotency_key(*, purchase_order_id, lines) -> str:
    parts = sorted(
        f"{line.product_id}:{Decimal(str(line.quantity_received))}" for line in lines
    )
    return f"PURCHASE_RECEIVED:purchases:po:{purchase_order_id}:{'|'.join(parts)}"


class AccountingPostingService:
    @staticmethod
    @transaction.atomic
    def post(
        *,
        event_type: str,
        tenant_id,
        source_module: str,
        source_type: str,
        source_id,
        payload: dict,
        idempotency_key: str,
        source_reference: str = "",
        occurred_at=None,
        user=None,
        branch_id=None,
    ) -> JournalEntry:
        from apps.finance.services.cutover_service import AccountingCutoverService

        if not AccountingCutoverService.is_posting_enabled(tenant_id=tenant_id):
            raise PostingError("Accounting posting is disabled for this tenant.")
        if not tenant_id:
            raise PostingError("Tenant could not be resolved.")
        if not idempotency_key:
            raise PostingError("idempotency_key is required.")

        existing_event = (
            AccountingEvent.active_objects()
            .filter(tenant_id=tenant_id, idempotency_key=idempotency_key)
            .select_related("journal_entry")
            .first()
        )
        if existing_event and existing_event.status == AccountingEvent.STATUS_POSTED:
            if existing_event.journal_entry_id:
                return existing_event.journal_entry
        if existing_event is None:
            existing_event = AccountingEvent.objects.create(
                tenant_id=tenant_id,
                event_type=event_type,
                source_module=source_module,
                source_type=source_type,
                source_id=source_id,
                source_reference=source_reference,
                idempotency_key=idempotency_key,
                occurred_at=occurred_at or timezone.now(),
                payload=payload,
                status=AccountingEvent.STATUS_PROCESSING,
                created_by=user,
            )
        else:
            existing_event.status = AccountingEvent.STATUS_PROCESSING
            existing_event.retry_count += 1
            existing_event.error = ""
            existing_event.save(update_fields=["status", "retry_count", "error", "updated_at"])

        existing_journal = JournalEntry.active_objects().filter(
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            status=JournalEntry.STATUS_POSTED,
        ).first()
        if existing_journal:
            AccountingPostingService._mark_posted(existing_event, existing_journal)
            return existing_journal

        ChartService.ensure_default_chart(tenant_id=tenant_id, user=user)
        MappingService.seed_defaults(tenant_id=tenant_id, user=user)
        from apps.finance.services.posting_rule_service import PostingRuleService

        PostingRuleService.seed_defaults(tenant_id=tenant_id, user=user)

        try:
            period = PeriodService.resolve(
                tenant_id=tenant_id,
                on_date=payload.get("entry_date") or occurred_at,
                user=user,
            )
        except PeriodError as exc:
            AccountingPostingService._mark_failed(existing_event, str(exc))
            raise PostingError(str(exc)) from exc

        try:
            lines, description, entry_date = AccountingPostingService._build_lines(
                event_type=event_type,
                tenant_id=tenant_id,
                payload=payload,
                user=user,
            )
            journal_source_type = AccountingPostingService._journal_source_type(source_type)
            entry = JournalService.create_entry(
                data={
                    "tenant_id": tenant_id,
                    "entry_date": entry_date,
                    "description": description,
                    "source_type": journal_source_type,
                    "source_module": source_module,
                    "source_id": source_id,
                    "source_reference": source_reference,
                    "idempotency_key": idempotency_key,
                    "branch_id": branch_id,
                    "financial_period_id": period.id,
                    "lines": lines,
                },
                user=user,
            )
        except (JournalError, PostingError) as exc:
            AccountingPostingService._mark_failed(existing_event, str(exc))
            raise PostingError(str(exc)) from exc

        AccountingPostingService._mark_posted(existing_event, entry)
        return entry

    @staticmethod
    def _journal_source_type(source_type: str) -> str:
        mapping = {
            "expense": JournalEntry.SOURCE_EXPENSE,
            "invoice": JournalEntry.SOURCE_INVOICE,
            "booking": JournalEntry.SOURCE_INVOICE,
            "payment": JournalEntry.SOURCE_PAYMENT,
            "supplier_payment": JournalEntry.SOURCE_PAYMENT,
            "sale_refund": JournalEntry.SOURCE_REFUND,
            "travel_refund": JournalEntry.SOURCE_REFUND,
            "purchase_receive": JournalEntry.SOURCE_PURCHASE,
            "futsal_ledger": JournalEntry.SOURCE_FUTSAL,
        }
        return mapping.get(source_type, JournalEntry.SOURCE_MANUAL)

    @staticmethod
    def _build_lines(*, event_type, tenant_id, payload, user):
        from apps.finance.services.posting_rule_service import (
            PostingRuleError,
            PostingRuleService,
        )

        # Prefer configurable PostingRule when seeded for this event type
        try:
            built = PostingRuleService.try_build_lines(
                event_type=event_type,
                tenant_id=tenant_id,
                payload=payload,
                user=user,
            )
            if built is not None:
                return built
        except PostingRuleError as exc:
            raise PostingError(str(exc)) from exc

        if event_type == event_types.EXPENSE_APPROVED:
            return AccountingPostingService._lines_for_expense(
                tenant_id=tenant_id, payload=payload, user=user
            )
        if event_type == event_types.SALE_COMPLETED:
            return AccountingPostingService._lines_for_sale(
                tenant_id=tenant_id, payload=payload, user=user
            )
        if event_type == event_types.PHARMACY_SALE_COMPLETED:
            pharm_payload = {
                **payload,
                "revenue_mapping_key": payload.get("revenue_mapping_key")
                or "PHARMACY_SALES_REVENUE",
            }
            return AccountingPostingService._lines_for_sale(
                tenant_id=tenant_id, payload=pharm_payload, user=user
            )
        if event_type == event_types.SALE_REFUNDED:
            return AccountingPostingService._lines_for_refund(
                tenant_id=tenant_id, payload=payload, user=user
            )
        if event_type == event_types.PURCHASE_RECEIVED:
            return AccountingPostingService._lines_for_purchase_received(
                tenant_id=tenant_id, payload=payload, user=user
            )
        if event_type == event_types.GYM_MEMBERSHIP_SOLD:
            gym_payload = {
                **payload,
                "revenue_mapping_key": "GYM_MEMBERSHIP_REVENUE",
                "cost_total": payload.get("cost_total", "0"),
            }
            return AccountingPostingService._lines_for_sale(
                tenant_id=tenant_id, payload=gym_payload, user=user
            )
        if event_type == event_types.GYM_SERVICE_SOLD:
            gym_payload = {
                **payload,
                "revenue_mapping_key": payload.get("revenue_mapping_key")
                or "GYM_PERSONAL_TRAINING_REVENUE",
                "cost_total": payload.get("cost_total", "0"),
            }
            return AccountingPostingService._lines_for_sale(
                tenant_id=tenant_id, payload=gym_payload, user=user
            )
        if event_type == event_types.CUSTOMER_PAYMENT_RECEIVED:
            return AccountingPostingService._lines_for_customer_payment(
                tenant_id=tenant_id, payload=payload, user=user
            )
        if event_type == event_types.PROJECT_INVOICE_ISSUED:
            return AccountingPostingService._lines_for_project_invoice(
                tenant_id=tenant_id, payload=payload, user=user
            )
        if event_type == event_types.TRAVEL_BOOKING_CONFIRMED:
            return AccountingPostingService._lines_for_travel_booking(
                tenant_id=tenant_id, payload=payload, user=user
            )
        if event_type == event_types.TRAVEL_PAYMENT_RECEIVED:
            return AccountingPostingService._lines_for_customer_payment(
                tenant_id=tenant_id, payload=payload, user=user
            )
        if event_type == event_types.TRAVEL_REFUND_ISSUED:
            return AccountingPostingService._lines_for_travel_refund(
                tenant_id=tenant_id, payload=payload, user=user
            )
        if event_type == event_types.SUPPLIER_PAYMENT_COMPLETED:
            return AccountingPostingService._lines_for_supplier_payment(
                tenant_id=tenant_id, payload=payload, user=user
            )
        if event_type in (
            event_types.FUTSAL_INCOME_RECORDED,
            event_types.FUTSAL_EXPENSE_RECORDED,
        ):
            return AccountingPostingService._lines_for_futsal(
                event_type=event_type, tenant_id=tenant_id, payload=payload, user=user
            )
        raise PostingError(f"Unsupported accounting event type: {event_type}")

    @staticmethod
    def _lines_for_expense(*, tenant_id, payload, user):
        category = payload.get("category") or "other"
        amount = Decimal(str(payload.get("amount") or 0))
        if amount <= 0:
            raise PostingError("Expense amount must be positive.")
        expense_key = MappingService.expense_mapping_key(category)
        expense_account = MappingService.resolve(key=expense_key, tenant_id=tenant_id, user=user)
        cash_account = MappingService.resolve(key="DEFAULT_CASH", tenant_id=tenant_id, user=user)
        description = payload.get("description") or f"Expense: {category}"
        entry_date = payload.get("entry_date") or timezone.localdate()
        lines = [
            {
                "account_id": str(expense_account.id),
                "debit": amount,
                "credit": Decimal("0"),
                "memo": category,
            },
            {
                "account_id": str(cash_account.id),
                "debit": Decimal("0"),
                "credit": amount,
                "memo": "Cash out",
            },
        ]
        return lines, f"Expense: {description}", entry_date

    @staticmethod
    def _lines_for_project_invoice(*, tenant_id, payload, user):
        """Dr Accounts Receivable, Cr Project/Sales Revenue (+ tax payable when taxed)."""
        total_amount = _money(payload.get("total_amount") or 0)
        amount = _money(payload.get("amount") or total_amount)
        tax_amount = _money(payload.get("tax_amount") or 0)
        if total_amount <= 0:
            raise PostingError("Project invoice total must be positive.")
        if abs(total_amount - (amount + tax_amount)) > Decimal("0.02"):
            # Prefer explicit total; rebuild amount if tax missing.
            if tax_amount == 0 and amount == total_amount:
                pass
            elif tax_amount == 0:
                amount = total_amount
            else:
                amount = total_amount - tax_amount

        ar = MappingService.resolve(key="DEFAULT_RECEIVABLE", tenant_id=tenant_id, user=user)
        revenue_key = payload.get("revenue_mapping_key") or "DEFAULT_SALES_REVENUE"
        revenue = MappingService.resolve(key=revenue_key, tenant_id=tenant_id, user=user)
        invoice_number = payload.get("invoice_number") or ""
        entry_date = payload.get("entry_date") or timezone.localdate()
        cost_center_id = payload.get("cost_center_id")

        lines = [
            {
                "account_id": str(ar.id),
                "debit": total_amount,
                "credit": Decimal("0"),
                "memo": f"AR {invoice_number}".strip(),
                "cost_center_id": cost_center_id,
            },
            {
                "account_id": str(revenue.id),
                "debit": Decimal("0"),
                "credit": amount,
                "memo": f"Project revenue {invoice_number}".strip(),
                "cost_center_id": cost_center_id,
            },
        ]
        if tax_amount > 0:
            tax = MappingService.resolve(key="DEFAULT_TAX_PAYABLE", tenant_id=tenant_id, user=user)
            lines.append(
                {
                    "account_id": str(tax.id),
                    "debit": Decimal("0"),
                    "credit": tax_amount,
                    "memo": f"Tax {invoice_number}".strip(),
                    "cost_center_id": cost_center_id,
                }
            )
        description = payload.get("description") or f"Project invoice {invoice_number}".strip()
        return lines, description[:255], entry_date

    @staticmethod
    def _lines_for_travel_booking(*, tenant_id, payload, user):
        """Dr Accounts Receivable, Cr travel sales revenue."""
        total_amount = _money(payload.get("total_amount") or 0)
        if total_amount <= 0:
            raise PostingError("Travel booking total must be positive.")
        ar = MappingService.resolve(key="DEFAULT_RECEIVABLE", tenant_id=tenant_id, user=user)
        revenue = MappingService.resolve(
            key=payload.get("revenue_mapping_key") or "DEFAULT_SALES_REVENUE",
            tenant_id=tenant_id, user=user,
        )
        number = payload.get("booking_code") or ""
        entry_date = payload.get("entry_date") or timezone.localdate()
        return [
            {"account_id": str(ar.id), "debit": total_amount, "credit": Decimal("0"), "memo": f"AR {number}".strip()},
            {"account_id": str(revenue.id), "debit": Decimal("0"), "credit": total_amount, "memo": f"Travel revenue {number}".strip()},
        ], (payload.get("description") or f"Travel booking {number}")[:255], entry_date

    @staticmethod
    def _lines_for_sale(*, tenant_id, payload, user):
        total_amount = _money(payload.get("total_amount") or 0)
        if total_amount <= 0:
            raise PostingError("Sale total must be positive.")

        cost_total = _money(payload.get("cost_total") or 0)
        payment_method = (payload.get("payment_method") or "cash").strip().lower()
        tenders = payload.get("payments") or []
        revenue_key = payload.get("revenue_mapping_key") or "DEFAULT_SALES_REVENUE"
        revenue_account = MappingService.resolve(key=revenue_key, tenant_id=tenant_id, user=user)

        lines = []
        debit_total = Decimal("0")

        if payment_method == "on_account" and not tenders:
            ar = MappingService.resolve(key="DEFAULT_RECEIVABLE", tenant_id=tenant_id, user=user)
            lines.append(
                {
                    "account_id": str(ar.id),
                    "debit": total_amount,
                    "credit": Decimal("0"),
                    "memo": "On account sale",
                }
            )
            debit_total = total_amount
        elif payment_method == "on_account" and tenders:
            for row in tenders:
                amount = _money(row.get("amount") or 0)
                if amount <= 0:
                    continue
                method = (row.get("method") or "on_account").strip().lower()
                asset = MappingService.resolve(
                    key=_payment_mapping_key(method), tenant_id=tenant_id, user=user
                )
                lines.append(
                    {
                        "account_id": str(asset.id),
                        "debit": amount,
                        "credit": Decimal("0"),
                        "memo": method,
                    }
                )
                debit_total += amount
            if debit_total < total_amount:
                remainder = _money(total_amount - debit_total)
                ar = MappingService.resolve(key="DEFAULT_RECEIVABLE", tenant_id=tenant_id, user=user)
                lines.append(
                    {
                        "account_id": str(ar.id),
                        "debit": remainder,
                        "credit": Decimal("0"),
                        "memo": "On account balance",
                    }
                )
                debit_total += remainder
        elif payment_method == "split" and tenders:
            for row in tenders:
                amount = _money(row.get("amount") or 0)
                if amount <= 0:
                    continue
                method = (row.get("method") or "cash").strip().lower()
                asset = MappingService.resolve(
                    key=_payment_mapping_key(method), tenant_id=tenant_id, user=user
                )
                lines.append(
                    {
                        "account_id": str(asset.id),
                        "debit": amount,
                        "credit": Decimal("0"),
                        "memo": method,
                    }
                )
                debit_total += amount
        else:
            asset = MappingService.resolve(
                key=_payment_mapping_key(payment_method), tenant_id=tenant_id, user=user
            )
            lines.append(
                {
                    "account_id": str(asset.id),
                    "debit": total_amount,
                    "credit": Decimal("0"),
                    "memo": payment_method,
                }
            )
            debit_total = total_amount

        if debit_total != total_amount:
            raise PostingError(
                f"Sale debit total ({debit_total}) does not match total ({total_amount})."
            )

        tax_amount = _money(payload.get("tax_amount") or 0)
        if tax_amount < 0:
            raise PostingError("Tax amount cannot be negative.")
        if tax_amount > total_amount:
            raise PostingError("Tax amount cannot exceed sale total.")

        revenue_amount = _money(total_amount - tax_amount)
        if revenue_amount > 0:
            lines.append(
                {
                    "account_id": str(revenue_account.id),
                    "debit": Decimal("0"),
                    "credit": revenue_amount,
                    "memo": "Sales revenue",
                }
            )
        if tax_amount > 0:
            tax_account = MappingService.resolve(
                key="DEFAULT_TAX_PAYABLE", tenant_id=tenant_id, user=user
            )
            lines.append(
                {
                    "account_id": str(tax_account.id),
                    "debit": Decimal("0"),
                    "credit": tax_amount,
                    "memo": "Sales tax",
                }
            )

        if cost_total > 0:
            cogs = MappingService.resolve(key="DEFAULT_COGS", tenant_id=tenant_id, user=user)
            inventory = MappingService.resolve(
                key="DEFAULT_INVENTORY", tenant_id=tenant_id, user=user
            )
            lines.extend(
                [
                    {
                        "account_id": str(cogs.id),
                        "debit": cost_total,
                        "credit": Decimal("0"),
                        "memo": "COGS",
                    },
                    {
                        "account_id": str(inventory.id),
                        "debit": Decimal("0"),
                        "credit": cost_total,
                        "memo": "Inventory",
                    },
                ]
            )

        entry_date = payload.get("entry_date") or timezone.localdate()
        invoice_number = payload.get("invoice_number") or "POS sale"
        return lines, f"Sale: {invoice_number}", entry_date

    @staticmethod
    def _lines_for_refund(*, tenant_id, payload, user):
        refund_amount = _money(payload.get("refund_amount") or 0)
        if refund_amount <= 0:
            raise PostingError("Refund amount must be positive.")

        cost_total = _money(payload.get("cost_total") or 0)
        payment_method = (payload.get("payment_method") or "cash").strip().lower()
        restore_inventory = payload.get("restore_inventory", True)
        tax_amount = _money(payload.get("tax_amount") or 0)
        if tax_amount < 0:
            raise PostingError("Tax amount cannot be negative.")
        if tax_amount > refund_amount:
            raise PostingError("Tax amount cannot exceed refund total.")

        returns_account = MappingService.resolve(
            key="DEFAULT_SALES_RETURNS", tenant_id=tenant_id, user=user
        )
        asset = MappingService.resolve(
            key=_payment_mapping_key(payment_method), tenant_id=tenant_id, user=user
        )

        net_return = _money(refund_amount - tax_amount)
        lines = []
        if net_return > 0:
            lines.append(
                {
                    "account_id": str(returns_account.id),
                    "debit": net_return,
                    "credit": Decimal("0"),
                    "memo": "Sales return",
                }
            )
        if tax_amount > 0:
            tax_account = MappingService.resolve(
                key="DEFAULT_TAX_PAYABLE", tenant_id=tenant_id, user=user
            )
            lines.append(
                {
                    "account_id": str(tax_account.id),
                    "debit": tax_amount,
                    "credit": Decimal("0"),
                    "memo": "Sales tax reversal",
                }
            )
        lines.append(
            {
                "account_id": str(asset.id),
                "debit": Decimal("0"),
                "credit": refund_amount,
                "memo": payment_method,
            }
        )

        if restore_inventory and cost_total > 0:
            inventory = MappingService.resolve(
                key="DEFAULT_INVENTORY", tenant_id=tenant_id, user=user
            )
            cogs = MappingService.resolve(key="DEFAULT_COGS", tenant_id=tenant_id, user=user)
            lines.extend(
                [
                    {
                        "account_id": str(inventory.id),
                        "debit": cost_total,
                        "credit": Decimal("0"),
                        "memo": "Inventory restored",
                    },
                    {
                        "account_id": str(cogs.id),
                        "debit": Decimal("0"),
                        "credit": cost_total,
                        "memo": "COGS reversal",
                    },
                ]
            )

        entry_date = payload.get("entry_date") or timezone.localdate()
        refund_number = payload.get("refund_number") or "Refund"
        return lines, f"Refund: {refund_number}", entry_date

    @staticmethod
    def _lines_for_purchase_received(*, tenant_id, payload, user):
        receive_total = _money(payload.get("receive_total") or 0)
        if receive_total <= 0:
            raise PostingError("Receive total must be positive.")

        inventory = MappingService.resolve(
            key="DEFAULT_INVENTORY", tenant_id=tenant_id, user=user
        )
        payable = MappingService.resolve(key="DEFAULT_PAYABLE", tenant_id=tenant_id, user=user)

        lines = [
            {
                "account_id": str(inventory.id),
                "debit": receive_total,
                "credit": Decimal("0"),
                "memo": "Goods received",
            },
            {
                "account_id": str(payable.id),
                "debit": Decimal("0"),
                "credit": receive_total,
                "memo": "Accounts payable",
            },
        ]
        entry_date = payload.get("entry_date") or timezone.localdate()
        order_number = payload.get("order_number") or "PO receive"
        return lines, f"Purchase received: {order_number}", entry_date

    @staticmethod
    def _lines_for_futsal(*, event_type, tenant_id, payload, user):
        amount = _money(payload.get("amount") or 0)
        if amount <= 0:
            raise PostingError("Futsal amount must be positive.")

        method = (payload.get("payment_method") or "cash").strip().lower()
        cash = MappingService.resolve(
            key=_payment_mapping_key(method), tenant_id=tenant_id, user=user
        )
        category = payload.get("category") or ""
        entry_date = payload.get("entry_date") or timezone.localdate()
        label = payload.get("description") or category or "Futsal"

        if event_type == event_types.FUTSAL_INCOME_RECORDED:
            revenue = MappingService.resolve(
                key="FUTSAL_REVENUE", tenant_id=tenant_id, user=user
            )
            lines = [
                {
                    "account_id": str(cash.id),
                    "debit": amount,
                    "credit": Decimal("0"),
                    "memo": method,
                },
                {
                    "account_id": str(revenue.id),
                    "debit": Decimal("0"),
                    "credit": amount,
                    "memo": category or "Futsal income",
                },
            ]
            return lines, f"Futsal income: {label}"[:255], entry_date

        expense = MappingService.resolve(key="FUTSAL_EXPENSE", tenant_id=tenant_id, user=user)
        lines = [
            {
                "account_id": str(expense.id),
                "debit": amount,
                "credit": Decimal("0"),
                "memo": category or "Futsal expense",
            },
            {
                "account_id": str(cash.id),
                "debit": Decimal("0"),
                "credit": amount,
                "memo": method,
            },
        ]
        return lines, f"Futsal expense: {label}"[:255], entry_date

    @staticmethod
    def _lines_for_customer_payment(*, tenant_id, payload, user):
        amount = _money(payload.get("amount") or 0)
        if amount <= 0:
            raise PostingError("Customer payment amount must be positive.")

        method = (payload.get("payment_method") or "cash").strip().lower()
        asset = MappingService.resolve(
            key=_payment_mapping_key(method), tenant_id=tenant_id, user=user
        )
        ar = MappingService.resolve(key="DEFAULT_RECEIVABLE", tenant_id=tenant_id, user=user)

        lines = [
            {
                "account_id": str(asset.id),
                "debit": amount,
                "credit": Decimal("0"),
                "memo": method,
            },
            {
                "account_id": str(ar.id),
                "debit": Decimal("0"),
                "credit": amount,
                "memo": "AR settlement",
            },
        ]
        entry_date = payload.get("entry_date") or timezone.localdate()
        ref = payload.get("invoice_number") or "Customer receipt"
        return lines, f"Customer receipt: {ref}", entry_date

    @staticmethod
    def _lines_for_travel_refund(*, tenant_id, payload, user):
        amount = _money(payload.get("amount") or 0)
        if amount <= 0:
            raise PostingError("Travel refund amount must be positive.")
        asset = MappingService.resolve(key=_payment_mapping_key(payload.get("payment_method") or "cash"), tenant_id=tenant_id, user=user)
        ar = MappingService.resolve(key="DEFAULT_RECEIVABLE", tenant_id=tenant_id, user=user)
        lines = [
            {"account_id": str(ar.id), "debit": amount, "credit": Decimal("0"), "memo": "Travel refund reversal"},
            {"account_id": str(asset.id), "debit": Decimal("0"), "credit": amount, "memo": "Travel refund paid"},
        ]
        return lines, f"Travel refund: {payload.get('booking_code') or ''}", payload.get("entry_date") or timezone.localdate()

    @staticmethod
    def _lines_for_supplier_payment(*, tenant_id, payload, user):
        amount = _money(payload.get("amount") or 0)
        if amount <= 0:
            raise PostingError("Supplier payment amount must be positive.")

        method = (payload.get("payment_method") or "cash").strip().lower()
        asset = MappingService.resolve(
            key=_payment_mapping_key(method), tenant_id=tenant_id, user=user
        )
        ap = MappingService.resolve(key="DEFAULT_PAYABLE", tenant_id=tenant_id, user=user)

        lines = [
            {
                "account_id": str(ap.id),
                "debit": amount,
                "credit": Decimal("0"),
                "memo": "AP settlement",
            },
            {
                "account_id": str(asset.id),
                "debit": Decimal("0"),
                "credit": amount,
                "memo": method,
            },
        ]
        entry_date = payload.get("entry_date") or timezone.localdate()
        ref = payload.get("order_number") or "Supplier payment"
        return lines, f"Supplier payment: {ref}", entry_date

    @staticmethod
    def _mark_posted(event: AccountingEvent, entry: JournalEntry):
        event.status = AccountingEvent.STATUS_POSTED
        event.journal_entry = entry
        event.processed_at = timezone.now()
        event.error = ""
        event.save(
            update_fields=["status", "journal_entry", "processed_at", "error", "updated_at"]
        )

    @staticmethod
    def _mark_failed(event: AccountingEvent, message: str):
        event.status = AccountingEvent.STATUS_FAILED
        event.error = message[:2000]
        event.processed_at = timezone.now()
        event.save(update_fields=["status", "error", "processed_at", "updated_at"])

    @staticmethod
    @transaction.atomic
    def post_expense(*, expense, user=None, revision: int | None = None) -> JournalEntry | None:
        """Bridge from sales.Expense — preserves STEP 21 behavior via posting engine."""
        from apps.finance.services.cutover_service import AccountingCutoverService

        tenant_id = expense.tenant_id or getattr(expense.branch, "tenant_id", None)
        if not tenant_id:
            return None
        if not AccountingCutoverService.is_posting_enabled(tenant_id=tenant_id):
            return None
        if revision is None:
            idempotency_key = f"EXPENSE_APPROVED:sales:expense:{expense.id}"
        else:
            idempotency_key = f"EXPENSE_APPROVED:sales:expense:{expense.id}:v{revision}"
        return AccountingPostingService.post(
            event_type=event_types.EXPENSE_APPROVED,
            tenant_id=tenant_id,
            source_module="sales",
            source_type="expense",
            source_id=expense.id,
            source_reference=getattr(expense, "description", "")[:100],
            payload={
                "amount": str(expense.amount),
                "category": expense.category,
                "description": expense.description,
                "entry_date": expense.expense_date.isoformat()
                if hasattr(expense.expense_date, "isoformat")
                else expense.expense_date,
            },
            idempotency_key=idempotency_key,
            occurred_at=timezone.now(),
            user=user,
            branch_id=expense.branch_id,
        )

    @staticmethod
    @transaction.atomic
    def post_project_invoice(*, invoice, user=None) -> JournalEntry | None:
        """Post project billing invoice — Dr AR, Cr Revenue (+ tax)."""
        from apps.finance.services.cutover_service import AccountingCutoverService

        if invoice.status not in ("issued", "paid"):
            raise PostingError("Only issued or paid project invoices can be posted to the ledger.")

        tenant_id = invoice.tenant_id or getattr(getattr(invoice, "project", None), "tenant_id", None)
        if not tenant_id:
            raise PostingError("Tenant could not be resolved for project invoice.")
        if not AccountingCutoverService.is_posting_enabled(tenant_id=tenant_id):
            raise PostingError("Accounting posting is disabled for this tenant.")

        project = invoice.project
        branch_id = getattr(project, "branch_id", None)
        cost_center_id = getattr(project, "cost_center_id", None)
        idempotency_key = f"PROJECT_INVOICE_ISSUED:project_management:invoice:{invoice.id}"
        payload = {
            "amount": str(invoice.amount or 0),
            "tax_amount": str(invoice.tax_amount or 0),
            "total_amount": str(invoice.total_amount or 0),
            "invoice_number": invoice.invoice_number,
            "description": f"Project invoice {invoice.invoice_number}",
            "entry_date": invoice.invoice_date.isoformat()
            if hasattr(invoice.invoice_date, "isoformat")
            else invoice.invoice_date,
            "cost_center_id": str(cost_center_id) if cost_center_id else None,
            "revenue_mapping_key": "DEFAULT_SALES_REVENUE",
        }
        return AccountingPostingService.post(
            event_type=event_types.PROJECT_INVOICE_ISSUED,
            tenant_id=tenant_id,
            source_module="project_management",
            source_type="invoice",
            source_id=invoice.id,
            source_reference=invoice.invoice_number,
            payload=payload,
            idempotency_key=idempotency_key,
            occurred_at=timezone.now(),
            user=user,
            branch_id=branch_id,
        )

    @staticmethod
    @transaction.atomic
    def post_travel_booking(*, booking, user=None) -> JournalEntry | None:
        """Post a confirmed travel booking — Dr AR, Cr revenue."""
        from apps.finance.services.cutover_service import AccountingCutoverService
        if booking.status not in ("confirmed", "completed"):
            raise PostingError("Only confirmed or completed travel bookings can be posted to the ledger.")
        tenant_id = booking.tenant_id or getattr(booking.branch, "tenant_id", None)
        if not tenant_id:
            raise PostingError("Tenant could not be resolved for travel booking.")
        if not AccountingCutoverService.is_posting_enabled(tenant_id=tenant_id):
            raise PostingError("Accounting posting is disabled for this tenant.")
        return AccountingPostingService.post(
            event_type=event_types.TRAVEL_BOOKING_CONFIRMED, tenant_id=tenant_id,
            source_module="travel_agency", source_type="booking", source_id=booking.id,
            source_reference=booking.booking_code,
            payload={"total_amount": str(booking.total_amount or 0), "booking_code": booking.booking_code,
                     "description": f"Travel booking {booking.booking_code}",
                     "entry_date": booking.travel_date.isoformat() if booking.travel_date else timezone.localdate().isoformat(),
                     "revenue_mapping_key": "DEFAULT_SALES_REVENUE"},
            idempotency_key=f"TRAVEL_BOOKING_CONFIRMED:travel_agency:booking:{booking.id}",
            occurred_at=timezone.now(), user=user, branch_id=booking.branch_id,
        )

    @staticmethod
    def post_travel_payment(*, payment, user=None) -> JournalEntry:
        booking = payment.booking
        return AccountingPostingService.post(
            event_type=event_types.TRAVEL_PAYMENT_RECEIVED, tenant_id=booking.tenant_id,
            source_module="travel_agency", source_type="payment", source_id=payment.id,
            source_reference=payment.reference or booking.booking_code,
            payload={"amount": str(payment.amount), "payment_method": payment.method,
                     "booking_code": booking.booking_code, "entry_date": payment.paid_at.date().isoformat()},
            idempotency_key=f"TRAVEL_PAYMENT_RECEIVED:travel_agency:payment:{payment.id}",
            occurred_at=payment.paid_at, user=user, branch_id=booking.branch_id,
        )

    @staticmethod
    def post_travel_refund(*, refund, user=None) -> JournalEntry:
        booking = refund.booking
        method = refund.payment.method if refund.payment_id else "cash"
        return AccountingPostingService.post(
            event_type=event_types.TRAVEL_REFUND_ISSUED, tenant_id=booking.tenant_id,
            source_module="travel_agency", source_type="travel_refund", source_id=refund.id,
            source_reference=booking.booking_code,
            payload={"amount": str(refund.amount), "payment_method": method,
                     "booking_code": booking.booking_code, "entry_date": refund.refunded_at.date().isoformat()},
            idempotency_key=f"TRAVEL_REFUND_ISSUED:travel_agency:refund:{refund.id}",
            occurred_at=refund.refunded_at, user=user, branch_id=booking.branch_id,
        )

    @staticmethod
    @transaction.atomic
    def post_sale(
        *,
        invoice,
        user=None,
        payment_method=None,
        tender_lines=None,
        revenue_mapping_key=None,
        event_type=None,
        source_module=None,
    ) -> JournalEntry | None:
        """Post POS/invoice sale — Dr Cash/AR, Cr Revenue; Dr COGS, Cr Inventory.

        Pharmacy POS (module profile) uses PHARMACY_SALE_COMPLETED + PHARMACY_SALES_REVENUE
        with source_module=pharmacy so BusinessUnit stamps PHARM — same CAE, no parallel ledger.
        """
        from apps.finance.services.cutover_service import AccountingCutoverService
        from apps.sales.models import Invoice

        if invoice.status not in (Invoice.STATUS_PAID, Invoice.STATUS_SENT):
            return None

        tenant_id = invoice.tenant_id or getattr(invoice.branch, "tenant_id", None)
        if not tenant_id:
            return None
        if not AccountingCutoverService.is_posting_enabled(tenant_id=tenant_id):
            return None

        payment_method, tender_lines = AccountingPostingService._invoice_payment_context(
            invoice=invoice,
            payment_method=payment_method,
            tender_lines=tender_lines,
        )

        resolved_event = event_type or event_types.SALE_COMPLETED
        resolved_module = source_module or "sales"
        if resolved_event == event_types.PHARMACY_SALE_COMPLETED:
            resolved_module = source_module or "pharmacy"
            revenue_mapping_key = revenue_mapping_key or "PHARMACY_SALES_REVENUE"

        idempotency_key = f"{resolved_event}:{resolved_module}:invoice:{invoice.id}"
        payload = {
            "total_amount": str(invoice.total_amount),
            "tax_amount": str(getattr(invoice, "tax_amount", 0) or 0),
            "cost_total": str(_compute_invoice_cost(invoice)),
            "payment_method": payment_method,
            "payments": tender_lines,
            "invoice_number": invoice.invoice_number,
            "entry_date": invoice.issue_date.isoformat()
            if hasattr(invoice.issue_date, "isoformat")
            else invoice.issue_date,
        }
        if revenue_mapping_key:
            payload["revenue_mapping_key"] = revenue_mapping_key
        return AccountingPostingService.post(
            event_type=resolved_event,
            tenant_id=tenant_id,
            source_module=resolved_module,
            source_type="invoice",
            source_id=invoice.id,
            source_reference=invoice.invoice_number,
            payload=payload,
            idempotency_key=idempotency_key,
            occurred_at=timezone.now(),
            user=user,
            branch_id=invoice.branch_id,
        )

    @staticmethod
    @transaction.atomic
    def post_refund(*, refund, invoice, user=None, restore_inventory=True) -> JournalEntry | None:
        """Post sale refund — Dr Sales Returns (+ tax payable), Cr Cash; restore inventory/COGS when applicable."""
        from apps.finance.services.cutover_service import AccountingCutoverService

        tenant_id = refund.tenant_id or getattr(invoice.branch, "tenant_id", None)
        if not tenant_id:
            return None
        if not AccountingCutoverService.is_posting_enabled(tenant_id=tenant_id):
            return None

        payment_method = "cash"
        if invoice.notes:
            import re

            match = re.search(r"Payment:\s*([a-z_]+)", invoice.notes, re.IGNORECASE)
            if match:
                payment_method = match.group(1).lower()
        if invoice.payments.exists():
            payment_method = invoice.payments.first().method or payment_method

        refund_amount = _money(refund.total_amount)
        inv_total = _money(invoice.total_amount)
        inv_tax = _money(getattr(invoice, "tax_amount", 0) or 0)
        tax_amount = Decimal("0")
        if inv_total > 0 and inv_tax > 0 and refund_amount > 0:
            tax_amount = _money(refund_amount * inv_tax / inv_total)

        idempotency_key = f"SALE_REFUNDED:sales:sale_refund:{refund.id}"
        return AccountingPostingService.post(
            event_type=event_types.SALE_REFUNDED,
            tenant_id=tenant_id,
            source_module="sales",
            source_type="sale_refund",
            source_id=refund.id,
            source_reference=refund.refund_number,
            payload={
                "refund_amount": str(refund_amount),
                "tax_amount": str(tax_amount),
                "cost_total": str(_compute_refund_cost(refund)),
                "payment_method": payment_method,
                "restore_inventory": restore_inventory,
                "refund_number": refund.refund_number,
                "invoice_number": invoice.invoice_number,
                "entry_date": timezone.localdate().isoformat(),
            },
            idempotency_key=idempotency_key,
            occurred_at=timezone.now(),
            user=user,
            branch_id=invoice.branch_id,
        )

    @staticmethod
    @transaction.atomic
    def post_purchase_received(
        *, purchase_order, receive_total, lines, user=None, warehouse=None
    ) -> JournalEntry | None:
        """Post goods receipt — Dr Inventory, Cr Accounts Payable."""
        from apps.finance.services.cutover_service import AccountingCutoverService

        tenant_id = purchase_order.tenant_id or getattr(purchase_order.branch, "tenant_id", None)
        if not tenant_id:
            return None
        if not AccountingCutoverService.is_posting_enabled(tenant_id=tenant_id):
            return None

        receive_total = _money(receive_total)
        if receive_total <= 0:
            return None

        idempotency_key = _receive_idempotency_key(
            purchase_order_id=purchase_order.id, lines=lines
        )
        return AccountingPostingService.post(
            event_type=event_types.PURCHASE_RECEIVED,
            tenant_id=tenant_id,
            source_module="purchases",
            source_type="purchase_receive",
            source_id=purchase_order.id,
            source_reference=purchase_order.order_number,
            payload={
                "receive_total": str(receive_total),
                "order_number": purchase_order.order_number,
                "entry_date": timezone.localdate().isoformat(),
            },
            idempotency_key=idempotency_key,
            occurred_at=timezone.now(),
            user=user,
            branch_id=purchase_order.branch_id,
        )

    @staticmethod
    def _invoice_payment_context(*, invoice, payment_method=None, tender_lines=None):
        if payment_method is None and invoice.notes:
            import re

            match = re.search(r"Payment:\s*([a-z_]+)", invoice.notes, re.IGNORECASE)
            if match:
                payment_method = match.group(1).lower()
        payment_method = payment_method or "cash"

        if tender_lines is None:
            tender_lines = [
                {
                    "method": p.method,
                    "amount": str(p.amount),
                    "reference": p.reference or "",
                }
                for p in invoice.payments.all()
            ]
        if not tender_lines:
            tender_lines = [
                {
                    "method": payment_method,
                    "amount": str(invoice.total_amount),
                    "reference": "",
                }
            ]
        return payment_method, tender_lines

    @staticmethod
    @transaction.atomic
    def post_gym_membership(*, invoice, user=None, payment_method=None, tender_lines=None) -> JournalEntry | None:
        """Post gym membership sale — Dr Cash/AR, Cr Membership Revenue (no COGS)."""
        from apps.finance.services.cutover_service import AccountingCutoverService
        from apps.sales.models import Invoice

        if invoice.status not in (Invoice.STATUS_PAID, Invoice.STATUS_SENT):
            return None

        tenant_id = invoice.tenant_id or getattr(invoice.branch, "tenant_id", None)
        if not tenant_id:
            return None
        if not AccountingCutoverService.is_posting_enabled(tenant_id=tenant_id):
            return None

        payment_method, tender_lines = AccountingPostingService._invoice_payment_context(
            invoice=invoice,
            payment_method=payment_method,
            tender_lines=tender_lines,
        )

        idempotency_key = f"GYM_MEMBERSHIP_SOLD:sales:invoice:{invoice.id}"
        return AccountingPostingService.post(
            event_type=event_types.GYM_MEMBERSHIP_SOLD,
            tenant_id=tenant_id,
            source_module="gym",
            source_type="invoice",
            source_id=invoice.id,
            source_reference=invoice.invoice_number,
            payload={
                "total_amount": str(invoice.total_amount),
                "tax_amount": str(getattr(invoice, "tax_amount", 0) or 0),
                "cost_total": "0",
                "payment_method": payment_method,
                "payments": tender_lines,
                "invoice_number": invoice.invoice_number,
                "entry_date": invoice.issue_date.isoformat()
                if hasattr(invoice.issue_date, "isoformat")
                else invoice.issue_date,
            },
            idempotency_key=idempotency_key,
            occurred_at=timezone.now(),
            user=user,
            branch_id=invoice.branch_id,
        )

    @staticmethod
    @transaction.atomic
    def post_gym_service(
        *,
        invoice,
        user=None,
        payment_method=None,
        tender_lines=None,
        revenue_mapping_key="GYM_PERSONAL_TRAINING_REVENUE",
        service_label="gym_service",
    ) -> JournalEntry | None:
        """Post gym PT/class service sale — Dr Cash/AR, Cr PT/class revenue (no COGS)."""
        from apps.finance.services.cutover_service import AccountingCutoverService
        from apps.sales.models import Invoice

        if invoice.status not in (Invoice.STATUS_PAID, Invoice.STATUS_SENT):
            return None

        tenant_id = invoice.tenant_id or getattr(invoice.branch, "tenant_id", None)
        if not tenant_id:
            return None
        if not AccountingCutoverService.is_posting_enabled(tenant_id=tenant_id):
            return None

        payment_method, tender_lines = AccountingPostingService._invoice_payment_context(
            invoice=invoice,
            payment_method=payment_method,
            tender_lines=tender_lines,
        )

        idempotency_key = f"GYM_SERVICE_SOLD:sales:invoice:{invoice.id}"
        return AccountingPostingService.post(
            event_type=event_types.GYM_SERVICE_SOLD,
            tenant_id=tenant_id,
            source_module="gym",
            source_type="invoice",
            source_id=invoice.id,
            source_reference=invoice.invoice_number,
            payload={
                "total_amount": str(invoice.total_amount),
                "tax_amount": str(getattr(invoice, "tax_amount", 0) or 0),
                "cost_total": "0",
                "payment_method": payment_method,
                "payments": tender_lines,
                "invoice_number": invoice.invoice_number,
                "revenue_mapping_key": revenue_mapping_key
                or "GYM_PERSONAL_TRAINING_REVENUE",
                "service_label": service_label,
                "entry_date": invoice.issue_date.isoformat()
                if hasattr(invoice.issue_date, "isoformat")
                else invoice.issue_date,
            },
            idempotency_key=idempotency_key,
            occurred_at=timezone.now(),
            user=user,
            branch_id=invoice.branch_id,
        )

    @staticmethod
    @transaction.atomic
    def post_customer_payment(*, payment, invoice, user=None) -> JournalEntry | None:
        """Post AR receipt — Dr Cash/Bank/Mobile, Cr Accounts Receivable."""
        from apps.finance.services.cutover_service import AccountingCutoverService

        tenant_id = payment.tenant_id or invoice.tenant_id
        if not tenant_id:
            return None
        if not AccountingCutoverService.is_posting_enabled(tenant_id=tenant_id):
            return None

        amount = _money(payment.amount)
        if amount <= 0:
            return None

        paid_date = payment.paid_at.date() if payment.paid_at else timezone.localdate()
        idempotency_key = f"CUSTOMER_PAYMENT_RECEIVED:sales:payment:{payment.id}"
        return AccountingPostingService.post(
            event_type=event_types.CUSTOMER_PAYMENT_RECEIVED,
            tenant_id=tenant_id,
            source_module="sales",
            source_type="payment",
            source_id=payment.id,
            source_reference=invoice.invoice_number,
            payload={
                "amount": str(amount),
                "payment_method": payment.method,
                "invoice_number": invoice.invoice_number,
                "reference": payment.reference or "",
                "entry_date": paid_date.isoformat(),
            },
            idempotency_key=idempotency_key,
            occurred_at=payment.paid_at or timezone.now(),
            user=user,
            branch_id=payment.branch_id or invoice.branch_id,
        )

    @staticmethod
    @transaction.atomic
    def post_supplier_payment(*, payment, user=None) -> JournalEntry | None:
        """Post AP payment — Dr Accounts Payable, Cr Cash/Bank/Mobile."""
        from apps.finance.services.cutover_service import AccountingCutoverService

        po = payment.purchase_order
        tenant_id = payment.tenant_id or po.tenant_id
        if not tenant_id:
            return None
        if not AccountingCutoverService.is_posting_enabled(tenant_id=tenant_id):
            return None

        amount = _money(payment.amount)
        if amount <= 0:
            return None

        paid_date = payment.paid_at.date() if payment.paid_at else timezone.localdate()
        idempotency_key = f"SUPPLIER_PAYMENT_COMPLETED:finance:supplier_payment:{payment.id}"
        return AccountingPostingService.post(
            event_type=event_types.SUPPLIER_PAYMENT_COMPLETED,
            tenant_id=tenant_id,
            source_module="finance",
            source_type="supplier_payment",
            source_id=payment.id,
            source_reference=po.order_number,
            payload={
                "amount": str(amount),
                "payment_method": payment.method,
                "order_number": po.order_number,
                "reference": payment.reference or "",
                "entry_date": paid_date.isoformat(),
            },
            idempotency_key=idempotency_key,
            occurred_at=payment.paid_at or timezone.now(),
            user=user,
            branch_id=payment.branch_id or po.branch_id,
        )

    @staticmethod
    @transaction.atomic
    def post_futsal_ledger(*, entry, user=None, payment_method="cash") -> JournalEntry | None:
        """Post futsal operational ledger row to GL — income or expense."""
        from apps.finance.services.cutover_service import AccountingCutoverService
        from apps.futsal.models import FutsalLedgerEntry

        tenant_id = getattr(entry.branch, "tenant_id", None)
        if not tenant_id:
            return None
        if not AccountingCutoverService.is_posting_enabled(tenant_id=tenant_id):
            return None

        amount = _money(entry.amount)
        if amount <= 0:
            return None

        if entry.entry_type == FutsalLedgerEntry.TYPE_INCOME:
            event_type = event_types.FUTSAL_INCOME_RECORDED
        elif entry.entry_type == FutsalLedgerEntry.TYPE_EXPENSE:
            event_type = event_types.FUTSAL_EXPENSE_RECORDED
        else:
            return None

        entry_date = entry.entry_date
        if hasattr(entry_date, "isoformat"):
            entry_date_str = entry_date.isoformat()
        else:
            entry_date_str = str(entry_date)

        idempotency_key = f"{event_type}:futsal:ledger:{entry.id}"
        return AccountingPostingService.post(
            event_type=event_type,
            tenant_id=tenant_id,
            source_module="futsal",
            source_type="futsal_ledger",
            source_id=entry.id,
            source_reference=(entry.description or entry.category or "")[:100],
            payload={
                "amount": str(amount),
                "category": entry.category or "",
                "description": entry.description or "",
                "payment_method": payment_method or "cash",
                "entry_type": entry.entry_type,
                "entry_date": entry_date_str,
            },
            idempotency_key=idempotency_key,
            occurred_at=timezone.now(),
            user=user,
            branch_id=entry.branch_id,
        )
