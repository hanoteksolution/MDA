from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.restaurant.serializers import (
    serialize_floor,
    serialize_ingredient,
    serialize_category,
    serialize_item,
    serialize_modifier,
    serialize_modifier_group,
    serialize_order,
    serialize_recipe,
    serialize_station,
    serialize_table,
)
from apps.restaurant.services import RestaurantError, RestaurantService
from core.responses.api_response import error_response, success_response
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission, user_has_any


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
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.create"):
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


class CategoryDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request, pk):
        try:
            row = RestaurantService.get_category(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Category")
        return success_response(data=serialize_category(row))

    def put(self, request, pk):
        return self._update(request, pk)

    def patch(self, request, pk):
        return self._update(request, pk)

    def _update(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = RestaurantService.get_category(pk=pk, user=request.user, request=request)
            row = RestaurantService.update_category(
                category=row, data=request.data, user=request.user, request=request
            )
        except ObjectDoesNotExist:
            return _not_found("Category")
        except RestaurantError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_category(row), message="Category updated.")

    def delete(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = RestaurantService.get_category(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Category")
        RestaurantService.soft_delete_category(category=row, user=request.user, request=request)
        return success_response(message="Category deleted.")


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
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.create"):
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


class ItemDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request, pk):
        try:
            row = RestaurantService.get_item(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Menu item")
        return success_response(data=serialize_item(row))

    def put(self, request, pk):
        return self._update(request, pk)

    def patch(self, request, pk):
        return self._update(request, pk)

    def _update(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = RestaurantService.get_item(pk=pk, user=request.user, request=request)
            row = RestaurantService.update_item(
                item=row, data=request.data, user=request.user, request=request
            )
        except ObjectDoesNotExist:
            return _not_found("Menu item")
        except RestaurantError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_item(row), message="Menu item updated.")

    def delete(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = RestaurantService.get_item(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Menu item")
        RestaurantService.soft_delete_item(item=row, user=request.user, request=request)
        return success_response(message="Menu item deleted.")


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
        if not user_has_any(request.user, "restaurant.manage", "restaurant.tables.create"):
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


class TableDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request, pk):
        try:
            row = RestaurantService.get_table(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Table")
        return success_response(data=serialize_table(row))

    def put(self, request, pk):
        return self._update(request, pk)

    def patch(self, request, pk):
        return self._update(request, pk)

    def _update(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.tables.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = RestaurantService.get_table(pk=pk, user=request.user, request=request)
            row = RestaurantService.update_table(
                table=row, data=request.data, user=request.user, request=request
            )
        except ObjectDoesNotExist:
            return _not_found("Table")
        except RestaurantError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_table(row), message="Table updated.")

    def delete(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.tables.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = RestaurantService.get_table(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Table")
        RestaurantService.soft_delete_table(table=row, user=request.user, request=request)
        return success_response(message="Table deleted.")


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


class FloorListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request):
        qs = RestaurantService.list_floors(
            branch_id=_branch_id(request), user=request.user, request=request
        )
        return paginate_queryset(request, qs, lambda items: [serialize_floor(i) for i in items])

    def post(self, request):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.tables.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = RestaurantService.create_floor(data=data, user=request.user, request=request)
        except (RestaurantError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_floor(row), message="Floor created.", status=status.HTTP_201_CREATED)


class FloorDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request, pk):
        try:
            row = RestaurantService.get_floor(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Floor")
        return success_response(data=serialize_floor(row))

    def patch(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.tables.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = RestaurantService.get_floor(pk=pk, user=request.user, request=request)
            row = RestaurantService.update_floor(floor=row, data=request.data, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Floor")
        except RestaurantError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_floor(row), message="Floor updated.")

    def delete(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.tables.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = RestaurantService.get_floor(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Floor")
        RestaurantService.soft_delete_floor(floor=row, user=request.user, request=request)
        return success_response(message="Floor deleted.")


class StationListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request):
        qs = RestaurantService.list_stations(
            branch_id=_branch_id(request), user=request.user, request=request
        )
        return paginate_queryset(request, qs, lambda items: [serialize_station(i) for i in items])

    def post(self, request):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.kitchen"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = RestaurantService.create_station(data=data, user=request.user, request=request)
        except (RestaurantError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_station(row), message="Station created.", status=status.HTTP_201_CREATED)


class StationDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request, pk):
        try:
            row = RestaurantService.get_station(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Kitchen station")
        return success_response(data=serialize_station(row))

    def patch(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.kitchen"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = RestaurantService.get_station(pk=pk, user=request.user, request=request)
            row = RestaurantService.update_station(station=row, data=request.data, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Kitchen station")
        except RestaurantError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_station(row), message="Station updated.")

    def delete(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.kitchen"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = RestaurantService.get_station(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Kitchen station")
        RestaurantService.soft_delete_station(station=row, user=request.user, request=request)
        return success_response(message="Station deleted.")


class ModifierGroupListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request):
        qs = RestaurantService.list_modifier_groups(
            branch_id=_branch_id(request), user=request.user, request=request
        )
        return paginate_queryset(request, qs, lambda items: [serialize_modifier_group(i) for i in items])

    def post(self, request):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = RestaurantService.create_modifier_group(data=data, user=request.user, request=request)
        except (RestaurantError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_modifier_group(row), message="Modifier group created.", status=status.HTTP_201_CREATED)


class ModifierGroupDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request, pk):
        try:
            row = RestaurantService.get_modifier_group(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Modifier group")
        return success_response(data=serialize_modifier_group(row))

    def patch(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = RestaurantService.get_modifier_group(pk=pk, user=request.user, request=request)
            row = RestaurantService.update_modifier_group(group=row, data=request.data, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Modifier group")
        except RestaurantError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_modifier_group(row), message="Modifier group updated.")

    def delete(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = RestaurantService.get_modifier_group(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Modifier group")
        RestaurantService.soft_delete_modifier_group(group=row, user=request.user, request=request)
        return success_response(message="Modifier group deleted.")


class ModifierListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request):
        qs = RestaurantService.list_modifiers(
            branch_id=_branch_id(request),
            group_id=request.query_params.get("group_id"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(request, qs, lambda items: [serialize_modifier(i) for i in items])

    def post(self, request):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = RestaurantService.create_modifier(data=data, user=request.user, request=request)
        except (RestaurantError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_modifier(row), message="Modifier created.", status=status.HTTP_201_CREATED)


class ModifierDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request, pk):
        try:
            row = RestaurantService.get_modifier(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Modifier")
        return success_response(data=serialize_modifier(row))

    def patch(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = RestaurantService.get_modifier(pk=pk, user=request.user, request=request)
            row = RestaurantService.update_modifier(modifier=row, data=request.data, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Modifier")
        except RestaurantError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_modifier(row), message="Modifier updated.")

    def delete(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = RestaurantService.get_modifier(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Modifier")
        RestaurantService.soft_delete_modifier(modifier=row, user=request.user, request=request)
        return success_response(message="Modifier deleted.")


class IngredientListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request):
        qs = RestaurantService.list_ingredients(
            branch_id=_branch_id(request), user=request.user, request=request
        )
        return paginate_queryset(request, qs, lambda items: [serialize_ingredient(i) for i in items])

    def post(self, request):
        if not user_has_any(request.user, "restaurant.manage", "inventory.manage", "products.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = RestaurantService.create_ingredient(data=data, user=request.user, request=request)
        except (RestaurantError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_ingredient(row), message="Ingredient created.", status=status.HTTP_201_CREATED)


class IngredientDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request, pk):
        try:
            row = RestaurantService.get_ingredient(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Ingredient")
        return success_response(data=serialize_ingredient(row))

    def patch(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "inventory.manage", "products.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = RestaurantService.get_ingredient(pk=pk, user=request.user, request=request)
            row = RestaurantService.update_ingredient(ingredient=row, data=request.data, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Ingredient")
        except RestaurantError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_ingredient(row), message="Ingredient updated.")

    def delete(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "inventory.manage", "products.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = RestaurantService.get_ingredient(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Ingredient")
        RestaurantService.soft_delete_ingredient(ingredient=row, user=request.user, request=request)
        return success_response(message="Ingredient deleted.")


class RecipeListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request):
        qs = RestaurantService.list_recipes(
            branch_id=_branch_id(request),
            menu_item_id=request.query_params.get("menu_item_id"),
            user=request.user,
            request=request,
        )
        return paginate_queryset(request, qs, lambda items: [serialize_recipe(i, include_ingredients=False) for i in items])

    def post(self, request):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = dict(request.data)
        data.setdefault("branch_id", _branch_id(request))
        try:
            row = RestaurantService.create_recipe(data=data, user=request.user, request=request)
        except (RestaurantError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_recipe(row), message="Recipe created.", status=status.HTTP_201_CREATED)


class RecipeDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def get(self, request, pk):
        try:
            row = RestaurantService.get_recipe(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Recipe")
        return success_response(data=serialize_recipe(row))

    def patch(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = RestaurantService.get_recipe(pk=pk, user=request.user, request=request)
            row = RestaurantService.update_recipe(recipe=row, data=request.data, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Recipe")
        except RestaurantError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_recipe(row), message="Recipe updated.")

    def delete(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = RestaurantService.get_recipe(pk=pk, user=request.user, request=request)
        except ObjectDoesNotExist:
            return _not_found("Recipe")
        RestaurantService.soft_delete_recipe(recipe=row, user=request.user, request=request)
        return success_response(message="Recipe deleted.")


class RecipeIngredientCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def post(self, request, pk):
        if not user_has_any(request.user, "restaurant.manage", "restaurant.menu.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            recipe = RestaurantService.get_recipe(pk=pk, user=request.user, request=request)
            RestaurantService.add_recipe_ingredient(
                recipe=recipe, data=request.data, user=request.user, request=request
            )
            recipe.refresh_from_db()
        except (RestaurantError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_recipe(recipe), message="Recipe ingredient added.")


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
        if not user_has_any(
            request.user,
            "restaurant.manage",
            "restaurant.floor",
            "restaurant.orders.create",
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
        if not user_has_any(
            request.user,
            "restaurant.manage",
            "restaurant.floor",
            "restaurant.kitchen",
            "restaurant.orders.update",
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
        if not user_has_any(
            request.user,
            "restaurant.manage",
            "restaurant.floor",
            "restaurant.orders.update",
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


class OrderSubmitView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def post(self, request, pk):
        if not user_has_any(
            request.user,
            "restaurant.manage",
            "restaurant.floor",
            "restaurant.orders.update",
        ):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            order = RestaurantService.get_order(pk=pk, user=request.user, request=request)
            order = RestaurantService.update_order_status(
                order=order, status=order.STATUS_SUBMITTED, user=request.user
            )
        except (RestaurantError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_order(order), message="Order submitted.")


class OrderCancelView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def post(self, request, pk):
        if not user_has_any(
            request.user,
            "restaurant.manage",
            "restaurant.floor",
            "restaurant.orders.cancel",
        ):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            order = RestaurantService.get_order(pk=pk, user=request.user, request=request)
            order = RestaurantService.update_order_status(
                order=order, status=order.STATUS_CANCELLED, user=request.user
            )
        except (RestaurantError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_order(order), message="Order cancelled.")


class OrderVoidView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def post(self, request, pk):
        if not user_has_any(
            request.user,
            "restaurant.manage",
            "restaurant.orders.void",
        ):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            order = RestaurantService.get_order(pk=pk, user=request.user, request=request)
            order = RestaurantService.update_order_status(
                order=order, status=order.STATUS_VOIDED, user=request.user
            )
        except (RestaurantError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_order(order), message="Order voided.")


class OrderRefundView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

    def post(self, request, pk):
        if not user_has_any(
            request.user,
            "restaurant.manage",
            "restaurant.orders.refund",
        ):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            order = RestaurantService.get_order(pk=pk, user=request.user, request=request)
            order = RestaurantService.update_order_status(
                order=order, status=order.STATUS_REFUNDED, user=request.user
            )
        except (RestaurantError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_order(order), message="Order refunded.")
