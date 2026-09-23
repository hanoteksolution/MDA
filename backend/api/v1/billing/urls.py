from django.urls import path

from api.v1.billing.views import SubscriptionCheckoutView, SubscriptionOverviewView, SubscriptionPaymentDetailView

urlpatterns = [
    path("subscription/", SubscriptionOverviewView.as_view(), name="billing-subscription"),
    path("subscription/checkout/", SubscriptionCheckoutView.as_view(), name="billing-subscription-checkout"),
    path("subscription/payments/<uuid:pk>/", SubscriptionPaymentDetailView.as_view(), name="billing-subscription-payment"),
]
