"""Commerce APIs: combos, promotions, loyalty, reservations, shifts, modifier links."""

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.restaurant.services.commerce_service import CommerceError, CommerceService
from apps.restaurant.services.restaurant_service import RestaurantService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasAnyPermission, user_has_any


def _branch_id(request):
    return request.query_params.get("branch_id") or getattr(request.user, "branch_id", None)


class ItemModifierGroupLinkView(APIView):
    permission_classes = [IsAuthenticated, HasAnyPermission("restaurant.view", "restaurant.manage")]

    def get(self, request, pk):
        try:
            rows = CommerceService.list_item_modifier_groups(
                menu_item_id=pk, user=request.user, request=request
            )
        except ObjectDoesNotExist:
            return error_response(message="Item not found.", status=status.HTTP_404_NOT_FOUND)
        data = [
            {
                "id": str(r.id),
                "modifier_group_id": str(r.modifier_group_id),
                "modifier_group_name": r.modifier_group.name if r.modifier_group_id else "",
                "sort_order": r.sort_order,
            }
            for r in rows
        ]
        return success_response(data=data)

    def post(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = CommerceService.link_modifier_group(
                menu_item_id=pk,
                modifier_group_id=request.data.get("modifier_group_id"),
                sort_order=request.data.get("sort_order") or 100,
                user=request.user,
                request=request,
            )
        except (CommerceError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data={"id": str(row.id), "modifier_group_id": str(row.modifier_group_id)},
            message="Modifier group linked.",
            status=status.HTTP_201_CREATED,
        )


class ComboListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasAnyPermission("restaurant.view")]

    def get(self, request):
        qs = CommerceService.list_combos(
            branch_id=_branch_id(request), user=request.user, request=request
        )
        return paginate_queryset(
            request, qs, lambda items: [CommerceService.serialize_combo(c) for c in items]
        )

    def post(self, request):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = CommerceService.create_combo(data=data, user=request.user, request=request)
        except CommerceError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=CommerceService.serialize_combo(row),
            message="Combo created.",
            status=status.HTTP_201_CREATED,
        )


class ComboDetailView(APIView):
    permission_classes = [IsAuthenticated, HasAnyPermission("restaurant.view")]

    def get(self, request, pk):
        try:
            row = CommerceService.get_combo(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return error_response(message="Combo not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(data=CommerceService.serialize_combo(row))

    def patch(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = CommerceService.get_combo(pk=pk, user=request.user, request=request)
            row = CommerceService.update_combo(
                combo=row, data=request.data, user=request.user, request=request
            )
        except ObjectDoesNotExist:
            return error_response(message="Combo not found.", status=status.HTTP_404_NOT_FOUND)
        except CommerceError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=CommerceService.serialize_combo(row), message="Combo updated.")

    def delete(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = CommerceService.get_combo(pk=pk, user=request.user, request=request)
            CommerceService.archive_combo(combo=row, user=request.user, request=request)
        except ObjectDoesNotExist:
            return error_response(message="Combo not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(data={}, message="Combo archived.")


class PromotionListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasAnyPermission("restaurant.view")]

    def get(self, request):
        qs = CommerceService.list_promotions(
            branch_id=_branch_id(request), user=request.user, request=request
        )
        return paginate_queryset(
            request, qs, lambda items: [CommerceService.serialize_promotion(p) for p in items]
        )

    def post(self, request):
        if not user_has_any(request.user, "restaurant.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = CommerceService.create_promotion(data=data, user=request.user, request=request)
        except CommerceError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=CommerceService.serialize_promotion(row),
            message="Promotion created.",
            status=status.HTTP_201_CREATED,
        )


class PromotionDetailView(APIView):
    permission_classes = [IsAuthenticated, HasAnyPermission("restaurant.view")]

    def get(self, request, pk):
        try:
            row = CommerceService.get_promotion(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return error_response(message="Promotion not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(data=CommerceService.serialize_promotion(row))

    def patch(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = CommerceService.get_promotion(pk=pk, user=request.user, request=request)
            row = CommerceService.update_promotion(
                promotion=row, data=request.data, user=request.user, request=request
            )
        except ObjectDoesNotExist:
            return error_response(message="Promotion not found.", status=status.HTTP_404_NOT_FOUND)
        except CommerceError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=CommerceService.serialize_promotion(row), message="Promotion updated."
        )

    def delete(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = CommerceService.get_promotion(pk=pk, user=request.user, request=request)
            CommerceService.archive_promotion(
                promotion=row, user=request.user, request=request
            )
        except ObjectDoesNotExist:
            return error_response(message="Promotion not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(data={}, message="Promotion archived.")


class PromotionResolveView(APIView):
    """Preview / resolve a promo or coupon code against a cart subtotal."""

    permission_classes = [IsAuthenticated, HasAnyPermission("restaurant.view", "pos.access")]

    def post(self, request):
        try:
            promo, discount = CommerceService.resolve_active_promotion(
                code=request.data.get("code") or request.data.get("promotion_code"),
                branch_id=_branch_id(request) or request.data.get("branch_id"),
                amount=request.data.get("amount") or request.data.get("subtotal") or 0,
                user=request.user,
                request=request,
            )
        except CommerceError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data={
                "promotion": CommerceService.serialize_promotion(promo) if promo else None,
                "discount_amount": float(discount),
            }
        )


class LoyaltyProgramView(APIView):
    permission_classes = [IsAuthenticated, HasAnyPermission("restaurant.view")]

    def get(self, request):
        branch_id = _branch_id(request)
        if not branch_id:
            return error_response(message="branch_id required.", status=status.HTTP_400_BAD_REQUEST)
        row = CommerceService.get_or_create_program(
            branch_id=branch_id, user=request.user, request=request
        )
        return success_response(data=CommerceService.serialize_loyalty_program(row))

    def patch(self, request):
        if not user_has_any(request.user, "restaurant.manage", "cafeteria.settings.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        branch_id = _branch_id(request) or request.data.get("branch_id")
        if not branch_id:
            return error_response(message="branch_id required.", status=status.HTTP_400_BAD_REQUEST)
        row = CommerceService.get_or_create_program(
            branch_id=branch_id, user=request.user, request=request
        )
        row = CommerceService.update_loyalty_program(
            program=row, data=request.data, user=request.user, request=request
        )
        return success_response(
            data=CommerceService.serialize_loyalty_program(row), message="Loyalty program updated."
        )


class LoyaltyEnrollView(APIView):
    permission_classes = [IsAuthenticated, HasAnyPermission("restaurant.view", "restaurant.manage")]

    def post(self, request):
        try:
            row = CommerceService.enroll_member(
                program_id=request.data.get("program_id"),
                customer_id=request.data.get("customer_id"),
                user=request.user,
                request=request,
            )
        except CommerceError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=CommerceService.serialize_member(row),
            message="Member enrolled.",
            status=status.HTTP_201_CREATED,
        )


class ReservationListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasAnyPermission("restaurant.view", "restaurant.floor")]

    def get(self, request):
        qs = CommerceService.list_reservations(
            branch_id=_branch_id(request),
            status=request.query_params.get("status"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [CommerceService.serialize_reservation(r) for r in items]
        )

    def post(self, request):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.floor", "restaurant.orders.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = CommerceService.create_reservation(data=data, user=request.user, request=request)
        except CommerceError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=CommerceService.serialize_reservation(row),
            message="Reservation created.",
            status=status.HTTP_201_CREATED,
        )


class ReservationStatusView(APIView):
    permission_classes = [IsAuthenticated, HasAnyPermission("restaurant.floor", "restaurant.manage")]

    def post(self, request, pk):
        try:
            row = CommerceService.list_reservations(user=request.user, request=request).get(pk=pk)
            row = CommerceService.update_reservation_status(
                reservation=row,
                status=request.data.get("status"),
                user=request.user,
                request=request,
            )
        except ObjectDoesNotExist:
            return error_response(message="Not found.", status=status.HTTP_404_NOT_FOUND)
        except CommerceError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=CommerceService.serialize_reservation(row))


class ShiftListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasAnyPermission("restaurant.view", "cafeteria.staff.view")]

    def get(self, request):
        qs = CommerceService.list_shifts(
            branch_id=_branch_id(request), user=request.user, request=request
        )
        return paginate_queryset(
            request, qs, lambda items: [CommerceService.serialize_shift(s) for s in items]
        )

    def post(self, request):
        if not user_has_any(request.user, "restaurant.manage", "cafeteria.staff.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = CommerceService.create_shift(data=data, user=request.user, request=request)
        except CommerceError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=CommerceService.serialize_shift(row),
            message="Shift created.",
            status=status.HTTP_201_CREATED,
        )


class ShiftActionView(APIView):
    permission_classes = [IsAuthenticated, HasAnyPermission("restaurant.manage", "cafeteria.staff.manage", "cafeteria.barista.queue")]

    def post(self, request, pk, action):
        try:
            row = CommerceService.list_shifts(user=request.user, request=request).get(pk=pk)
            if action == "open":
                row = CommerceService.open_shift(shift=row, user=request.user, request=request)
            elif action == "close":
                row = CommerceService.close_shift(shift=row, user=request.user, request=request)
            else:
                return error_response(message="Unknown action.", status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist:
            return error_response(message="Not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(data=CommerceService.serialize_shift(row))
