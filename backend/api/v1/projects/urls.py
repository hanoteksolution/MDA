from django.urls import path

from api.v1.projects.boq_views import BoqDetailView, BoqListCreateView, BoqStatusView
from api.v1.projects.budget_views import (
    ProjectBudgetDetailView,
    ProjectBudgetListCreateView,
    ProjectBudgetStatusView,
)
from api.v1.projects.milestone_views import (
    ProjectMilestoneDetailView,
    ProjectMilestoneListCreateView,
    ProjectMilestoneStatusView,
)
from api.v1.projects.task_views import (
    ProjectTaskDetailView,
    ProjectTaskListCreateView,
    ProjectTaskStatusView,
)
from api.v1.projects.wbs_views import WbsDetailView, WbsListCreateView, WbsMoveView
from api.v1.projects.construction_views import (
    BuildingDetailView, BuildingListCreateView, FloorDetailView, FloorListCreateView,
    SiteDetailView, SiteListCreateView, UnitDetailView, UnitListCreateView,
)
from api.v1.projects.workforce_views import (
    AttendanceDetailView, AttendanceListCreateView, WageDetailView, WageListCreateView,
    WageStatusView, WorkerDetailView, WorkerListCreateView, WorkerRatesView,
)
from api.v1.projects.project_operations_views import (
    ProjectInvoiceAccountingPreviewView,
    ProjectInvoicePostAccountingView,
    ProjectOperationDetailView,
    ProjectOperationListCreateView, ProjectOperationStatusView,
)
from apps.project_management.services.project_operations_service import (
    ChangeOrderService, MaterialRequestLineService, MaterialRequestService,
    ProjectEquipmentService, ProjectExpenseService, ProjectInvoiceService,
    ProjectInventoryAllocationService, ProjectIssueService, ProjectRiskService, QualityInspectionService,
    SafetyIncidentService, SiteReportService,
)
from api.v1.projects.mobile_views import (
    MobileAttendanceView, MobileMyTasksView, MobileProjectsView, MobileSafetyIncidentView,
    MobileSiteReportView, MobileSummaryView,
)
from api.v1.projects.views import (
    ProjectDetailView,
    ProjectDuplicateView,
    ProjectListCreateView,
    ProjectRestoreView,
    ProjectStatusView,
    ProjectSummaryView,
)

urlpatterns = [
    path("summary/", ProjectSummaryView.as_view(), name="projects-summary"),
    path("mobile/summary/", MobileSummaryView.as_view(), name="projects-mobile-summary"),
    path("mobile/my-tasks/", MobileMyTasksView.as_view(), name="projects-mobile-my-tasks"),
    path("mobile/projects/", MobileProjectsView.as_view(), name="projects-mobile-projects"),
    path("mobile/attendance/", MobileAttendanceView.as_view(), name="projects-mobile-attendance"),
    path("mobile/site-reports/", MobileSiteReportView.as_view(), name="projects-mobile-site-reports"),
    path("mobile/safety-incidents/", MobileSafetyIncidentView.as_view(), name="projects-mobile-safety-incidents"),
    path("sites/", SiteListCreateView.as_view(), name="project-sites-list"),
    path("sites/<uuid:pk>/", SiteDetailView.as_view(), name="project-sites-detail"),
    path("buildings/", BuildingListCreateView.as_view(), name="project-buildings-list"),
    path("buildings/<uuid:pk>/", BuildingDetailView.as_view(), name="project-buildings-detail"),
    path("floors/", FloorListCreateView.as_view(), name="project-floors-list"),
    path("floors/<uuid:pk>/", FloorDetailView.as_view(), name="project-floors-detail"),
    path("units/", UnitListCreateView.as_view(), name="project-units-list"),
    path("units/<uuid:pk>/", UnitDetailView.as_view(), name="project-units-detail"),
    path("boq/", BoqListCreateView.as_view(), name="project-boq-list"),
    path("boq/<uuid:pk>/", BoqDetailView.as_view(), name="project-boq-detail"),
    path("boq/<uuid:pk>/status/", BoqStatusView.as_view(), name="project-boq-status"),
    path("workers/", WorkerListCreateView.as_view(), name="project-workers-list"),
    path("workers/<uuid:pk>/", WorkerDetailView.as_view(), name="project-workers-detail"),
    path("workers/<uuid:pk>/rates/", WorkerRatesView.as_view(), name="project-workers-rates"),
    path("attendance/", AttendanceListCreateView.as_view(), name="project-attendance-list"),
    path("attendance/<uuid:pk>/", AttendanceDetailView.as_view(), name="project-attendance-detail"),
    path("wages/", WageListCreateView.as_view(), name="project-wages-list"),
    path("wages/<uuid:pk>/", WageDetailView.as_view(), name="project-wages-detail"),
    path("wages/<uuid:pk>/status/", WageStatusView.as_view(), name="project-wages-status"),
    path("budgets/", ProjectBudgetListCreateView.as_view(), name="project-budgets-list"),
    path("budgets/<uuid:pk>/", ProjectBudgetDetailView.as_view(), name="project-budgets-detail"),
    path(
        "budgets/<uuid:pk>/status/",
        ProjectBudgetStatusView.as_view(),
        name="project-budgets-status",
    ),
    path("tasks/", ProjectTaskListCreateView.as_view(), name="project-tasks-list"),
    path("tasks/<uuid:pk>/", ProjectTaskDetailView.as_view(), name="project-tasks-detail"),
    path(
        "tasks/<uuid:pk>/status/",
        ProjectTaskStatusView.as_view(),
        name="project-tasks-status",
    ),
    path("milestones/", ProjectMilestoneListCreateView.as_view(), name="project-milestones-list"),
    path(
        "milestones/<uuid:pk>/",
        ProjectMilestoneDetailView.as_view(),
        name="project-milestones-detail",
    ),
    path(
        "milestones/<uuid:pk>/status/",
        ProjectMilestoneStatusView.as_view(),
        name="project-milestones-status",
    ),
    path("wbs/", WbsListCreateView.as_view(), name="project-wbs-list"),
    path("wbs/<uuid:pk>/", WbsDetailView.as_view(), name="project-wbs-detail"),
    path("wbs/<uuid:pk>/move/", WbsMoveView.as_view(), name="project-wbs-move"),
    path("material-requests/", ProjectOperationListCreateView.as_view(service=MaterialRequestService, permission_prefix="project.materials"), name="material-requests-list"),
    path("material-requests/<uuid:pk>/", ProjectOperationDetailView.as_view(service=MaterialRequestService, permission_prefix="project.materials"), name="material-requests-detail"),
    path("material-requests/<uuid:pk>/status/", ProjectOperationStatusView.as_view(service=MaterialRequestService, permission_prefix="project.materials"), name="material-requests-status"),
    path("material-request-lines/", ProjectOperationListCreateView.as_view(service=MaterialRequestLineService, permission_prefix="project.materials"), name="material-request-lines-list"),
    path("material-request-lines/<uuid:pk>/", ProjectOperationDetailView.as_view(service=MaterialRequestLineService, permission_prefix="project.materials"), name="material-request-lines-detail"),
    path("inventory-allocations/", ProjectOperationListCreateView.as_view(service=ProjectInventoryAllocationService, permission_prefix="project.inventory"), name="inventory-allocations-list"),
    path("inventory-allocations/<uuid:pk>/", ProjectOperationDetailView.as_view(service=ProjectInventoryAllocationService, permission_prefix="project.inventory"), name="inventory-allocations-detail"),
    path("equipment/", ProjectOperationListCreateView.as_view(service=ProjectEquipmentService, permission_prefix="project.equipment"), name="equipment-list"),
    path("equipment/<uuid:pk>/", ProjectOperationDetailView.as_view(service=ProjectEquipmentService, permission_prefix="project.equipment"), name="equipment-detail"),
    path("equipment/<uuid:pk>/status/", ProjectOperationStatusView.as_view(service=ProjectEquipmentService, permission_prefix="project.equipment"), name="equipment-status"),
    path("expenses/", ProjectOperationListCreateView.as_view(service=ProjectExpenseService, permission_prefix="project.expenses"), name="expenses-list"),
    path("expenses/<uuid:pk>/", ProjectOperationDetailView.as_view(service=ProjectExpenseService, permission_prefix="project.expenses"), name="expenses-detail"),
    path("expenses/<uuid:pk>/status/", ProjectOperationStatusView.as_view(service=ProjectExpenseService, permission_prefix="project.expenses"), name="expenses-status"),
    path("change-orders/", ProjectOperationListCreateView.as_view(service=ChangeOrderService, permission_prefix="project.change_orders"), name="change-orders-list"),
    path("change-orders/<uuid:pk>/", ProjectOperationDetailView.as_view(service=ChangeOrderService, permission_prefix="project.change_orders"), name="change-orders-detail"),
    path("change-orders/<uuid:pk>/status/", ProjectOperationStatusView.as_view(service=ChangeOrderService, permission_prefix="project.change_orders"), name="change-orders-status"),
    path("site-reports/", ProjectOperationListCreateView.as_view(service=SiteReportService, permission_prefix="project.site_reports"), name="site-reports-list"),
    path("site-reports/<uuid:pk>/", ProjectOperationDetailView.as_view(service=SiteReportService, permission_prefix="project.site_reports"), name="site-reports-detail"),
    path("site-reports/<uuid:pk>/status/", ProjectOperationStatusView.as_view(service=SiteReportService, permission_prefix="project.site_reports"), name="site-reports-status"),
    path("quality-inspections/", ProjectOperationListCreateView.as_view(service=QualityInspectionService, permission_prefix="project.quality"), name="quality-inspections-list"),
    path("quality-inspections/<uuid:pk>/", ProjectOperationDetailView.as_view(service=QualityInspectionService, permission_prefix="project.quality"), name="quality-inspections-detail"),
    path("quality-inspections/<uuid:pk>/status/", ProjectOperationStatusView.as_view(service=QualityInspectionService, permission_prefix="project.quality"), name="quality-inspections-status"),
    path("safety-incidents/", ProjectOperationListCreateView.as_view(service=SafetyIncidentService, permission_prefix="project.safety"), name="safety-incidents-list"),
    path("safety-incidents/<uuid:pk>/", ProjectOperationDetailView.as_view(service=SafetyIncidentService, permission_prefix="project.safety"), name="safety-incidents-detail"),
    path("safety-incidents/<uuid:pk>/status/", ProjectOperationStatusView.as_view(service=SafetyIncidentService, permission_prefix="project.safety"), name="safety-incidents-status"),
    path("risks/", ProjectOperationListCreateView.as_view(service=ProjectRiskService, permission_prefix="project.risks"), name="risks-list"),
    path("risks/<uuid:pk>/", ProjectOperationDetailView.as_view(service=ProjectRiskService, permission_prefix="project.risks"), name="risks-detail"),
    path("risks/<uuid:pk>/status/", ProjectOperationStatusView.as_view(service=ProjectRiskService, permission_prefix="project.risks"), name="risks-status"),
    path("issues/", ProjectOperationListCreateView.as_view(service=ProjectIssueService, permission_prefix="project.issues"), name="issues-list"),
    path("issues/<uuid:pk>/", ProjectOperationDetailView.as_view(service=ProjectIssueService, permission_prefix="project.issues"), name="issues-detail"),
    path("issues/<uuid:pk>/status/", ProjectOperationStatusView.as_view(service=ProjectIssueService, permission_prefix="project.issues"), name="issues-status"),
    path("invoices/", ProjectOperationListCreateView.as_view(service=ProjectInvoiceService, permission_prefix="project.invoices"), name="invoices-list"),
    path("invoices/<uuid:pk>/accounting-preview/", ProjectInvoiceAccountingPreviewView.as_view(service=ProjectInvoiceService), name="invoices-accounting-preview"),
    path("invoices/<uuid:pk>/post-accounting/", ProjectInvoicePostAccountingView.as_view(service=ProjectInvoiceService), name="invoices-post-accounting"),
    path("invoices/<uuid:pk>/", ProjectOperationDetailView.as_view(service=ProjectInvoiceService, permission_prefix="project.invoices"), name="invoices-detail"),
    path("invoices/<uuid:pk>/status/", ProjectOperationStatusView.as_view(service=ProjectInvoiceService, permission_prefix="project.invoices"), name="invoices-status"),
    path("", ProjectListCreateView.as_view(), name="projects-list"),
    path("<uuid:pk>/", ProjectDetailView.as_view(), name="projects-detail"),
    path("<uuid:pk>/status/", ProjectStatusView.as_view(), name="projects-status"),
    path("<uuid:pk>/restore/", ProjectRestoreView.as_view(), name="projects-restore"),
    path("<uuid:pk>/duplicate/", ProjectDuplicateView.as_view(), name="projects-duplicate"),
]
