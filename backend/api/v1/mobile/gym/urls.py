from django.urls import path

from api.v1.mobile.gym.views import (
    MemberPortalAttendanceView,
    MemberPortalClassesView,
    MemberPortalHomeView,
    MemberPortalProfileView,
    MemberPortalQrView,
    MemberPortalWorkoutsView,
)

urlpatterns = [
    path("home/", MemberPortalHomeView.as_view(), name="mobile-gym-home"),
    path("profile/", MemberPortalProfileView.as_view(), name="mobile-gym-profile"),
    path("qr/", MemberPortalQrView.as_view(), name="mobile-gym-qr"),
    path("attendance/", MemberPortalAttendanceView.as_view(), name="mobile-gym-attendance"),
    path("workouts/", MemberPortalWorkoutsView.as_view(), name="mobile-gym-workouts"),
    path("classes/", MemberPortalClassesView.as_view(), name="mobile-gym-classes"),
]
