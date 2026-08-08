from django.urls import include, path

from api.v1.mobile.views import MobileBootstrapView, MobileMetaView

urlpatterns = [
    path("meta/", MobileMetaView.as_view(), name="mobile-meta"),
    path("bootstrap/", MobileBootstrapView.as_view(), name="mobile-bootstrap"),
    path("gym/", include("api.v1.mobile.gym.urls")),
]
