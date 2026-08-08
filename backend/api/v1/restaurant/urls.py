from django.urls import path

from api.v1.restaurant.views import (
    CategoryListCreateView,
    ItemListCreateView,
    OrderAddLineView,
    OrderDetailView,
    OrderListCreateView,
    OrderPosPayloadView,
    OrderStatusView,
    RestaurantSummaryView,
    TableListCreateView,
    TableStatusView,
)

urlpatterns = [
    path("summary/", RestaurantSummaryView.as_view(), name="restaurant-summary"),
    path("categories/", CategoryListCreateView.as_view(), name="restaurant-categories"),
    path("items/", ItemListCreateView.as_view(), name="restaurant-items"),
    path("tables/", TableListCreateView.as_view(), name="restaurant-tables"),
    path("tables/<uuid:pk>/status/", TableStatusView.as_view(), name="restaurant-table-status"),
    path("orders/", OrderListCreateView.as_view(), name="restaurant-orders"),
    path("orders/<uuid:pk>/", OrderDetailView.as_view(), name="restaurant-order-detail"),
    path("orders/<uuid:pk>/pos/", OrderPosPayloadView.as_view(), name="restaurant-order-pos"),
    path("orders/<uuid:pk>/status/", OrderStatusView.as_view(), name="restaurant-order-status"),
    path("orders/<uuid:pk>/lines/", OrderAddLineView.as_view(), name="restaurant-order-lines"),
]
