"""Posting rule engine — resolve event_type + conditions → journal lines via AccountMapping.

Complex sales/refunds stay in AccountingPostingService hardcoded builders (fallback).
Simple events (expense, purchase receive, AR/AP payments, futsal) are rule-driven.
"""

from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from apps.finance.events import event_types
from apps.finance.models import PostingRule, PostingRuleLine
from apps.finance.services.mapping_service import MappingError, MappingService

MONEY = Decimal("0.01")
_MEMO_TOKEN = re.compile(r"\{(\w+)(?::([^}]*))?\}")


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(MONEY, rounding=ROUND_HALF_UP)


def _render_memo(template: str, payload: dict, *, fallback: str = "") -> str:
    """Expand `{field}` / `{field:default}` tokens from payload into a memo."""
    if not template:
        return (fallback or "")[:255]

    def repl(match):
        field, default = match.group(1), match.group(2)
        value = payload.get(field)
        if value is None or str(value).strip() == "":
            return default if default is not None else ""
        return str(value)

    rendered = _MEMO_TOKEN.sub(repl, template).strip()
    return (rendered or fallback or template)[:255]


def _payment_mapping_key(method: str) -> str:
    method = (method or "cash").strip().lower()
    if method == "on_account":
        return "DEFAULT_RECEIVABLE"
    if method in ("card", "bank"):
        return "DEFAULT_BANK"
    if method == "mobile":
        return "DEFAULT_MOBILE_MONEY"
    return "DEFAULT_CASH"


class PostingRuleError(ValueError):
    pass


# Seed catalog: (event_type, name, priority, conditions, lines, description_key)
# mapping_key may be a literal mapping or `@expense_mapping` / `@payment_mapping`
DEFAULT_RULE_SPECS = [
    {
        "event_type": event_types.EXPENSE_APPROVED,
        "name": "Expense (cash)",
        "priority": 100,
        "conditions": {},
        "description_field": "description",
        "description_prefix": "Expense",
        "lines": [
            {
                "side": PostingRuleLine.SIDE_DEBIT,
                "mapping_key": "@expense_mapping",
                "amount_field": "amount",
                "memo": "Expense",
            },
            {
                "side": PostingRuleLine.SIDE_CREDIT,
                "mapping_key": "DEFAULT_CASH",
                "amount_field": "amount",
                "memo": "Cash out",
            },
        ],
    },
    {
        "event_type": event_types.PURCHASE_RECEIVED,
        "name": "Purchase received to inventory",
        "priority": 100,
        "conditions": {},
        "description_field": "order_number",
        "description_prefix": "Purchase receive",
        "lines": [
            {
                "side": PostingRuleLine.SIDE_DEBIT,
                "mapping_key": "DEFAULT_INVENTORY",
                "amount_field": "receive_total",
                "memo": "Inventory",
            },
            {
                "side": PostingRuleLine.SIDE_CREDIT,
                "mapping_key": "DEFAULT_PAYABLE",
                "amount_field": "receive_total",
                "memo": "Accounts payable",
            },
        ],
    },
    {
        "event_type": event_types.CUSTOMER_PAYMENT_RECEIVED,
        "name": "Customer receipt",
        "priority": 100,
        "conditions": {},
        "description_field": "invoice_number",
        "description_prefix": "Customer receipt",
        "lines": [
            {
                "side": PostingRuleLine.SIDE_DEBIT,
                "mapping_key": "@payment_mapping",
                "amount_field": "amount",
                "memo": "{payment_method}",
            },
            {
                "side": PostingRuleLine.SIDE_CREDIT,
                "mapping_key": "DEFAULT_RECEIVABLE",
                "amount_field": "amount",
                "memo": "AR settlement",
            },
        ],
    },
    {
        "event_type": event_types.SUPPLIER_PAYMENT_COMPLETED,
        "name": "Supplier payment",
        "priority": 100,
        "conditions": {},
        "description_field": "order_number",
        "description_prefix": "Supplier payment",
        "lines": [
            {
                "side": PostingRuleLine.SIDE_DEBIT,
                "mapping_key": "DEFAULT_PAYABLE",
                "amount_field": "amount",
                "memo": "AP settlement",
            },
            {
                "side": PostingRuleLine.SIDE_CREDIT,
                "mapping_key": "@payment_mapping",
                "amount_field": "amount",
                "memo": "{payment_method}",
            },
        ],
    },
    {
        "event_type": event_types.FUTSAL_INCOME_RECORDED,
        "name": "Futsal income",
        "priority": 100,
        "conditions": {},
        "description_field": "description",
        "description_prefix": "Futsal income",
        "lines": [
            {
                "side": PostingRuleLine.SIDE_DEBIT,
                "mapping_key": "@payment_mapping",
                "amount_field": "amount",
                "memo": "{payment_method}",
            },
            {
                "side": PostingRuleLine.SIDE_CREDIT,
                "mapping_key": "FUTSAL_REVENUE",
                "amount_field": "amount",
                "memo": "{category:Futsal income}",
            },
        ],
    },
    {
        "event_type": event_types.FUTSAL_EXPENSE_RECORDED,
        "name": "Futsal expense",
        "priority": 100,
        "conditions": {},
        "description_field": "description",
        "description_prefix": "Futsal expense",
        "lines": [
            {
                "side": PostingRuleLine.SIDE_DEBIT,
                "mapping_key": "FUTSAL_EXPENSE",
                "amount_field": "amount",
                "memo": "{category:Futsal expense}",
            },
            {
                "side": PostingRuleLine.SIDE_CREDIT,
                "mapping_key": "@payment_mapping",
                "amount_field": "amount",
                "memo": "{payment_method}",
            },
        ],
    },
]


class PostingRuleService:
    """Select and apply tenant PostingRule rows."""

    RULE_DRIVEN_EVENTS = frozenset(
        {
            event_types.EXPENSE_APPROVED,
            event_types.PURCHASE_RECEIVED,
            event_types.CUSTOMER_PAYMENT_RECEIVED,
            event_types.SUPPLIER_PAYMENT_COMPLETED,
            event_types.FUTSAL_INCOME_RECORDED,
            event_types.FUTSAL_EXPENSE_RECORDED,
        }
    )

    @staticmethod
    @transaction.atomic
    def seed_defaults(*, tenant_id, user=None) -> list[PostingRule]:
        if not tenant_id:
            return []
        created = []
        for spec in DEFAULT_RULE_SPECS:
            existing = PostingRule.active_objects().filter(
                tenant_id=tenant_id,
                event_type=spec["event_type"],
                name=spec["name"],
            ).first()
            if existing:
                continue
            rule = PostingRule.objects.create(
                tenant_id=tenant_id,
                event_type=spec["event_type"],
                business_type_code="",
                name=spec["name"],
                conditions=spec.get("conditions") or {},
                priority=spec.get("priority", 100),
                is_active=True,
                created_by=user,
            )
            for line in spec["lines"]:
                PostingRuleLine.objects.create(
                    rule=rule,
                    side=line["side"],
                    mapping_key=line["mapping_key"],
                    amount_field=line.get("amount_field") or "amount",
                    memo=line.get("memo") or "",
                    created_by=user,
                )
            # stash description metadata on conditions for apply
            meta = dict(rule.conditions or {})
            meta["_description_field"] = spec.get("description_field") or ""
            meta["_description_prefix"] = spec.get("description_prefix") or rule.name
            rule.conditions = meta
            rule.save(update_fields=["conditions", "updated_at"])
            created.append(rule)
        return created

    @staticmethod
    def find_rule(*, event_type: str, tenant_id, payload: dict | None = None) -> PostingRule | None:
        payload = payload or {}
        qs = (
            PostingRule.active_objects()
            .filter(tenant_id=tenant_id, event_type=event_type, is_active=True)
            .prefetch_related("lines")
            .order_by("priority", "name")
        )
        for rule in qs:
            if PostingRuleService._conditions_match(rule.conditions or {}, payload):
                return rule
        return None

    @staticmethod
    def _conditions_match(conditions: dict, payload: dict) -> bool:
        for key, expected in conditions.items():
            if key.startswith("_"):
                continue
            actual = payload.get(key)
            if actual is None:
                actual = ""
            if str(actual).strip().lower() != str(expected).strip().lower():
                return False
        return True

    @staticmethod
    def _resolve_mapping_key(*, mapping_key: str, payload: dict) -> str:
        if mapping_key == "@expense_mapping":
            return MappingService.expense_mapping_key(payload.get("category") or "other")
        if mapping_key == "@payment_mapping":
            return _payment_mapping_key(payload.get("payment_method") or "cash")
        if mapping_key.startswith("@") and len(mapping_key) > 1:
            field = mapping_key[1:]
            value = payload.get(field)
            if not value:
                raise PostingRuleError(f"Payload missing mapping field '{field}'.")
            return str(value)
        return mapping_key

    @staticmethod
    def apply_rule(*, rule: PostingRule, tenant_id, payload: dict, user=None) -> tuple[list, str, object]:
        lines_out = []
        for line in rule.lines.all():
            amount = _money(payload.get(line.amount_field))
            if amount <= 0:
                raise PostingRuleError(
                    f"Amount field '{line.amount_field}' must be positive for rule '{rule.name}'."
                )
            key = PostingRuleService._resolve_mapping_key(
                mapping_key=line.mapping_key, payload=payload
            )
            try:
                account = MappingService.resolve(key=key, tenant_id=tenant_id, user=user)
            except MappingError as exc:
                raise PostingRuleError(str(exc)) from exc
            row = {
                "account_id": str(account.id),
                "debit": amount if line.side == PostingRuleLine.SIDE_DEBIT else Decimal("0"),
                "credit": amount if line.side == PostingRuleLine.SIDE_CREDIT else Decimal("0"),
                "memo": _render_memo(line.memo or "", payload, fallback=key),
            }
            lines_out.append(row)

        if len(lines_out) < 2:
            raise PostingRuleError(f"Posting rule '{rule.name}' produced fewer than 2 lines.")

        prefix = (rule.conditions or {}).get("_description_prefix") or rule.name
        field = (rule.conditions or {}).get("_description_field") or ""
        detail = (payload.get(field) if field else None) or payload.get("description") or ""
        description = f"{prefix}: {detail}".strip(": ").strip()[:255] or rule.name
        entry_date = payload.get("entry_date") or timezone.localdate()
        return lines_out, description, entry_date

    @staticmethod
    def try_build_lines(
        *, event_type: str, tenant_id, payload: dict, user=None
    ) -> tuple[list, str, object] | None:
        """Return journal lines if a matching active rule exists; else None (caller fallback)."""
        if event_type not in PostingRuleService.RULE_DRIVEN_EVENTS:
            return None
        PostingRuleService.seed_defaults(tenant_id=tenant_id, user=user)
        rule = PostingRuleService.find_rule(
            event_type=event_type, tenant_id=tenant_id, payload=payload
        )
        if rule is None:
            return None
        return PostingRuleService.apply_rule(
            rule=rule, tenant_id=tenant_id, payload=payload, user=user
        )
