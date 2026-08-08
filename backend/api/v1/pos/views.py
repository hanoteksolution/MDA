import uuid

from decimal import Decimal, InvalidOperation

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.sales.services.pos_service import PosService, get_pos_profile, save_pos_profile
from apps.sales.models import DocumentSequence
from apps.sales.services.sequence_service import DocumentSequenceService
from apps.sales.services.sales_service import _resolve_branch
from apps.platform.services.sync_service import ShopSyncService
from core.responses.api_response import error_response, success_response
from permissions.base import HasPermission


class PosCheckoutView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("pos.access")]

    def post(self, request):
        if not request.user.has_permission("sales.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            ShopSyncService.assert_subscription_usable()
        except ValueError as e:
            return error_response(message=str(e), status=status.HTTP_402_PAYMENT_REQUIRED)
        try:
            result = PosService.checkout(data=request.data, user=request.user)
        except ValueError as e:
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=result,
            message="Sale completed.",
            status=status.HTTP_201_CREATED,
        )


class PosHoldListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("pos.access")]

    def get(self, request):
        if not (
            request.user.has_permission("pos.access")
            or request.user.has_permission("sales.view")
        ):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = PosService.list_holds(
            branch_id=request.query_params.get("branch_id"),
            search=request.query_params.get("search"),
            user=request.user,
        )
        return success_response(data=data)

    def post(self, request):
        if not request.user.has_permission("sales.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            ShopSyncService.assert_subscription_usable()
        except ValueError as e:
            return error_response(message=str(e), status=status.HTTP_402_PAYMENT_REQUIRED)
        try:
            invoice = PosService.hold(data=request.data, user=request.user)
        except ValueError as e:
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=invoice,
            message="Sale held.",
            status=status.HTTP_201_CREATED,
        )


class PosProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_pos_profile(user=request.user)
        return success_response(data=profile)

    def put(self, request):
        data = request.data
        merchants = data.get("merchants") or []
        cleaned = []
        for m in merchants:
            cleaned.append({
                "id": m.get("id") or str(uuid.uuid4()),
                "label": m.get("label", ""),
                "company_name": m.get("company_name", ""),
                "merchant_number": m.get("merchant_number", ""),
                "provider": m.get("provider", "mobile"),
                "is_default": bool(m.get("is_default")),
            })
        if cleaned and not any(m["is_default"] for m in cleaned):
            cleaned[0]["is_default"] = True
        payload = {
            "merchants": cleaned,
            "waiters": data.get("waiters") or [],
            "default_payment_method": data.get("default_payment_method") or "cash",
            "receipt_footer": data.get("receipt_footer") or "Thank you for your purchase!",
        }
        save_pos_profile(user=request.user, data=payload)
        return success_response(data=payload, message="POS profile updated.")


class PosWaiterSalesView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("pos.access")]

    def get(self, request):
        waiter_id = request.query_params.get("waiter_id")
        user_id = request.query_params.get("user_id")
        branch_id = request.query_params.get("branch_id")
        days = request.query_params.get("days", "30")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        waiter_name = request.query_params.get("waiter_name")
        try:
            data = PosService.list_waiter_sales(
                user=request.user,
                waiter_id=waiter_id,
                user_id=user_id,
                branch_id=branch_id,
                days=days,
                date_from=date_from,
                date_to=date_to,
                waiter_name=waiter_name,
            )
        except ValueError as e:
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=data)


class PosWaiterPerformanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (
            request.user.has_permission("pos.access")
            or request.user.has_permission("sales.view")
        ):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            data = PosService.waiter_performance(
                user=request.user,
                branch_id=request.query_params.get("branch_id"),
                date_from=request.query_params.get("date_from"),
                date_to=request.query_params.get("date_to"),
                waiter_id=request.query_params.get("waiter_id"),
                waiter_name=request.query_params.get("waiter_name"),
            )
        except ValueError as e:
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=data)


class PosReceiptNumberView(APIView):
    """Allocate or peek sequential receipt / slip numbers (accountable counters)."""

    permission_classes = [IsAuthenticated, HasPermission("pos.access")]

    KIND_MAP = {
        "order": DocumentSequence.KIND_ORDER_SLIP,
        "order_slip": DocumentSequence.KIND_ORDER_SLIP,
        "hold": DocumentSequence.KIND_HOLD_SLIP,
        "hold_slip": DocumentSequence.KIND_HOLD_SLIP,
        "invoice": DocumentSequence.KIND_INVOICE,
    }

    def _resolve_kind(self, raw: str) -> str:
        key = (raw or "order").strip().lower()
        kind = self.KIND_MAP.get(key)
        if not kind:
            raise ValueError("kind must be order, hold, or invoice.")
        return kind

    def get(self, request):
        """Return current issued count without allocating."""
        try:
            kind = self._resolve_kind(request.query_params.get("kind", "order"))
            branch = _resolve_branch(
                request.query_params.get("branch_id") or getattr(request.user, "branch_id", None)
            )
            if not branch:
                raise ValueError("No branch available for receipt numbering.")
            data = DocumentSequenceService.peek(branch=branch, kind=kind)
        except ValueError as e:
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=data)

    def post(self, request):
        """Allocate the next serial number (call once per printed slip)."""
        try:
            kind = self._resolve_kind(request.data.get("kind", "order"))
            branch_id = request.data.get("branch_id") or getattr(request.user, "branch_id", None)
            branch = _resolve_branch(branch_id)
            if not branch:
                raise ValueError("No branch available for receipt numbering.")
            data = DocumentSequenceService.allocate(branch=branch, kind=kind, width=6)
        except ValueError as e:
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=data, message="Receipt number allocated.")


class PosSessionListView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("pos.access")]

    def get(self, request):
        from apps.sales.services.cashier_session_service import CashierSessionService

        qs = CashierSessionService.list(
            user=request.user,
            request=request,
            branch_id=request.query_params.get("branch_id"),
            status=request.query_params.get("status"),
        )
        return success_response(
            data=[CashierSessionService.serialize(s) for s in qs[:100]]
        )


class PosSessionCurrentView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("pos.access")]

    def get(self, request):
        from apps.sales.services.cashier_session_service import CashierSessionService

        session = CashierSessionService.get_open(
            user=request.user,
            branch_id=request.query_params.get("branch_id"),
        )
        if session is None:
            return success_response(data=None, message="No open session.")
        return success_response(data=CashierSessionService.serialize(session))


class PosSessionOpenView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("pos.access")]

    def post(self, request):
        from apps.sales.services.cashier_session_service import (
            CashierSessionError,
            CashierSessionService,
        )

        try:
            session = CashierSessionService.open_session(
                user=request.user,
                branch_id=request.data.get("branch_id"),
                opening_float=request.data.get("opening_float") or 0,
                notes=request.data.get("notes") or "",
            )
        except CashierSessionError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=CashierSessionService.serialize(session),
            message="Cashier session opened.",
            status=status.HTTP_201_CREATED,
        )


class PosSessionCloseView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("pos.access")]

    def post(self, request):
        from apps.sales.services.cashier_session_service import (
            CashierSessionError,
            CashierSessionService,
        )

        session_id = request.data.get("session_id")
        if not session_id:
            return error_response(message="session_id is required.", status=status.HTTP_400_BAD_REQUEST)
        try:
            session = CashierSessionService.close_session(
                session_id=session_id,
                user=request.user,
                closing_cash_counted=request.data.get("closing_cash_counted"),
                notes=request.data.get("notes") or "",
            )
        except CashierSessionError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=CashierSessionService.serialize(session),
            message="Cashier session closed.",
        )


class PosRefundView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("sales.refund")]

    def post(self, request):
        from apps.sales.services.refund_service import RefundError, RefundService

        data = request.data
        invoice_id = data.get("invoice_id")
        items = data.get("items") or []
        if not invoice_id:
            return error_response(message="invoice_id is required.", status=status.HTTP_400_BAD_REQUEST)
        try:
            ShopSyncService.assert_subscription_usable()
        except ValueError as e:
            return error_response(message=str(e), status=status.HTTP_402_PAYMENT_REQUIRED)
        try:
            result = RefundService.refund_invoice(
                invoice_id=invoice_id,
                items=items,
                reason=data.get("reason") or "",
                user=request.user,
                cashier_session_id=data.get("cashier_session_id"),
            )
        except RefundError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=result, message="Refund processed.", status=status.HTTP_201_CREATED)
