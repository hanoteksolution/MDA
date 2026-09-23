from django.urls import path, include
from .views import ResourceView, SchoolSummaryView, SchoolProfileView, LookupView, ActivityView, CapabilitiesView, ProfileLogoView

urlpatterns = [
    path("sis/", include("api.v1.school.sis_urls")),
    path("profile/logo/", ProfileLogoView.as_view()),
    path("capabilities/", CapabilitiesView.as_view()),
    path("summary/", SchoolSummaryView.as_view(), name="school-summary"),
    path("profile/", SchoolProfileView.as_view(), name="school-profile"),
    path("lookups/<str:kind>/", LookupView.as_view()),
    path("academic-years/", ResourceView.as_view(), {"resource": "academic-years"}, name="school-academic-years"),
    path("academic-years/<uuid:pk>/", ResourceView.as_view(), {"resource": "academic-years"}, name="school-academic-year-detail"),
    path("academic-years/<uuid:pk>/activate/", ResourceView.as_view(), {"resource": "academic-years", "action": "activate"}, name="school-academic-year-activate"),
    path("terms/", ResourceView.as_view(), {"resource": "terms"}, name="school-terms"),
    path("terms/<uuid:pk>/", ResourceView.as_view(), {"resource": "terms"}, name="school-term-detail"),
    path("<str:resource>/", ResourceView.as_view()),
    path("<str:resource>/<uuid:pk>/", ResourceView.as_view()),
    path("<str:resource>/<uuid:pk>/activity/", ActivityView.as_view()),
    path("<str:resource>/<uuid:pk>/<str:action>/", ResourceView.as_view()),
]
