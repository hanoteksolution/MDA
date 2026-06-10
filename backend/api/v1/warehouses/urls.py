from django.urls import path

from api.v1.inventory.views import WarehouseDetailView, WarehouseListCreateView

urlpatterns = [
    path("", WarehouseListCreateView.as_view(), name="warehouse-list"),
    path("<uuid:pk>/", WarehouseDetailView.as_view(), name="warehouse-detail"),
]
