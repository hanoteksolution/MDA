from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.project_management.serializers import serialize_attendance
from apps.project_management.serializers.project_operations_serializers import serialize_project_operation
from apps.project_management.services.project_operations_service import (
    ProjectOperationError, SafetyIncidentService, SiteReportService,
)
from apps.project_management.services.project_service import ProjectService
from apps.project_management.services.task_service import ProjectTaskService
from apps.project_management.services.workforce_service import WorkforceError, WorkforceService
from core.responses.api_response import error_response, success_response
from permissions.base import HasPermission, user_has_any


class MobileSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("projects.view")]

    def get(self, request):
        projects = ProjectService.list_projects(user=request.user, request=request)
        tasks = ProjectTaskService.list_tasks(user=request.user, request=request).filter(assignee=request.user)
        return success_response(data={
            "active_projects": projects.filter(status="active").count(),
            "my_open_tasks": tasks.exclude(status="done").count(),
            "today": timezone.localdate().isoformat(),
        })


class MobileMyTasksView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.tasks.view")]

    def get(self, request):
        rows = ProjectTaskService.list_tasks(user=request.user, request=request).filter(assignee=request.user).exclude(status="done")
        return success_response(data=[{
            "id": str(row.id), "project_id": str(row.project_id), "title": row.title,
            "status": row.status, "priority": row.priority, "planned_end": row.planned_end.isoformat() if row.planned_end else None,
        } for row in rows[:100]])


class MobileProjectsView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("projects.view")]

    def get(self, request):
        rows = ProjectService.list_projects(user=request.user, request=request).filter(is_archived=False)
        return success_response(data=[{
            "id": str(row.id), "project_code": row.project_code, "name": row.name,
            "status": row.status, "progress_percent": float(row.progress_percent),
        } for row in rows[:100]])


class MobileAttendanceView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("project.workers.create")]

    def post(self, request):
        try:
            row = WorkforceService.create_attendance(data=request.data, user=request.user, request=request)
        except (WorkforceError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_attendance(row), message="Attendance recorded.", status=status.HTTP_201_CREATED)


class _MobileOperationView(APIView):
    service = None
    permission = ""

    def post(self, request):
        if not user_has_any(request.user, self.permission):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            row = self.service.create(data=request.data, user=request.user, request=request)
        except (ProjectOperationError, ObjectDoesNotExist) as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=serialize_project_operation(row), message="Submitted.", status=status.HTTP_201_CREATED)


class MobileSiteReportView(_MobileOperationView):
    permission_classes = [IsAuthenticated, HasPermission("project.site_reports.create")]
    service = SiteReportService
    permission = "project.site_reports.create"


class MobileSafetyIncidentView(_MobileOperationView):
    permission_classes = [IsAuthenticated, HasPermission("project.safety.create")]
    service = SafetyIncidentService
    permission = "project.safety.create"
