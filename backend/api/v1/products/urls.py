from django.urls import path

from api.v1.products.views import (
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
    path("<uuid:pk>/", ProductDetailView.as_view(), name="product-detail"),
]
