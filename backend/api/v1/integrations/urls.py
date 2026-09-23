"""Tenant-facing integration operations. Provider configuration lives in ``platform_urls``."""

from django.urls import path

from api.v1.integrations.payment_views import (
    PaymentIntentDetailView,
    PaymentIntentListCreateView,
    PaymentWebhookView,
)
from api.v1.integrations.sms_billing_views import (
    TenantSmsBillingSummaryView,
    TenantSmsLedgerView,
    TenantSmsPackageListView,
    TenantSmsPurchaseDetailView,
    TenantSmsPurchaseListCreateView,
)
from api.v1.integrations.views import SmsLogListView, SmsSendView, SmsTemplateListCreateView

urlpatterns = [
    path("sms-templates/", SmsTemplateListCreateView.as_view(), name="integrations-sms-templates"),
    path("sms-logs/", SmsLogListView.as_view(), name="integrations-sms-logs"),
    path("sms/send/", SmsSendView.as_view(), name="integrations-sms-send"),
    path("sms-billing/packages/", TenantSmsPackageListView.as_view(), name="integrations-sms-billing-packages"),
    path("sms-billing/summary/", TenantSmsBillingSummaryView.as_view(), name="integrations-sms-billing-summary"),
    path("sms-billing/ledger/", TenantSmsLedgerView.as_view(), name="integrations-sms-billing-ledger"),
    path("sms-billing/purchases/", TenantSmsPurchaseListCreateView.as_view(), name="integrations-sms-billing-purchases"),
    path("sms-billing/purchases/<uuid:pk>/", TenantSmsPurchaseDetailView.as_view(), name="integrations-sms-billing-purchase"),
    path("payments/intents/", PaymentIntentListCreateView.as_view(), name="integrations-payment-intents"),
    path("payments/intents/<uuid:pk>/", PaymentIntentDetailView.as_view(), name="integrations-payment-intent-detail"),
    # Public, HMAC-verified provider callback (selected by the unguessable provider id).
    path("payments/webhooks/<uuid:provider_id>/", PaymentWebhookView.as_view(), name="integrations-payment-webhook"),
]
