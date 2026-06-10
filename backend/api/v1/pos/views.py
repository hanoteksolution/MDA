import uuid

from decimal import Decimal, InvalidOperation

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.sales.services.pos_service import PosService, get_pos_profile, save_pos_profile
from core.responses.api_response import error_response, success_response
from permissions.base import HasPermission


class PosCheckoutView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("pos.access")]

    def post(self, request):
        if not request.user.has_permission("sales.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
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
            "default_payment_method": data.get("default_payment_method") or "cash",
            "receipt_footer": data.get("receipt_footer") or "Thank you for your purchase!",
        }
        save_pos_profile(user=request.user, data=payload)
        return success_response(data=payload, message="POS profile updated.")
