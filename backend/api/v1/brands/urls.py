from django.urls import path

from api.v1.products.views import BrandDetailView, BrandListCreateView

urlpatterns = [
    path("", BrandListCreateView.as_view(), name="brand-list"),
    path("<uuid:pk>/", BrandDetailView.as_view(), name="brand-detail"),
]
