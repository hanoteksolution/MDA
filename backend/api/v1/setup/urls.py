from django.urls import path

from api.v1.setup.views import SetupCompleteView, SetupStatusView

urlpatterns = [
    path("status/", SetupStatusView.as_view(), name="setup-status"),
    path("", SetupCompleteView.as_view(), name="setup-complete"),
]
