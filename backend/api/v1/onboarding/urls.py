from django.urls import path

from api.v1.onboarding.views import (
    OnboardingCatalogView,
    OnboardingProvisionView,
    OnboardingSlugCheckView,
)

urlpatterns = [
    path("catalog/", OnboardingCatalogView.as_view(), name="onboarding-catalog"),
    path("slug-check/", OnboardingSlugCheckView.as_view(), name="onboarding-slug-check"),
    path("provision/", OnboardingProvisionView.as_view(), name="onboarding-provision"),
]
