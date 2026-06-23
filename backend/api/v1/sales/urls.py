from django.urls import path

from api.v1.sales.views import (
    InvoiceDeliveryNoteView,
    InvoiceDetailView,
    InvoiceListCreateView,
    InvoiceReceiptView,
    QuotationDetailView,
    QuotationListCreateView,
    SalesSummaryView,
)

urlpatterns = [
    path("summary/", SalesSummaryView.as_view(), name="sales-summary"),
    path("invoices/", InvoiceListCreateView.as_view(), name="invoice-list"),
    path("invoices/<uuid:pk>/", InvoiceDetailView.as_view(), name="invoice-detail"),
    path("invoices/<uuid:pk>/receipt/", InvoiceReceiptView.as_view(), name="invoice-receipt"),
    path("invoices/<uuid:pk>/delivery-note/", InvoiceDeliveryNoteView.as_view(), name="invoice-delivery-note"),
    path("quotations/", QuotationListCreateView.as_view(), name="quotation-list"),
    path("quotations/<uuid:pk>/", QuotationDetailView.as_view(), name="quotation-detail"),
]
