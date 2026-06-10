from django.urls import path

from api.v1.customers.views import CustomerDetailView, CustomerListCreateView, CustomerSummaryView

urlpatterns = [
    path("", CustomerListCreateView.as_view(), name="customer-list"),
    path("summary/", CustomerSummaryView.as_view(), name="customer-summary"),
    path("<uuid:pk>/", CustomerDetailView.as_view(), name="customer-detail"),
]
