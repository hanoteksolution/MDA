from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.restaurant.serializers import (
    serialize_category,
    serialize_item,
    serialize_order,
    serialize_table,
)
from apps.restaurant.services import RestaurantError, RestaurantService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission


def _branch_id(request):
    return request.query_params.get("branch_id") or getattr(request.user, "branch_id", None)


def _not_found(entity="Record"):
    return error_response(message=f"{entity} not found.", status=status.HTTP_404_NOT_FOUND)


class RestaurantSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request):
        data = RestaurantService.summary(
            branch_id=_branch_id(request), user=request.user, request=request
        )
        return success_response(data=data)


class CategoryListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request):
        qs = RestaurantService.list_categories(
            branch_id=_branch_id(request), user=request.user, request=request
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_category(c) for c in items]
        )

    def post(self, request):
        if not request.user.has_permission("restaurant.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = RestaurantService.create_category(
                data=data, user=request.user, request=request
            )
        except (RestaurantError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_category(row),
            message="Category created.",
            status=status.HTTP_201_CREATED,
        )


class ItemListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request):
        qs = RestaurantService.list_items(
            branch_id=_branch_id(request),
            category_id=request.query_params.get("category_id"),
            available_only=request.query_params.get("available") == "1",
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_item(i) for i in items]
        )

    def post(self, request):
        if not request.user.has_permission("restaurant.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = RestaurantService.create_item(
                data=data, user=request.user, request=request
            )
        except (RestaurantError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_item(row),
            message="Menu item created.",
            status=status.HTTP_201_CREATED,
        )


class TableListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request):
        qs = RestaurantService.list_tables(
            branch_id=_branch_id(request),
            status=request.query_params.get("status"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_table(t) for t in items]
        )

    def post(self, request):
        if not request.user.has_permission("restaurant.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = RestaurantService.create_table(
                data=data, user=request.user, request=request
            )
        except (RestaurantError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_table(row),
            message="Table created.",
            status=status.HTTP_201_CREATED,
        )


class TableStatusView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def post(self, request, pk):
        if not (
            request.user.has_permission("restaurant.manage")
            or request.user.has_permission("restaurant.floor")
        ):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            table = RestaurantService.get_table(pk=pk, user=request.user, request=request)
            table = RestaurantService.set_table_status(
                table=table, status=request.data.get("status"), user=request.user
            )
        except (RestaurantError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_table(table), message="Table updated.")


class OrderListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request):
        qs = RestaurantService.list_orders(
            branch_id=_branch_id(request),
            status=request.query_params.get("status"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [serialize_order(o) for o in items]
        )

    def post(self, request):
        if not (
            request.user.has_permission("restaurant.manage")
            or request.user.has_permission("restaurant.floor")
        ):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            order = RestaurantService.create_order(
                data=data, user=request.user, request=request
            )
        except (RestaurantError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_order(order),
            message="Order created.",
            status=status.HTTP_201_CREATED,
        )


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request, pk):
        try:
            order = RestaurantService.get_order(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Order")
        return success_response(data=serialize_order(order))


class OrderPosPayloadView(APIView):
    """Hydrate POS cart from an open restaurant order (ensures Product links)."""

    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request, pk):
        try:
            order = RestaurantService.get_order(pk=pk, user=request.user, request=request)
            data = RestaurantService.serialize_order_for_pos(
                order=order, user=request.user
            )
        except ObjectDoesNotExist:
            return _not_found("Order")
        except RestaurantError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=data)


class OrderStatusView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def post(self, request, pk):
        if not (
            request.user.has_permission("restaurant.manage")
            or request.user.has_permission("restaurant.floor")
            or request.user.has_permission("restaurant.kitchen")
        ):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            order = RestaurantService.get_order(pk=pk, user=request.user, request=request)
            order = RestaurantService.update_order_status(
                order=order, status=request.data.get("status"), user=request.user
            )
        except (RestaurantError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_order(order), message="Order updated.")


class OrderAddLineView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def post(self, request, pk):
        if not (
            request.user.has_permission("restaurant.manage")
            or request.user.has_permission("restaurant.floor")
        ):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            order = RestaurantService.get_order(pk=pk, user=request.user, request=request)
            RestaurantService.add_line(
                order=order, data=request.data, user=request.user, request=request
            )
            order.refresh_from_db()
        except (RestaurantError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_order(order), message="Line added.")
