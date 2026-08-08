from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.finance.services.backfill_service import AccountingBackfillService, BackfillError
from apps.finance.services.chart_service import ChartError, ChartService
from apps.finance.services.cutover_service import AccountingCutoverService, CutoverError
from apps.finance.services.health_service import AccountingHealthService
from apps.finance.services.journal_service import JournalError, JournalService
from apps.finance.services.period_service import PeriodError, PeriodService
from apps.finance.services.reconciliation_service import (
    ReconciliationError,
    ReconciliationService,
)
from apps.finance.services.summary_service import FinanceSummaryService
from apps.finance.services.voucher_service import VoucherError, VoucherService
from apps.finance.selectors.balance_sheet import BalanceSheetSelector
from apps.finance.selectors.bank_book import BankBookSelector
from apps.finance.selectors.cash_flow import CashFlowSelector
from apps.finance.selectors.ledger import GeneralLedgerSelector
from apps.finance.selectors.payables import PayablesAgingSelector
from apps.finance.selectors.profit_loss import ProfitLossSelector
from apps.finance.selectors.receivables import ReceivablesAgingSelector
from apps.finance.selectors.tax_report import TaxReportSelector
from apps.finance.selectors.trial_balance import TrialBalanceSelector
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission


class FinanceSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.view")]

    def get(self, request):
        period = request.query_params.get("period", "month")
        branch_id = request.query_params.get("branch_id") or getattr(
            getattr(request.user, "branch", None), "id", None
        )
        data = FinanceSummaryService.get_summary(
            branch_id=branch_id,
            period=period,
            user=request.user,
            request=request,
        )
        return success_response(data=data)


class AccountListView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.view")]

    def get(self, request):
        qs = ChartService.list(
            account_type=request.query_params.get("type"),
            is_active=True,
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request,
            qs,
            lambda items: [
                ChartService.serialize(a, balance=ChartService.account_balance(account=a))
                for a in items
            ],
        )


class CostCenterListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.view")]

    def get(self, request):
        from apps.finance.services.cost_center_service import CostCenterService

        tenant_id = getattr(request.user, "tenant_id", None)
        if tenant_id:
            CostCenterService.seed_defaults(tenant_id=tenant_id, user=request.user)
        active = request.query_params.get("is_active")
        is_active = None
        if active is not None:
            is_active = str(active).lower() not in ("0", "false", "no")
        qs = CostCenterService.list(
            is_active=is_active, user=request.user, request=request
        )
        return paginate_queryset(
            request, qs, lambda items: [CostCenterService.serialize(c) for c in items]
        )

    def post(self, request):
        from apps.finance.services.cost_center_service import CostCenterError, CostCenterService

        if not request.user.has_permission("finance.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            cc = CostCenterService.create(
                data=request.data, user=request.user, request=request
            )
        except CostCenterError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=CostCenterService.serialize(cc),
            message="Cost center created.",
            status=status.HTTP_201_CREATED,
        )


class BusinessUnitListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.view")]

    def get(self, request):
        from apps.finance.services.business_unit_service import BusinessUnitService

        tenant_id = getattr(request.user, "tenant_id", None)
        if tenant_id:
            BusinessUnitService.seed_defaults(tenant_id=tenant_id, user=request.user)
        active = request.query_params.get("is_active")
        is_active = None
        if active is not None:
            is_active = str(active).lower() not in ("0", "false", "no")
        qs = BusinessUnitService.list(
            is_active=is_active, user=request.user, request=request
        )
        return paginate_queryset(
            request, qs, lambda items: [BusinessUnitService.serialize(b) for b in items]
        )

    def post(self, request):
        from apps.finance.services.business_unit_service import (
            BusinessUnitError,
            BusinessUnitService,
        )

        if not request.user.has_permission("finance.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            bu = BusinessUnitService.create(
                data=request.data, user=request.user, request=request
            )
        except BusinessUnitError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=BusinessUnitService.serialize(bu),
            message="Business unit created.",
            status=status.HTTP_201_CREATED,
        )


class JournalListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.view")]

    def get(self, request):
        qs = JournalService.list(
            search=request.query_params.get("search"),
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
            user=request.user,
            request=request,
        )
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return paginate_queryset(
            request, qs, lambda items: [JournalService.serialize(e) for e in items]
        )

    def post(self, request):
        if not request.user.has_permission("finance.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        source_type = data.get("source_type") or "manual"
        # Manual journals default to draft (maker-checker). System sources still post.
        if source_type == "manual" and not data.get("status"):
            data["status"] = "draft"
        want_post = str(data.get("status") or "").lower() == "posted"
        if want_post and source_type == "manual":
            if not request.user.has_permission("finance.approve"):
                return error_response(
                    message="finance.approve required to post manual journals immediately.",
                    status=status.HTTP_403_FORBIDDEN,
                )
            # Immediate post on create is always self-approve; require explicit flag.
            if not data.get("allow_self_approve"):
                data["status"] = "draft"
        try:
            entry = JournalService.create_entry(
                data=data, user=request.user, request=request
            )
        except (JournalError, ChartError) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        msg = (
            "Journal entry posted."
            if entry.status == "posted"
            else "Journal draft saved. Awaiting approval."
        )
        return success_response(
            data=JournalService.serialize(entry),
            message=msg,
            status=status.HTTP_201_CREATED,
        )


class JournalPostView(APIView):
    """Approve / post a draft journal (maker-checker)."""

    permission_classes = [IsAuthenticated, HasPermission("finance.approve")]

    def post(self, request, entry_id):
        try:
            entry = JournalService.get(
                entry_id=entry_id, user=request.user, request=request
            )
            allow_self = bool(request.data.get("allow_self_approve"))
            entry = JournalService.post_draft(
                entry=entry, user=request.user, allow_self_approve=allow_self
            )
        except JournalError as exc:
            code = getattr(exc, "code", "")
            http = (
                status.HTTP_404_NOT_FOUND
                if code == "JOURNAL_NOT_FOUND"
                else status.HTTP_400_BAD_REQUEST
            )
            return error_response(message=str(exc), status=http)
        return success_response(
            data=JournalService.serialize(entry),
            message="Journal entry approved and posted.",
        )


class JournalDiscardView(APIView):
    """Discard (soft-delete) a draft journal."""

    permission_classes = [IsAuthenticated, HasPermission("finance.create")]

    def post(self, request, entry_id):
        try:
            entry = JournalService.get(
                entry_id=entry_id, user=request.user, request=request
            )
            JournalService.discard_draft(entry=entry, user=request.user)
        except JournalError as exc:
            code = getattr(exc, "code", "")
            http = (
                status.HTTP_404_NOT_FOUND
                if code == "JOURNAL_NOT_FOUND"
                else status.HTTP_400_BAD_REQUEST
            )
            return error_response(message=str(exc), status=http)
        return success_response(message="Draft journal discarded.")


class TrialBalanceReportView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.view")]

    def get(self, request):
        data = TrialBalanceSelector.run(
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
            user=request.user,
            request=request,
        )
        return success_response(data=data)


class ProfitLossReportView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.view")]

    def get(self, request):
        data = ProfitLossSelector.run(
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
            business_unit_id=request.query_params.get("business_unit_id"),
            cost_center_id=request.query_params.get("cost_center_id"),
            user=request.user,
            request=request,
        )
        return success_response(data=data)


class BalanceSheetReportView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.view")]

    def get(self, request):
        data = BalanceSheetSelector.run(
            as_of=request.query_params.get("as_of"),
            user=request.user,
            request=request,
        )
        return success_response(data=data)


class AccountingHealthView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.view")]

    def get(self, request):
        data = AccountingHealthService.check(user=request.user, request=request)
        return success_response(data=data)


class AccountingEquationView(APIView):
    """Assets = Liabilities + Equity (with retained earnings) from posted ledger."""

    permission_classes = [IsAuthenticated, HasPermission("finance.view")]

    def get(self, request):
        from apps.finance.services.equation_service import AccountingEquationService

        as_of = request.query_params.get("as_of") or None
        result = AccountingEquationService.evaluate(
            as_of=as_of, user=request.user, request=request
        )
        return success_response(data=AccountingEquationService.serialize(result))


class GeneralLedgerReportView(APIView):
    """Account statement / general ledger drill-down."""

    permission_classes = [IsAuthenticated, HasPermission("finance.view")]

    def get(self, request):
        from django.utils.dateparse import parse_date

        date_from = request.query_params.get("date_from") or None
        date_to = request.query_params.get("date_to") or None
        if isinstance(date_from, str):
            date_from = parse_date(date_from)
        if isinstance(date_to, str):
            date_to = parse_date(date_to)
        try:
            limit = int(request.query_params.get("limit") or 500)
        except (TypeError, ValueError):
            limit = 500
        data = GeneralLedgerSelector.run(
            account_id=request.query_params.get("account_id"),
            account_code=request.query_params.get("account_code"),
            date_from=date_from,
            date_to=date_to,
            cost_center_id=request.query_params.get("cost_center_id"),
            business_unit_id=request.query_params.get("business_unit_id"),
            user=request.user,
            request=request,
            limit=limit,
        )
        if data.get("error"):
            return error_response(message=data["error"], status=status.HTTP_404_NOT_FOUND)
        if data.get("account") is None and not request.query_params.get("account_id") and not request.query_params.get(
            "account_code"
        ):
            return error_response(
                message="account_id or account_code is required.",
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=data)


class AccountingBackfillView(APIView):
    """Preview (GET) or run (POST dry_run/commit) historical journal backfill."""

    permission_classes = [IsAuthenticated, HasPermission("finance.create")]

    def get(self, request):
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return error_response(message="Tenant required.", status=status.HTTP_400_BAD_REQUEST)
        try:
            data = AccountingBackfillService.preview(
                tenant_id=tenant_id,
                before_date=request.query_params.get("before"),
                limit=int(request.query_params.get("limit") or 500),
            )
        except BackfillError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=data)

    def post(self, request):
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return error_response(message="Tenant required.", status=status.HTTP_400_BAD_REQUEST)
        dry_run = request.data.get("dry_run", True)
        if isinstance(dry_run, str):
            dry_run = dry_run.lower() not in ("0", "false", "no")
        try:
            data = AccountingBackfillService.run(
                tenant_id=tenant_id,
                before_date=request.data.get("before") or request.query_params.get("before"),
                dry_run=bool(dry_run),
                limit=int(request.data.get("limit") or 500),
                include_invoices=request.data.get("include_invoices", True) is not False,
                include_expenses=request.data.get("include_expenses", True) is not False,
                include_purchases=request.data.get("include_purchases", True) is not False,
                user=request.user,
            )
        except BackfillError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=data,
            message="Backfill dry-run complete." if data.get("dry_run") else "Backfill committed.",
        )


class AccountingCutoverView(APIView):
    """Cutover status (GET) or prepare/activate/disable (POST)."""

    permission_classes = [IsAuthenticated, HasPermission("finance.create")]

    def get(self, request):
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return error_response(message="Tenant required.", status=status.HTTP_400_BAD_REQUEST)
        try:
            data = AccountingCutoverService.status(tenant_id=tenant_id)
        except CutoverError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=data)

    def post(self, request):
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return error_response(message="Tenant required.", status=status.HTTP_400_BAD_REQUEST)
        action = (request.data.get("action") or "prepare").strip().lower()
        try:
            if action == "prepare":
                data = AccountingCutoverService.prepare(
                    tenant_id=tenant_id, user=request.user
                )
                message = "Cutover prepared."
            elif action == "activate":
                data = AccountingCutoverService.activate(
                    tenant_id=tenant_id,
                    cutover_date=request.data.get("date"),
                    user=request.user,
                )
                message = "Cutover activated."
            elif action in ("disable", "disable_posting"):
                data = AccountingCutoverService.disable_posting(
                    tenant_id=tenant_id, user=request.user
                )
                message = "Accounting posting disabled."
            else:
                return error_response(
                    message="Unknown action. Use prepare, activate, or disable_posting.",
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except CutoverError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=data, message=message)


class CashFlowReportView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.view")]

    def get(self, request):
        data = CashFlowSelector.run(
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
            user=request.user,
            request=request,
        )
        return success_response(data=data)


class PeriodListView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.view")]

    def get(self, request):
        # Ensure current month exists for the tenant
        try:
            PeriodService.ensure_current(user=request.user, request=request)
        except PeriodError:
            pass
        qs = PeriodService.list(
            user=request.user,
            request=request,
            status=request.query_params.get("status"),
        )
        return success_response(data=[PeriodService.serialize(p) for p in qs[:100]])


class PeriodActionView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.create")]

    def post(self, request, period_id, action):
        try:
            if action == "soft-close":
                period = PeriodService.soft_close(
                    period_id=period_id, user=request.user, request=request
                )
            elif action == "close":
                period = PeriodService.close(
                    period_id=period_id, user=request.user, request=request
                )
            elif action == "reopen":
                period = PeriodService.reopen(
                    period_id=period_id, user=request.user, request=request
                )
            elif action == "lock":
                period = PeriodService.lock(
                    period_id=period_id, user=request.user, request=request
                )
            else:
                return error_response(
                    message="Unknown action. Use soft-close, close, reopen, or lock.",
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except PeriodError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=PeriodService.serialize(period),
            message=f"Period {action.replace('-', ' ')}d.",
        )


class ReceivablesAgingView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.view")]

    def get(self, request):
        data = ReceivablesAgingSelector.run(
            as_of=request.query_params.get("as_of"),
            user=request.user,
            request=request,
        )
        return success_response(data=data)


class PayablesAgingView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.view")]

    def get(self, request):
        data = PayablesAgingSelector.run(
            as_of=request.query_params.get("as_of"),
            user=request.user,
            request=request,
        )
        return success_response(data=data)


class TaxReportView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.view")]

    def get(self, request):
        data = TaxReportSelector.run(
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
            user=request.user,
            request=request,
        )
        return success_response(data=data)


class CustomerReceiptView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.create")]

    def post(self, request):
        try:
            payment = VoucherService.record_customer_receipt(
                invoice_id=request.data.get("invoice_id"),
                amount=request.data.get("amount"),
                method=request.data.get("method") or "cash",
                reference=request.data.get("reference") or "",
                paid_at=request.data.get("paid_at"),
                user=request.user,
                request=request,
            )
        except VoucherError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=VoucherService.serialize_receipt(payment),
            message="Customer receipt posted.",
            status=status.HTTP_201_CREATED,
        )


class SupplierPaymentView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.create")]

    def post(self, request):
        try:
            payment = VoucherService.record_supplier_payment(
                purchase_order_id=request.data.get("purchase_order_id"),
                amount=request.data.get("amount"),
                method=request.data.get("method") or "cash",
                reference=request.data.get("reference") or "",
                notes=request.data.get("notes") or "",
                paid_at=request.data.get("paid_at"),
                branch_id=request.data.get("branch_id"),
                user=request.user,
                request=request,
            )
        except VoucherError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=VoucherService.serialize_supplier_payment(payment),
            message="Supplier payment posted.",
            status=status.HTTP_201_CREATED,
        )


class BankBookView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.view")]

    def get(self, request):
        account_id = request.query_params.get("account_id")
        if not account_id:
            accounts = BankBookSelector.cash_accounts(user=request.user, request=request)
            return success_response(data={"cash_accounts": accounts, "lines": []})
        try:
            data = BankBookSelector.run(
                account_id=account_id,
                as_of=request.query_params.get("as_of"),
                unmatched_only=request.query_params.get("unmatched_only") == "1",
                user=request.user,
                request=request,
            )
        except ReconciliationError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=data)


class ReconciliationListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.view")]

    def get(self, request):
        qs = ReconciliationService.list(
            user=request.user,
            request=request,
            account_id=request.query_params.get("account_id"),
            status=request.query_params.get("status"),
        )
        return success_response(
            data=[ReconciliationService.serialize(r, include_lines=False) for r in qs[:50]]
        )

    def post(self, request):
        if not request.user.has_permission("finance.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            rec = ReconciliationService.create(
                account_id=request.data.get("account_id"),
                statement_date=request.data.get("statement_date"),
                statement_balance=request.data.get("statement_balance"),
                notes=request.data.get("notes") or "",
                user=request.user,
                request=request,
            )
        except ReconciliationError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=ReconciliationService.serialize(rec),
            message="Reconciliation started.",
            status=status.HTTP_201_CREATED,
        )


class ReconciliationDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.view")]

    def get(self, request, reconciliation_id):
        try:
            rec = ReconciliationService.get(
                reconciliation_id=reconciliation_id, user=request.user, request=request
            )
        except ReconciliationError as exc:
            return error_response(message=str(exc), status=status.HTTP_404_NOT_FOUND)
        return success_response(data=ReconciliationService.serialize(rec))


class ReconciliationLineView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.create")]

    def post(self, request, reconciliation_id):
        try:
            line = ReconciliationService.add_statement_line(
                reconciliation_id=reconciliation_id,
                line_date=request.data.get("line_date"),
                amount=request.data.get("amount"),
                description=request.data.get("description") or "",
                reference=request.data.get("reference") or "",
                user=request.user,
                request=request,
            )
        except ReconciliationError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=ReconciliationService.serialize_line(line),
            message="Statement line added.",
            status=status.HTTP_201_CREATED,
        )


class ReconciliationMatchView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.create")]

    def post(self, request, reconciliation_id):
        try:
            line = ReconciliationService.match(
                reconciliation_id=reconciliation_id,
                statement_line_id=request.data.get("statement_line_id"),
                journal_line_id=request.data.get("journal_line_id"),
                user=request.user,
                request=request,
            )
        except ReconciliationError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=ReconciliationService.serialize_line(line),
            message="Line matched.",
        )


class ReconciliationUnmatchView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.create")]

    def post(self, request, reconciliation_id):
        try:
            line = ReconciliationService.unmatch(
                reconciliation_id=reconciliation_id,
                statement_line_id=request.data.get("statement_line_id"),
                user=request.user,
                request=request,
            )
        except ReconciliationError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=ReconciliationService.serialize_line(line),
            message="Line unmatched.",
        )


class ReconciliationAutoMatchView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.create")]

    def post(self, request, reconciliation_id):
        try:
            result = ReconciliationService.auto_match(
                reconciliation_id=reconciliation_id,
                user=request.user,
                request=request,
            )
            rec = ReconciliationService.get(
                reconciliation_id=reconciliation_id, user=request.user, request=request
            )
        except ReconciliationError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data={"result": result, "reconciliation": ReconciliationService.serialize(rec)},
            message=f"Auto-matched {result['matched']} line(s).",
        )


class ReconciliationCompleteView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("finance.create")]

    def post(self, request, reconciliation_id):
        try:
            rec = ReconciliationService.complete(
                reconciliation_id=reconciliation_id,
                user=request.user,
                request=request,
            )
        except ReconciliationError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=ReconciliationService.serialize(rec),
            message="Reconciliation completed.",
        )
