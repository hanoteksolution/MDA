from django.urls import path

from api.v1.products.views import CategoryDetailView, CategoryListCreateView

urlpatterns = [
    path("", CategoryListCreateView.as_view(), name="category-list"),
    path("<uuid:pk>/", CategoryDetailView.as_view(), name="category-detail"),
]
