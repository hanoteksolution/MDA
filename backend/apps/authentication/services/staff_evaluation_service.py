from django.utils import timezone

from apps.authentication.models import StaffEvaluation, User
from core.services.analytics_service import AnalyticsService


class StaffEvaluationService:
    @staticmethod
    def period_start_for(period: str):
        return AnalyticsService._period_start(period)

    @staticmethod
    def list_for_period(*, branch_id=None, period="month", evaluator=None):
        period_start = StaffEvaluationService.period_start_for(period)
        qs = (
            StaffEvaluation.active_objects()
            .filter(period=period, period_start=period_start)
            .select_related("staff", "evaluator", "branch")
        )
        if branch_id:
            qs = qs.filter(staff__branch_id=branch_id)
        if evaluator is not None:
            qs = qs.filter(evaluator=evaluator)
        return qs

    @staticmethod
    def map_by_staff(*, branch_id=None, period="month", evaluator=None):
        return {
            str(row.staff_id): StaffEvaluationService.serialize(row)
            for row in StaffEvaluationService.list_for_period(
                branch_id=branch_id,
                period=period,
                evaluator=evaluator,
            )
        }

    @staticmethod
    def serialize(row: StaffEvaluation) -> dict:
        return {
            "id": str(row.id),
            "staff_id": str(row.staff_id),
            "rating": row.rating,
            "notes": row.notes,
            "period": row.period,
            "period_start": row.period_start.isoformat(),
            "evaluator_id": str(row.evaluator_id),
            "evaluator_name": row.evaluator.get_full_name() or row.evaluator.username,
            "updated_at": row.updated_at.isoformat(),
        }

    @staticmethod
    def upsert(*, staff_id, evaluator, period, rating, notes=""):
        staff = User.objects.filter(id=staff_id, deleted_at__isnull=True).select_related("branch").first()
        if not staff:
            raise ValueError("Staff member not found.")

        if evaluator.branch_id and staff.branch_id and staff.branch_id != evaluator.branch_id:
            if not (evaluator.is_platform_admin or evaluator.role and evaluator.role.slug in ("super_admin", "admin")):
                raise PermissionError("You can only evaluate staff in your branch.")

        period_start = StaffEvaluationService.period_start_for(period)
        defaults = {
            "branch": staff.branch,
            "rating": rating,
            "notes": (notes or "").strip(),
            "updated_by": evaluator,
        }
        row, created = StaffEvaluation.objects.update_or_create(
            staff=staff,
            evaluator=evaluator,
            period=period,
            period_start=period_start,
            defaults=defaults,
        )
        if created:
            row.created_by = evaluator
            row.save(update_fields=["created_by"])
        return row
