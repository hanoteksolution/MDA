from django.urls import path

from api.v1.products.views import UnitListView

urlpatterns = [
    path("", UnitListView.as_view(), name="unit-list"),
]
