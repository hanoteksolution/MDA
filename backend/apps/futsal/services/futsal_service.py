from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.customers.models import Customer
from apps.futsal.models import Court, CourtBooking, FutsalLedgerEntry, Player, Team
from apps.settings_app.models import Branch
from core.tenancy import apply_tenant_scope, resolve_acting_tenant, stamp_tenant_id


class FutsalError(ValueError):
    pass


def _parse_dt(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


class FutsalService:
    @staticmethod
    def _scope(qs, *, user=None, request=None, branch_id=None):
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs

    @staticmethod
    def _require_branch(*, branch_id, user=None, request=None) -> Branch:
        if not branch_id:
            raise FutsalError("branch_id is required.")
        qs = apply_tenant_scope(Branch.active_objects(), user=user, request=request)
        branch = qs.filter(pk=branch_id).first()
        if not branch:
            raise FutsalError("Branch not found for this tenant.")
        return branch

    @staticmethod
    def _tenant_id(*, user=None, request=None, branch=None):
        tenant = resolve_acting_tenant(user=user, request=request)
        if tenant is not None:
            return tenant.pk
        if branch is not None and getattr(branch, "tenant_id", None):
            return branch.tenant_id
        return None

    # Courts
    @staticmethod
    def list_courts(*, branch_id=None, is_active=None, user=None, request=None):
        qs = Court.active_objects().select_related("branch")
        qs = FutsalService._scope(qs, user=user, request=request, branch_id=branch_id)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs.order_by("name")

    @staticmethod
    def get_court(*, pk, user=None, request=None):
        return FutsalService.list_courts(user=user, request=request).get(pk=pk)

    @staticmethod
    def create_court(*, data, user=None, request=None):
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = FutsalService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        payload["branch_id"] = branch.id
        if not payload.get("tenant_id"):
            payload["tenant_id"] = branch.tenant_id
        return Court.objects.create(**payload, created_by=user)

    @staticmethod
    def update_court(*, court, data, user=None, request=None):
        payload = dict(data)
        if "branch_id" in payload:
            branch = FutsalService._require_branch(
                branch_id=payload["branch_id"], user=user, request=request
            )
            payload["branch_id"] = branch.id
            if branch.tenant_id:
                payload["tenant_id"] = branch.tenant_id
        for key, value in payload.items():
            setattr(court, key, value)
        court.updated_by = user
        court.save()
        return court

    # Teams
    @staticmethod
    def list_teams(*, branch_id=None, search=None, user=None, request=None):
        qs = Team.active_objects().select_related("branch").annotate(player_count=Count("players"))
        qs = FutsalService._scope(qs, user=user, request=request, branch_id=branch_id)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(captain_name__icontains=search))
        return qs.order_by("name")

    @staticmethod
    def get_team(*, pk, user=None, request=None):
        return FutsalService.list_teams(user=user, request=request).get(pk=pk)

    @staticmethod
    def create_team(*, data, user=None, request=None):
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = FutsalService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        payload["branch_id"] = branch.id
        if not payload.get("tenant_id"):
            payload["tenant_id"] = branch.tenant_id
        return Team.objects.create(**payload, created_by=user)

    @staticmethod
    def update_team(*, team, data, user=None, request=None):
        payload = dict(data)
        if "branch_id" in payload:
            branch = FutsalService._require_branch(
                branch_id=payload["branch_id"], user=user, request=request
            )
            payload["branch_id"] = branch.id
            if branch.tenant_id:
                payload["tenant_id"] = branch.tenant_id
        for key, value in payload.items():
            setattr(team, key, value)
        team.updated_by = user
        team.save()
        return team

    # Players
    @staticmethod
    def list_players(*, branch_id=None, team_id=None, search=None, user=None, request=None):
        qs = Player.active_objects().select_related("team", "branch")
        qs = FutsalService._scope(qs, user=user, request=request, branch_id=branch_id)
        if team_id:
            qs = qs.filter(team_id=team_id)
        if search:
            qs = qs.filter(Q(full_name__icontains=search) | Q(phone__icontains=search))
        return qs.order_by("full_name")

    @staticmethod
    def get_player(*, pk, user=None, request=None):
        return FutsalService.list_players(user=user, request=request).get(pk=pk)

    @staticmethod
    def create_player(*, data, user=None, request=None):
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = FutsalService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        payload["branch_id"] = branch.id
        if not payload.get("tenant_id"):
            payload["tenant_id"] = branch.tenant_id
        team_id = payload.get("team_id") or None
        if team_id in ("", None):
            payload.pop("team_id", None)
        elif not FutsalService.list_teams(user=user, request=request).filter(pk=team_id).exists():
            raise FutsalError("Team not found for this tenant.")
        return Player.objects.create(**payload, created_by=user)

    @staticmethod
    def update_player(*, player, data, user=None, request=None):
        payload = dict(data)
        if "branch_id" in payload:
            branch = FutsalService._require_branch(
                branch_id=payload["branch_id"], user=user, request=request
            )
            payload["branch_id"] = branch.id
            if branch.tenant_id:
                payload["tenant_id"] = branch.tenant_id
        if "team_id" in payload:
            team_id = payload.get("team_id") or None
            if team_id in ("", None):
                payload["team_id"] = None
            elif not FutsalService.list_teams(user=user, request=request).filter(pk=team_id).exists():
                raise FutsalError("Team not found for this tenant.")
        for key, value in payload.items():
            setattr(player, key, value)
        player.updated_by = user
        player.save()
        return player

    # Bookings
    @staticmethod
    def list_bookings(
        *,
        branch_id=None,
        court_id=None,
        status=None,
        date_from=None,
        date_to=None,
        user=None,
        request=None,
    ):
        qs = CourtBooking.active_objects().select_related("court", "team", "customer", "branch")
        qs = FutsalService._scope(qs, user=user, request=request, branch_id=branch_id)
        if court_id:
            qs = qs.filter(court_id=court_id)
        if status:
            qs = qs.filter(status=status)
        if date_from:
            qs = qs.filter(start_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(start_at__date__lte=date_to)
        return qs.order_by("-start_at")

    @staticmethod
    def get_booking(*, pk, user=None, request=None):
        return FutsalService.list_bookings(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_booking(*, data, user=None, request=None):
        court = FutsalService.get_court(pk=data["court_id"], user=user, request=request)
        start = _parse_dt(data["start_at"])
        end = _parse_dt(data["end_at"])
        hours = data.get("hours")
        if hours is None and start and end:
            hours = Decimal(str(max((end - start).total_seconds() / 3600, 0)))
        hourly_rate = data.get("hourly_rate", court.hourly_rate)
        branch_id = data.get("branch_id") or court.branch_id
        branch = FutsalService._require_branch(
            branch_id=branch_id, user=user, request=request
        )
        team_id = data.get("team_id") or None
        if team_id and not FutsalService.list_teams(user=user, request=request).filter(pk=team_id).exists():
            raise FutsalError("Team not found for this tenant.")
        customer_id = data.get("customer_id") or None
        if customer_id:
            cust_qs = apply_tenant_scope(Customer.active_objects(), user=user, request=request)
            if not cust_qs.filter(pk=customer_id).exists():
                raise FutsalError("Customer not found for this tenant.")

        tenant_id = FutsalService._tenant_id(user=user, request=request, branch=branch)
        booking = CourtBooking(
            court=court,
            branch=branch,
            tenant_id=tenant_id,
            team_id=team_id,
            customer_id=customer_id,
            title=data.get("title", ""),
            start_at=start,
            end_at=end,
            hours=hours or Decimal("1"),
            hourly_rate=hourly_rate,
            amount_paid=Decimal(str(data.get("amount_paid", 0))),
            status=data.get("status", CourtBooking.STATUS_SCHEDULED),
            notes=data.get("notes", ""),
            created_by=user,
        )
        booking.recalc_amount()
        booking.save()
        if booking.amount_paid > 0:
            ledger = FutsalLedgerEntry.objects.create(
                branch=booking.branch,
                tenant_id=tenant_id,
                entry_type=FutsalLedgerEntry.TYPE_INCOME,
                category="booking_payment",
                amount=booking.amount_paid,
                entry_date=booking.start_at.date(),
                description=f"Booking payment — {booking}",
                booking=booking,
                created_by=user,
            )
            from apps.finance.services.posting_service import AccountingPostingService

            AccountingPostingService.post_futsal_ledger(entry=ledger, user=user)
        return booking

    @staticmethod
    @transaction.atomic
    def update_booking(*, booking, data, user=None, request=None):
        for key in ("title", "status", "notes"):
            if key in data:
                setattr(booking, key, data[key])
        if "team_id" in data:
            team_id = data.get("team_id") or None
            if team_id and not FutsalService.list_teams(user=user, request=request).filter(pk=team_id).exists():
                raise FutsalError("Team not found for this tenant.")
            booking.team_id = team_id
        if "customer_id" in data:
            customer_id = data.get("customer_id") or None
            if customer_id:
                cust_qs = apply_tenant_scope(
                    Customer.active_objects(), user=user, request=request
                )
                if not cust_qs.filter(pk=customer_id).exists():
                    raise FutsalError("Customer not found for this tenant.")
            booking.customer_id = customer_id
        if "start_at" in data:
            booking.start_at = _parse_dt(data["start_at"])
        if "end_at" in data:
            booking.end_at = _parse_dt(data["end_at"])
        if "hours" in data:
            booking.hours = Decimal(str(data["hours"]))
        if "hourly_rate" in data:
            booking.hourly_rate = Decimal(str(data["hourly_rate"]))
        if "amount_paid" in data:
            booking.amount_paid = Decimal(str(data["amount_paid"]))
        booking.recalc_amount()
        booking.updated_by = user
        booking.save()
        return booking

    # Ledger
    @staticmethod
    def list_ledger(
        *,
        branch_id=None,
        entry_type=None,
        date_from=None,
        date_to=None,
        user=None,
        request=None,
    ):
        qs = FutsalLedgerEntry.active_objects().select_related("branch", "booking")
        qs = FutsalService._scope(qs, user=user, request=request, branch_id=branch_id)
        if entry_type:
            qs = qs.filter(entry_type=entry_type)
        if date_from:
            qs = qs.filter(entry_date__gte=date_from)
        if date_to:
            qs = qs.filter(entry_date__lte=date_to)
        return qs.order_by("-entry_date", "-created_at")

    @staticmethod
    @transaction.atomic
    def create_ledger_entry(*, data, user=None, request=None):
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        payment_method = payload.pop("payment_method", None) or "cash"
        branch = FutsalService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        payload["branch_id"] = branch.id
        if not payload.get("tenant_id"):
            payload["tenant_id"] = branch.tenant_id
        booking_id = payload.get("booking_id") or None
        if booking_id in ("", None):
            payload.pop("booking_id", None)
        elif not FutsalService.list_bookings(user=user, request=request).filter(pk=booking_id).exists():
            raise FutsalError("Booking not found for this tenant.")
        if not payload.get("entry_date"):
            payload.pop("entry_date", None)
        entry = FutsalLedgerEntry.objects.create(**payload, created_by=user)
        from apps.finance.services.posting_service import AccountingPostingService

        AccountingPostingService.post_futsal_ledger(
            entry=entry,
            user=user,
            payment_method=payment_method,
        )
        return entry

    @staticmethod
    def summary(*, branch_id=None, user=None, request=None):
        today = timezone.localdate()
        month_start = today.replace(day=1)
        bookings = FutsalService.list_bookings(
            branch_id=branch_id, user=user, request=request
        )
        ledger = FutsalService.list_ledger(
            branch_id=branch_id, user=user, request=request
        )

        today_bookings = bookings.filter(start_at__date=today).exclude(
            status=CourtBooking.STATUS_CANCELLED
        )
        month_bookings = bookings.filter(start_at__date__gte=month_start).exclude(
            status=CourtBooking.STATUS_CANCELLED
        )

        income_qs = ledger.filter(entry_type=FutsalLedgerEntry.TYPE_INCOME)
        expense_qs = ledger.filter(entry_type=FutsalLedgerEntry.TYPE_EXPENSE)
        month_income = (
            income_qs.filter(entry_date__gte=month_start).aggregate(total=Sum("amount"))["total"]
            or 0
        )
        month_expense = (
            expense_qs.filter(entry_date__gte=month_start).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        return {
            "courts": FutsalService.list_courts(
                branch_id=branch_id, is_active=True, user=user, request=request
            ).count(),
            "teams": FutsalService.list_teams(
                branch_id=branch_id, user=user, request=request
            ).count(),
            "players": FutsalService.list_players(
                branch_id=branch_id, user=user, request=request
            ).count(),
            "bookings_today": today_bookings.count(),
            "hours_today": float(today_bookings.aggregate(total=Sum("hours"))["total"] or 0),
            "bookings_month": month_bookings.count(),
            "income_month": float(month_income),
            "expense_month": float(month_expense),
            "profit_month": float(month_income) - float(month_expense),
        }
