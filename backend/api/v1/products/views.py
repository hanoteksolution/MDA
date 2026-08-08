from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.products.models import Brand, Category, Product, Unit
from apps.products.serializers.catalog_serializers import (
    serialize_brand,
    serialize_category,
    serialize_product,
    serialize_products_batch,
    serialize_unit,
)
from apps.products.services.attribute_service import AttributeService, AttributeValidationError
from apps.products.services.product_service import BrandService, CategoryService, ProductService, UnitService
from core.cache.catalog_cache import CatalogCache
from core.responses.api_response import error_response, success_response
from core.utils.media import save_product_image
from core.utils.pagination import paginate_queryset, paginate_sequence
from permissions.base import HasPermission


class CategoryListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("products.view")]

    def get(self, request):
        if request.query_params.get("search"):
            qs = CategoryService.list(
                search=request.query_params.get("search"),
                user=request.user,
                request=request,
            )
            return paginate_queryset(request, qs, lambda rows: [serialize_category(c) for c in rows])
        tenant_id = CatalogCache.tenant_id(user=request.user, request=request)
        items = CatalogCache.get_or_load(
            prefix="categories",
            tenant_id=tenant_id,
            loader=lambda: CategoryService.list(user=request.user, request=request),
        )
        return paginate_sequence(request, items, lambda rows: [serialize_category(c) for c in rows])

    def post(self, request):
        if not request.user.has_permission("products.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            cat = CategoryService.create(data=request.data, user=request.user)
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_category(cat), message="Category created.", status=status.HTTP_201_CREATED)


class CategoryDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("products.view")]

    def put(self, request, pk):
        if not request.user.has_permission("products.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        cat = CategoryService.list(user=request.user).get(pk=pk)
        cat = CategoryService.update(instance=cat, data=request.data, user=request.user)
        return success_response(data=serialize_category(cat), message="Category updated.")

    def delete(self, request, pk):
        if not request.user.has_permission("products.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        cat = CategoryService.list(user=request.user).get(pk=pk)
        cat.soft_delete(user=request.user)
        CatalogCache.invalidate_tenant(CatalogCache.tenant_id(user=request.user, request=request))
        return success_response(message="Category deleted.")


class BrandListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("products.view")]

    def get(self, request):
        if request.query_params.get("search"):
            qs = BrandService.list(
                search=request.query_params.get("search"),
                user=request.user,
                request=request,
            )
            return paginate_queryset(request, qs, lambda items: [serialize_brand(b) for b in items])
        tenant_id = CatalogCache.tenant_id(user=request.user, request=request)
        items = CatalogCache.get_or_load(
            prefix="brands",
            tenant_id=tenant_id,
            loader=lambda: BrandService.list(user=request.user, request=request),
        )
        return paginate_sequence(request, items, lambda rows: [serialize_brand(b) for b in rows])

    def post(self, request):
        if not request.user.has_permission("products.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        brand = BrandService.create(data=request.data, user=request.user)
        return success_response(data=serialize_brand(brand), message="Brand created.", status=status.HTTP_201_CREATED)


class BrandDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("products.view")]

    def put(self, request, pk):
        if not request.user.has_permission("products.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        brand = BrandService.list(user=request.user).get(pk=pk)
        brand = BrandService.update(instance=brand, data=request.data, user=request.user)
        return success_response(data=serialize_brand(brand), message="Brand updated.")

    def delete(self, request, pk):
        if not request.user.has_permission("products.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        brand = BrandService.list(user=request.user).get(pk=pk)
        brand.soft_delete(user=request.user)
        CatalogCache.invalidate_tenant(CatalogCache.tenant_id(user=request.user, request=request))
        return success_response(message="Brand deleted.")


class UnitListView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("products.view")]

    def get(self, request):
        tenant_id = CatalogCache.tenant_id(user=request.user, request=request)
        units = CatalogCache.get_or_load(
            prefix="units",
            tenant_id=tenant_id,
            loader=lambda: UnitService.list(user=request.user, request=request),
        )
        return success_response(data=[serialize_unit(u) for u in units])

    def post(self, request):
        if not request.user.has_permission("products.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        name = request.data.get("name")
        abbreviation = request.data.get("abbreviation") or name[:3].lower() if name else ""
        if not name:
            return error_response(message="Unit name is required.", status=status.HTTP_400_BAD_REQUEST)
        unit = UnitService.create(data={"name": name, "abbreviation": abbreviation}, user=request.user)
        return success_response(data=serialize_unit(unit), message="Unit created.", status=status.HTTP_201_CREATED)


class ProductListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("products.view")]

    def get(self, request):
        is_active_param = request.query_params.get("is_active")
        is_active = None
        if is_active_param == "true":
            is_active = True
        elif is_active_param == "false":
            is_active = False
        qs = ProductService.list(
            search=request.query_params.get("search"),
            category_id=request.query_params.get("category"),
            brand_id=request.query_params.get("brand"),
            is_active=is_active,
            user=request.user,
        )
        return paginate_queryset(
            request,
            qs,
            lambda items: serialize_products_batch(
                items,
                include_stock=True,
                request=request,
                include_attributes=False,
            ),
        )

    def post(self, request):
        if not request.user.has_permission("products.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        data = request.data.copy()
        initial_stock = data.pop("initial_stock", 0)
        warehouse_id = data.pop("warehouse_id", None)
        warehouse = None
        if warehouse_id:
            from apps.inventory.models import Warehouse
            warehouse = Warehouse.active_objects().get(id=warehouse_id)
        try:
            product = ProductService.create(
                data=data,
                user=request.user,
                request=request,
                initial_stock=initial_stock,
                warehouse=warehouse,
            )
        except (ValueError, AttributeValidationError) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_product(product, include_stock=True, request=request),
            message="Product created.",
            status=status.HTTP_201_CREATED,
        )


class ProductDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("products.view")]

    def get(self, request, pk):
        product = ProductService.list(user=request.user).get(pk=pk)
        return success_response(data=serialize_product(product, include_stock=True, request=request))

    def put(self, request, pk):
        if not request.user.has_permission("products.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        product = ProductService.list(user=request.user).get(pk=pk)
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        stock = data.pop("stock", data.pop("initial_stock", None))
        warehouse_id = data.pop("warehouse_id", None)
        warehouse = None
        if warehouse_id:
            from apps.inventory.models import Warehouse
            warehouse = Warehouse.active_objects().get(id=warehouse_id)
        try:
            product = ProductService.update(
                product=product,
                data=data,
                user=request.user,
                request=request,
                stock=stock,
                warehouse=warehouse,
            )
        except (ValueError, AttributeValidationError) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=serialize_product(product, include_stock=True, request=request),
            message="Product updated.",
        )

    def delete(self, request, pk):
        if not request.user.has_permission("products.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        product = ProductService.list(user=request.user).get(pk=pk)
        ProductService.soft_delete(product=product, user=request.user)
        return success_response(message="Product deleted.")


class ProductSearchView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("products.view")]

    def get(self, request):
        q = request.query_params.get("q", "")
        limit = min(int(request.query_params.get("limit", 20)), 50)
        category_id = request.query_params.get("category")
        products = list(
            ProductService.search_for_pos(
                search=q,
                category_id=category_id,
                limit=limit,
                user=request.user,
                request=request,
            )
        )
        return success_response(
            data=serialize_products_batch(
                products,
                include_stock=True,
                request=request,
                include_attributes=False,
            )
        )


class ProductBarcodeView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("products.view")]

    def get(self, request, barcode):
        try:
            product = ProductService.get_by_barcode(barcode, user=request.user)
            return success_response(data=serialize_product(product, include_stock=True, request=request))
        except Product.DoesNotExist:
            return error_response(message="Product not found.", status=status.HTTP_404_NOT_FOUND)


class ProductImageUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.has_permission("products.create") and not request.user.has_permission(
            "products.update"
        ):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)

        uploaded = request.FILES.get("image")
        if not uploaded:
            return error_response(message="No image file provided.", status=status.HTTP_400_BAD_REQUEST)

        try:
            url = save_product_image(uploaded_file=uploaded)
        except ValueError as e:
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)

        return success_response(
            data={"url": url, "path": url},
            message="Image uploaded.",
            status=status.HTTP_201_CREATED,
        )


class AttributeDefinitionListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("products.view")]

    def get(self, request):
        qs = AttributeService.list_definitions(user=request.user, request=request)
        return success_response(
            data=[AttributeService.serialize_definition(d) for d in qs]
        )

    def post(self, request):
        if not request.user.has_permission("products.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            defn = AttributeService.create_definition(
                data=request.data, user=request.user, request=request
            )
        except AttributeValidationError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=AttributeService.serialize_definition(defn),
            message="Attribute created.",
            status=status.HTTP_201_CREATED,
        )


class AttributeDefinitionDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("products.view")]

    def get(self, request, pk):
        defn = AttributeService.list_definitions(user=request.user, request=request).get(pk=pk)
        return success_response(data=AttributeService.serialize_definition(defn))

    def put(self, request, pk):
        if not request.user.has_permission("products.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        defn = AttributeService.list_definitions(user=request.user, request=request).get(pk=pk)
        try:
            defn = AttributeService.update_definition(
                definition=defn, data=request.data, user=request.user
            )
        except AttributeValidationError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=AttributeService.serialize_definition(defn),
            message="Attribute updated.",
        )

    def delete(self, request, pk):
        if not request.user.has_permission("products.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        defn = AttributeService.list_definitions(user=request.user, request=request).get(pk=pk)
        if defn.tenant_id is None:
            return error_response(
                message="System attributes cannot be deleted.",
                status=status.HTTP_400_BAD_REQUEST,
            )
        defn.soft_delete(user=request.user)
        return success_response(message="Attribute deleted.")


class ApplicableAttributesView(APIView):
    """Attributes applicable for a category / business-type context (product form)."""

    permission_classes = [IsAuthenticated, HasPermission("products.view")]

    def get(self, request):
        applicable = AttributeService.resolve_applicable(
            user=request.user,
            request=request,
            category_id=request.query_params.get("category_id") or None,
            business_type_id=request.query_params.get("business_type_id") or None,
        )
        return success_response(
            data=[
                AttributeService.serialize_definition(
                    item["definition"],
                    is_required=item["is_required"],
                    source=item["source"],
                )
                for item in applicable
            ]
        )


class CategoryAttributeAssignView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("products.update")]

    def put(self, request, category_id):
        definition_id = request.data.get("definition_id")
        if not definition_id:
            return error_response(
                message="definition_id is required.", status=status.HTTP_400_BAD_REQUEST
            )
        # Ensure category is in tenant scope
        CategoryService.list(user=request.user).get(pk=category_id)
        link = AttributeService.assign_to_category(
            category_id=category_id,
            definition_id=definition_id,
            is_required=request.data.get("is_required"),
            sort_order=int(request.data.get("sort_order") or 100),
            user=request.user,
        )
        return success_response(
            data={
                "id": str(link.id),
                "category_id": str(link.category_id),
                "definition_id": str(link.definition_id),
                "is_required": link.is_required,
                "sort_order": link.sort_order,
            },
            message="Attribute assigned to category.",
        )
