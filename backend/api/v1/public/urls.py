from django.urls import path

from .views import (
    BusinessPresetsView,
    BusinessTypesView,
    CatalogView,
    ModulesView,
    PlansView,
    RegistrationStatusView,
    RegistrationView,
    SubdomainCheckView,
    VerifyEmailView,
)

urlpatterns = [
    path("catalog/", CatalogView.as_view(), name="public-catalog"),
    path("business-types/", BusinessTypesView.as_view(), name="public-business-types"),
    path("business-presets/", BusinessPresetsView.as_view(), name="public-business-presets"),
    path("modules/", ModulesView.as_view(), name="public-modules"),
    path("plans/", PlansView.as_view(), name="public-plans"),
    path("subdomains/check/", SubdomainCheckView.as_view(), name="public-subdomain-check"),
    path(
        "workspaces/subdomain-availability/",
        SubdomainCheckView.as_view(),
        name="public-workspace-subdomain-availability",
    ),
    path("registrations/", RegistrationView.as_view(), name="public-registration"),
    path("registrations/<uuid:registration_id>/status/", RegistrationStatusView.as_view(), name="public-registration-status"),
    path("email/verify/", VerifyEmailView.as_view(), name="public-email-verify"),
]
