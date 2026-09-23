"""Cafeteria profile, barista queue, waste, variants API."""

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.restaurant.models import MenuItemVariant, Recipe
from apps.restaurant.serializers import serialize_order, serialize_recipe
from apps.restaurant.serializers.restaurant_serializers import serialize_variant
from apps.restaurant.services import (
    BaristaError,
    BaristaService,
    CafeteriaProfileService,
    ProfileError,
    RestaurantError,
    RestaurantService,
    WasteError,
    WasteService,
)
from core.responses.api_response import error_response, success_response
from core.tenancy import stamp_tenant_id
from core.utils.pagination import paginate_queryset
from permissions.base import HasAnyPermission, HasPermission, user_has_any


def _branch_id(request):
    return request.query_params.get("branch_id") or getattr(request.user, "branch_id", None)


class CafeteriaProfileView(APIView):
    permission_classes = [
        IsAuthenticated,
        HasAnyPermission("restaurant.view", "cafeteria.dashboard.view", "cafeteria.settings.view"),
    ]

    def get(self, request):
        branch_id = _branch_id(request)
        if not branch_id:
            return error_response(
                message="branch_id is required.", status=status.HTTP_400_BAD_REQUEST
            )
        try:
            row = CafeteriaProfileService.get_for_branch(
                branch_id=branch_id, user=request.user, request=request
            )
        except ProfileError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        if not row:
            return success_response(data=None)
        return success_response(data=CafeteriaProfileService.serialize(row))

    def put(self, request):
        if not user_has_any(
            request.user,
            "restaurant.manage",
            "cafeteria.settings.update",
        ):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = CafeteriaProfileService.upsert(
                data=data, user=request.user, request=request
            )
        except ProfileError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=CafeteriaProfileService.serialize(row),
            message="Cafeteria profile saved.",
        )


class BaristaQueueView(APIView):
    permission_classes = [
        IsAuthenticated,
        HasAnyPermission(
            "restaurant.kitchen",
            "restaurant.view",
            "cafeteria.barista.queue",
        ),
    ]

    def get(self, request):
        data = BaristaService.queue(
            branch_id=_branch_id(request),
            station_id=request.query_params.get("station_id"),
            user=request.user,
            request=request,
        )
        return success_response(data=data)


class BaristaTicketActionView(APIView):
    permission_classes = [
        IsAuthenticated,
        HasAnyPermission(
            "restaurant.kitchen",
            "restaurant.orders.update",
            "cafeteria.barista.queue",
        ),
    ]

    def post(self, request, pk, action):
        try:
            order = RestaurantService.get_order(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return error_response(message="Order not found.", status=status.HTTP_404_NOT_FOUND)
        fn = {
            "accept": BaristaService.accept,
            "start": BaristaService.start,
            "ready": BaristaService.ready,
            "complete": BaristaService.complete,
        }.get(action)
        if not fn:
            return error_response(message="Unknown action.", status=status.HTTP_400_BAD_REQUEST)
        try:
            order = fn(order=order, user=request.user, request=request)
        except (BaristaError, RestaurantError) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=BaristaService.serialize_ticket(order),
            message=f"Order {action}ed.",
        )


class WasteListCreateView(APIView):
    permission_classes = [
        IsAuthenticated,
        HasAnyPermission("restaurant.view", "cafeteria.waste.view", "inventory.view"),
    ]

    def get(self, request):
        qs = WasteService.list(
            branch_id=_branch_id(request),
            approval_status=request.query_params.get("approval_status"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(
            request, qs, lambda items: [WasteService.serialize(w) for w in items]
        )

    def post(self, request):
        if not user_has_any(
            request.user,
            "restaurant.manage",
            "cafeteria.waste.create",
            "inventory.manage",
        ):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = WasteService.create(data=data, user=request.user, request=request)
        except WasteError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=WasteService.serialize(row),
            message="Waste recorded.",
            status=status.HTTP_201_CREATED,
        )


class WasteApproveView(APIView):
    permission_classes = [
        IsAuthenticated,
        HasAnyPermission("restaurant.manage", "cafeteria.waste.approve"),
    ]

    def post(self, request, pk):
        try:
            row = WasteService.get(pk=pk, user=request.user, request=request)
            row = WasteService.approve(waste=row, user=request.user, request=request)
        except ObjectDoesNotExist:
            return error_response(message="Waste not found.", status=status.HTTP_404_NOT_FOUND)
        except WasteError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=WasteService.serialize(row), message="Waste approved.")


class BaristaListCreateView(APIView):
    permission_classes = [
        IsAuthenticated,
        HasAnyPermission("restaurant.view", "cafeteria.staff.view"),
    ]

    def get(self, request):
        qs = BaristaService.list_baristas(
            branch_id=_branch_id(request), user=request.user, request=request
        )
        return paginate_queryset(
            request, qs, lambda items: [BaristaService.serialize_barista(b) for b in items]
        )

    def post(self, request):
        if not user_has_any(request.user, "restaurant.manage", "cafeteria.staff.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = BaristaService.create_barista(
                data=data, user=request.user, request=request
            )
        except BaristaError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=BaristaService.serialize_barista(row),
            message="Barista created.",
            status=status.HTTP_201_CREATED,
        )


class ItemVariantListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request, pk):
        try:
            item = RestaurantService.get_item(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return error_response(message="Item not found.", status=status.HTTP_404_NOT_FOUND)
        qs = item.variants.filter(deleted_at__isnull=True).order_by("sort_order", "name")
        return success_response(data=[serialize_variant(v) for v in qs])

    def post(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            item = RestaurantService.get_item(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return error_response(message="Item not found.", status=status.HTTP_404_NOT_FOUND)
        payload = stamp_tenant_id(dict(request.data), user=request.user, request=request)
        name = (payload.get("name") or "").strip()
        if not name:
            return error_response(message="Variant name is required.", status=status.HTTP_400_BAD_REQUEST)
        row = MenuItemVariant.objects.create(
            tenant_id=payload.get("tenant_id") or item.tenant_id,
            menu_item=item,
            name=name,
            sku=(payload.get("sku") or "").strip(),
            barcode=(payload.get("barcode") or "").strip(),
            price_adjustment=payload.get("price_adjustment") or 0,
            recipe_qty_multiplier=payload.get("recipe_qty_multiplier") or 1,
            is_default=bool(payload.get("is_default")),
            is_available=payload.get("is_available", True),
            sort_order=int(payload.get("sort_order") or 100),
            created_by=request.user,
        )
        return success_response(
            data=serialize_variant(row),
            message="Variant created.",
            status=status.HTTP_201_CREATED,
        )


class RecipeActivateView(APIView):
    permission_classes = [
        IsAuthenticated,
        HasAnyPermission("restaurant.manage", "restaurant.menu.update", "cafeteria.recipes.update"),
    ]

    def post(self, request, pk):
        try:
            recipe = RestaurantService.get_recipe(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return error_response(message="Recipe not found.", status=status.HTTP_404_NOT_FOUND)
        # Archive other actives for same menu item
        Recipe.active_objects().filter(
            menu_item_id=recipe.menu_item_id, status=Recipe.STATUS_ACTIVE
        ).exclude(pk=recipe.pk).update(status=Recipe.STATUS_ARCHIVED, is_active=False)
        recipe.status = Recipe.STATUS_ACTIVE
        recipe.is_active = True
        recipe.updated_by = request.user
        recipe.save(update_fields=["status", "is_active", "updated_by", "updated_at"])
        return success_response(data=serialize_recipe(recipe), message="Recipe activated.")


class RecipeCostingView(APIView):
    permission_classes = [
        IsAuthenticated,
        HasAnyPermission("restaurant.view", "cafeteria.recipes.view"),
    ]

    def get(self, request, pk):
        try:
            recipe = RestaurantService.get_recipe(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return error_response(message="Recipe not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(data=serialize_recipe(recipe))


class ItemCustomizeByProductView(APIView):
    """POS helper: menu item + variants + modifier groups for a product id."""

    permission_classes = [
        IsAuthenticated,
        HasAnyPermission("restaurant.view", "pos.access", "cafeteria.pos.use"),
    ]

    def get(self, request, product_id):
        data = RestaurantService.get_item_customize_payload(
            product_id=product_id, user=request.user, request=request
        )
        return success_response(data=data)
