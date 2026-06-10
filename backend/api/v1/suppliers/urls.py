from django.urls import path

from api.v1.suppliers.views import SupplierDetailView, SupplierListCreateView, SupplierSummaryView

urlpatterns = [
    path("", SupplierListCreateView.as_view(), name="supplier-list"),
    path("summary/", SupplierSummaryView.as_view(), name="supplier-summary"),
    path("<uuid:pk>/", SupplierDetailView.as_view(), name="supplier-detail"),
]
