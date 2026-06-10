from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.products.models import Brand, Category, Product, Unit
from apps.products.serializers.catalog_serializers import (
    serialize_brand,
    serialize_category,
    serialize_product,
    serialize_unit,
)
from apps.products.services.product_service import BrandService, CategoryService, ProductService, UnitService
from core.responses.api_response import error_response, success_response
from core.utils.media import save_product_image
from core.utils.pagination import paginate_queryset
from permissions.base import HasPermission


class CategoryListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("products.view")]

    def get(self, request):
        qs = CategoryService.list(search=request.query_params.get("search"))
        return paginate_queryset(request, qs, lambda items: [serialize_category(c) for c in items])

    def post(self, request):
        if not request.user.has_permission("products.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        cat = CategoryService.create(data=request.data, user=request.user)
        return success_response(data=serialize_category(cat), message="Category created.", status=status.HTTP_201_CREATED)


class CategoryDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("products.view")]

    def put(self, request, pk):
        if not request.user.has_permission("products.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        cat = CategoryService.list().get(pk=pk)
        cat = CategoryService.update(instance=cat, data=request.data, user=request.user)
        return success_response(data=serialize_category(cat), message="Category updated.")

    def delete(self, request, pk):
        if not request.user.has_permission("products.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        cat = CategoryService.list().get(pk=pk)
        cat.soft_delete(user=request.user)
        return success_response(message="Category deleted.")


class BrandListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("products.view")]

    def get(self, request):
        qs = BrandService.list(search=request.query_params.get("search"))
        return paginate_queryset(request, qs, lambda items: [serialize_brand(b) for b in items])

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
        brand = BrandService.list().get(pk=pk)
        brand = BrandService.update(instance=brand, data=request.data, user=request.user)
        return success_response(data=serialize_brand(brand), message="Brand updated.")

    def delete(self, request, pk):
        if not request.user.has_permission("products.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        brand = BrandService.list().get(pk=pk)
        brand.soft_delete(user=request.user)
        return success_response(message="Brand deleted.")


class UnitListView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("products.view")]

    def get(self, request):
        units = UnitService.list()
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
        )
        return paginate_queryset(
            request,
            qs,
            lambda items: [serialize_product(p, include_stock=True, request=request) for p in items],
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
        product = ProductService.create(
            data=data, user=request.user, initial_stock=initial_stock, warehouse=warehouse
        )
        return success_response(
            data=serialize_product(product, include_stock=True, request=request),
            message="Product created.",
            status=status.HTTP_201_CREATED,
        )


class ProductDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("products.view")]

    def get(self, request, pk):
        product = ProductService.list().get(pk=pk)
        return success_response(data=serialize_product(product, include_stock=True, request=request))

    def put(self, request, pk):
        if not request.user.has_permission("products.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        product = ProductService.list().get(pk=pk)
        product = ProductService.update(product=product, data=request.data, user=request.user)
        return success_response(
            data=serialize_product(product, include_stock=True, request=request),
            message="Product updated.",
        )

    def delete(self, request, pk):
        if not request.user.has_permission("products.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        product = ProductService.list().get(pk=pk)
        ProductService.soft_delete(product=product, user=request.user)
        return success_response(message="Product deleted.")


class ProductSearchView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("products.view")]

    def get(self, request):
        q = request.query_params.get("q", "")
        limit = min(int(request.query_params.get("limit", 20)), 50)
        qs = ProductService.list(search=q, is_active=True)[:limit]
        return success_response(data=[serialize_product(p, request=request) for p in qs])


class ProductBarcodeView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("products.view")]

    def get(self, request, barcode):
        try:
            product = ProductService.get_by_barcode(barcode)
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
