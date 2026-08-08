from django.urls import path

from api.v1.restaurant.views import (
    CategoryDetailView,
    CategoryListCreateView,
    ItemDetailView,
    ItemListCreateView,
    OrderAddLineView,
    OrderDetailView,
    OrderListCreateView,
    OrderPosPayloadView,
    OrderStatusView,
    RestaurantSummaryView,
    TableDetailView,
    TableListCreateView,
    TableStatusView,
)

urlpatterns = [
    path("summary/", RestaurantSummaryView.as_view(), name="restaurant-summary"),
    path("categories/", CategoryListCreateView.as_view(), name="restaurant-categories"),
    path("categories/<uuid:pk>/", CategoryDetailView.as_view(), name="restaurant-category-detail"),
    path("items/", ItemListCreateView.as_view(), name="restaurant-items"),
    path("items/<uuid:pk>/", ItemDetailView.as_view(), name="restaurant-item-detail"),
    path("tables/", TableListCreateView.as_view(), name="restaurant-tables"),
    path("tables/<uuid:pk>/", TableDetailView.as_view(), name="restaurant-table-detail"),
    path("tables/<uuid:pk>/status/", TableStatusView.as_view(), name="restaurant-table-status"),
    path("orders/", OrderListCreateView.as_view(), name="restaurant-orders"),
    path("orders/<uuid:pk>/", OrderDetailView.as_view(), name="restaurant-order-detail"),
    path("orders/<uuid:pk>/pos/", OrderPosPayloadView.as_view(), name="restaurant-order-pos"),
    path("orders/<uuid:pk>/status/", OrderStatusView.as_view(), name="restaurant-order-status"),
    path("orders/<uuid:pk>/lines/", OrderAddLineView.as_view(), name="restaurant-order-lines"),
]
