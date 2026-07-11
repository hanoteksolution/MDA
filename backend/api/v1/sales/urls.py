from django.urls import path

from api.v1.sales.views import (
    CustomerMonthlyAccountView,
    DailyOpsView,
    ExpenseDetailView,
    ExpenseListCreateView,
    InvoiceDeliveryNoteView,
    InvoiceDetailView,
    InvoiceListCreateView,
    InvoiceMarkPaidView,
    InvoiceReceiptView,
    QuotationDetailView,
    QuotationListCreateView,
    SalesSummaryView,
)

urlpatterns = [
    path("summary/", SalesSummaryView.as_view(), name="sales-summary"),
    path("daily-ops/", DailyOpsView.as_view(), name="sales-daily-ops"),
    path("customer-monthly/", CustomerMonthlyAccountView.as_view(), name="sales-customer-monthly"),
    path("expenses/", ExpenseListCreateView.as_view(), name="sales-expenses"),
    path("expenses/<uuid:pk>/", ExpenseDetailView.as_view(), name="sales-expense-detail"),
    path("invoices/", InvoiceListCreateView.as_view(), name="invoice-list"),
    path("invoices/<uuid:pk>/", InvoiceDetailView.as_view(), name="invoice-detail"),
    path("invoices/<uuid:pk>/mark-paid/", InvoiceMarkPaidView.as_view(), name="invoice-mark-paid"),
    path("invoices/<uuid:pk>/receipt/", InvoiceReceiptView.as_view(), name="invoice-receipt"),
    path("invoices/<uuid:pk>/delivery-note/", InvoiceDeliveryNoteView.as_view(), name="invoice-delivery-note"),
    path("quotations/", QuotationListCreateView.as_view(), name="quotation-list"),
    path("quotations/<uuid:pk>/", QuotationDetailView.as_view(), name="quotation-detail"),
]
