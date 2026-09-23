from django.urls import path
from .sis_views import AttendanceRosterView, SisResourceView, SisCapabilitiesView, SisFileView, SisExportView, SisDuplicatesView
from .sis_read_views import SisDashboardView, SisActivityView, SisSchemaView, SisStaffView

from .learning_views import MarksRosterView, ReportPrintView

from .fee_views import FeeSummaryView, BillingReceiptPrintView

urlpatterns=[
    path('finance-summary/',FeeSummaryView.as_view()),
    path('billing-receipts/<uuid:pk>/print/',BillingReceiptPrintView.as_view()),
    path("marks-roster/<uuid:pk>/",MarksRosterView.as_view()),
    path("report-cards/<uuid:pk>/print/",ReportPrintView.as_view()),
    path('capabilities/',SisCapabilitiesView.as_view()),
    path('dashboard/',SisDashboardView.as_view()),
    path('staff/',SisStaffView.as_view()),
    path('attendance-roster/',AttendanceRosterView.as_view()),
    path('duplicates/',SisDuplicatesView.as_view()),
    path('files/',SisFileView.as_view()),
    path('files/<uuid:pk>/',SisFileView.as_view()),
    path('<str:resource>/schema/',SisSchemaView.as_view()),
    path('<str:resource>/export/',SisExportView.as_view()),
    path('<str:resource>/',SisResourceView.as_view()),
    path('<str:resource>/<uuid:pk>/',SisResourceView.as_view()),
    path('<str:resource>/<uuid:pk>/activity/',SisActivityView.as_view()),
    path('<str:resource>/<uuid:pk>/<str:action>/',SisResourceView.as_view()),
]
