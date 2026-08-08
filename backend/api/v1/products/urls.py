from django.urls import path

from api.v1.products.views import (
    ApplicableAttributesView,
    AttributeDefinitionDetailView,
    AttributeDefinitionListCreateView,
    CategoryAttributeAssignView,
    ProductBarcodeView,
    ProductDetailView,
    ProductImageUploadView,
    ProductListCreateView,
    ProductSearchView,
)

urlpatterns = [
    path("", ProductListCreateView.as_view(), name="product-list"),
    path("upload-image/", ProductImageUploadView.as_view(), name="product-upload-image"),
    path("search/", ProductSearchView.as_view(), name="product-search"),
    path("barcode/<str:barcode>/", ProductBarcodeView.as_view(), name="product-barcode"),
    path("attributes/", AttributeDefinitionListCreateView.as_view(), name="attribute-list"),
    path(
        "attributes/applicable/",
        ApplicableAttributesView.as_view(),
        name="attribute-applicable",
    ),
    path(
        "attributes/<uuid:pk>/",
        AttributeDefinitionDetailView.as_view(),
        name="attribute-detail",
    ),
    path(
        "categories/<uuid:category_id>/attributes/",
        CategoryAttributeAssignView.as_view(),
        name="category-attribute-assign",
    ),
    path("<uuid:pk>/", ProductDetailView.as_view(), name="product-detail"),
]
