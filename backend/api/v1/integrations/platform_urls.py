"""Platform Admin → Integrations. Global platform administrators only; every call names ``tenant_id``."""

from django.urls import path

from api.v1.integrations.payment_views import (
    PaymentProviderDetailView,
    PaymentProviderListCreateView,
    PaymentWebhookEventListView,
    ReconciliationRecordListView,
    ReconciliationResolveView,
    ReconciliationRunView,
)
from api.v1.integrations.sms_billing_views import (
    PlatformSmsAdjustmentView,
    PlatformSmsBalanceListView,
    PlatformSmsBillingSettingsView,
    PlatformSmsPackageDetailView,
    PlatformSmsPackageListCreateView,
    PlatformSmsTenantLedgerView,
)
from api.v1.integrations.views import (
    CredentialDetailView,
    CredentialListCreateView,
    PlatformTenantBranchListView,
    SmsProviderDetailView,
    SmsProviderListCreateView,
)

urlpatterns = [
    path("sms-billing/packages/", PlatformSmsPackageListCreateView.as_view(), name="platform-sms-packages"),
    path("sms-billing/packages/<uuid:pk>/", PlatformSmsPackageDetailView.as_view(), name="platform-sms-package-detail"),
    path("sms-billing/settings/", PlatformSmsBillingSettingsView.as_view(), name="platform-sms-billing-settings"),
    path("sms-billing/balances/", PlatformSmsBalanceListView.as_view(), name="platform-sms-balances"),
    path("sms-billing/ledger/", PlatformSmsTenantLedgerView.as_view(), name="platform-sms-ledger"),
    path("sms-billing/adjustments/", PlatformSmsAdjustmentView.as_view(), name="platform-sms-adjustments"),
    path("branches/", PlatformTenantBranchListView.as_view(), name="platform-integrations-branches"),
    path("credentials/", CredentialListCreateView.as_view(), name="platform-integrations-credentials"),
    path("credentials/<uuid:pk>/", CredentialDetailView.as_view(), name="platform-integrations-credential-detail"),
    path("sms-providers/", SmsProviderListCreateView.as_view(), name="platform-integrations-sms-providers"),
    path("sms-providers/<uuid:pk>/", SmsProviderDetailView.as_view(), name="platform-integrations-sms-provider-detail"),
    path("payment-providers/", PaymentProviderListCreateView.as_view(), name="platform-integrations-payment-providers"),
    path("payment-providers/<uuid:pk>/", PaymentProviderDetailView.as_view(), name="platform-integrations-payment-provider-detail"),
    path("payments/webhook-events/", PaymentWebhookEventListView.as_view(), name="platform-integrations-webhook-events"),
    path("payments/reconcile/", ReconciliationRunView.as_view(), name="platform-integrations-reconcile"),
    path("payments/reconciliation/", ReconciliationRecordListView.as_view(), name="platform-integrations-reconciliation"),
    path("payments/reconciliation/<uuid:pk>/resolve/", ReconciliationResolveView.as_view(), name="platform-integrations-reconciliation-resolve"),
]
