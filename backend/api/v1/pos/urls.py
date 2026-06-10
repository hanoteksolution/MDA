from django.urls import path

from api.v1.pos.views import PosCheckoutView, PosProfileView

urlpatterns = [
    path("checkout/", PosCheckoutView.as_view(), name="pos-checkout"),
    path("profile/", PosProfileView.as_view(), name="pos-profile"),
]
