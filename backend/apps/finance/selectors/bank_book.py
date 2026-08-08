"""Cash / bank book — journal lines for reconcilable asset accounts."""

from __future__ import annotations

from apps.finance.models import Account
from apps.finance.services.chart_service import ChartService
from apps.finance.services.mapping_service import MappingService
from apps.finance.services.reconciliation_service import ReconciliationService
from core.tenancy import stamp_tenant_id


class BankBookSelector:
    @staticmethod
    def cash_accounts(*, user=None, request=None) -> list[dict]:
        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            return []
        ChartService.ensure_default_chart(tenant_id=tenant_id, user=user, request=request)
        MappingService.seed_defaults(tenant_id=tenant_id, user=user)

        accounts = []
        seen = set()
        for key in ("DEFAULT_CASH", "DEFAULT_BANK", "DEFAULT_MOBILE_MONEY"):
            try:
                acct = MappingService.resolve(key=key, tenant_id=tenant_id, user=user)
            except Exception:
                continue
            if acct.id in seen:
                continue
            seen.add(acct.id)
            bal = ChartService.account_balance(account=acct)
            accounts.append(
                {
                    "id": str(acct.id),
                    "code": acct.code,
                    "name": acct.name,
                    "balance": float(bal),
                    "mapping_key": key,
                }
            )
        # Also include any other asset accounts coded 10xx
        for acct in Account.active_objects().filter(
            tenant_id=tenant_id, account_type=Account.TYPE_ASSET, code__startswith="10"
        ):
            if acct.id in seen:
                continue
            seen.add(acct.id)
            accounts.append(
                {
                    "id": str(acct.id),
                    "code": acct.code,
                    "name": acct.name,
                    "balance": float(ChartService.account_balance(account=acct)),
                    "mapping_key": "",
                }
            )
        accounts.sort(key=lambda a: a["code"])
        return accounts

    @staticmethod
    def run(*, account_id, as_of=None, unmatched_only=False, user=None, request=None) -> dict:
        accounts = BankBookSelector.cash_accounts(user=user, request=request)
        lines = ReconciliationService.list_book_lines(
            account_id=account_id,
            as_of=as_of,
            unmatched_only=unmatched_only,
            user=user,
            request=request,
        )
        account = next((a for a in accounts if a["id"] == str(account_id)), None)
        return {
            "account": account,
            "as_of": as_of,
            "lines": lines,
            "cash_accounts": accounts,
        }
