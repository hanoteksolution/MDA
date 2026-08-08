"""Gym demo seeder — plans, members, active subscriptions, check-ins."""

from __future__ import annotations

from apps.gym.models import Attendance, Member, MembershipPlan
from apps.gym.services.attendance_service import AttendanceService
from apps.gym.services.member_service import MemberService
from apps.gym.services.subscription_service import PlanService, SubscriptionService
from apps.settings_app.models import Branch
from core.tenancy import tenant_context

DEMO_PLAN_CODES = ("demo_monthly", "demo_daypass")

DEMO_MEMBERS = (
    {"full_name": "Amina Hassan", "phone": "+252610000101", "gender": "female"},
    {"full_name": "Omar Ali", "phone": "+252610000102", "gender": "male"},
    {"full_name": "Sara Mohamed", "phone": "+252610000103", "gender": "female"},
    {"full_name": "Yusuf Ibrahim", "phone": "+252610000104", "gender": "male"},
    {"full_name": "Layla Abdi", "phone": "+252610000105", "gender": "female"},
)


def seed(*, tenant, user=None) -> dict:
    """Create sample gym data for a demo tenant. Idempotent on plan codes."""
    with tenant_context(tenant, enforce=True):
        existing = MembershipPlan.active_objects().filter(
            tenant=tenant, code__in=DEMO_PLAN_CODES
        ).count()
        if existing >= len(DEMO_PLAN_CODES):
            members = Member.active_objects().filter(tenant=tenant).count()
            return {
                "gym": {
                    "seeded": True,
                    "idempotent": True,
                    "plans": existing,
                    "members": members,
                }
            }

        branch = (
            Branch.active_objects()
            .filter(tenant=tenant, is_default=True)
            .first()
            or Branch.active_objects().filter(tenant=tenant).first()
        )

        plans = []
        for spec in (
            {
                "code": "demo_monthly",
                "name": "Demo Monthly",
                "duration_days": 30,
                "price": "45.00",
                "visit_limit": None,
                "sort_order": 10,
            },
            {
                "code": "demo_daypass",
                "name": "Demo Day Pass",
                "duration_days": 1,
                "price": "5.00",
                "visit_limit": 1,
                "sort_order": 20,
            },
        ):
            plan = MembershipPlan.active_objects().filter(
                tenant=tenant, code=spec["code"]
            ).first()
            if plan is None:
                plan = PlanService.create(
                    data={**spec, "tenant": tenant},
                    user=user,
                )
            plans.append(plan)

        monthly = plans[0]
        members_created = []
        for i, row in enumerate(DEMO_MEMBERS):
            data = {
                **row,
                "tenant": tenant,
                "notes": "Demo seed member",
            }
            if branch is not None:
                data["branch_id"] = branch.id
            member = MemberService.create(data=data, user=user)
            SubscriptionService.subscribe(
                member_id=member.id,
                plan_id=monthly.id,
                activate=True,
                payment_reference="DEMO",
                price_paid=str(monthly.price),
                notes="Demo seed subscription",
                user=user,
            )
            members_created.append(member)

        checkins = 0
        # Check in first three; leave first two inside, check out the third
        for idx, member in enumerate(members_created[:3]):
            att = AttendanceService.check_in(
                member_id=member.id,
                branch_id=branch.id if branch else None,
                source="manual",
                notes="Demo seed check-in",
                user=user,
            )
            checkins += 1
            if idx == 2:
                AttendanceService.check_out(
                    attendance_id=att.id,
                    user=user,
                    notes="Demo seed check-out",
                )

        from apps.gym.models import Trainer
        from apps.gym.services.trainer_service import PTSessionService, TrainerService

        trainer = Trainer.active_objects().filter(
            tenant=tenant, code="DEMO-PT"
        ).first()
        if trainer is None:
            trainer = TrainerService.create(
                data={
                    "code": "DEMO-PT",
                    "full_name": "Demo Coach",
                    "hourly_rate": "50.00",
                    "specialty_codes": ["strength"],
                    "tenant": tenant,
                    "branch_id": branch.id if branch else None,
                },
                user=user,
            )
        pt_scheduled = 0
        if members_created:
            from django.utils import timezone

            existing_pt = PTSessionService.list(user=user).filter(
                member_id=members_created[0].id, trainer_id=trainer.id
            ).exists()
            if not existing_pt:
                PTSessionService.schedule(
                    member_id=members_created[0].id,
                    trainer_id=trainer.id,
                    scheduled_at=timezone.now(),
                    duration_minutes=60,
                    notes="Demo seed PT session",
                    user=user,
                )
                pt_scheduled = 1

        return {
            "gym": {
                "seeded": True,
                "plans": len(plans),
                "members": len(members_created),
                "subscriptions": len(members_created),
                "checkins": checkins,
                "open_visits": Attendance.active_objects()
                .filter(tenant=tenant, check_out_at__isnull=True)
                .count(),
                "trainers": 1,
                "pt_sessions": pt_scheduled,
            }
        }
