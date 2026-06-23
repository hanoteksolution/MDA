from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.futsal.models import Court, CourtBooking, FutsalLedgerEntry, Player, Team


def _parse_dt(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


class FutsalService:
    @staticmethod
    def _branch_filter(qs, branch_id=None):
        if branch_id:
            return qs.filter(branch_id=branch_id)
        return qs

    # Courts
    @staticmethod
    def list_courts(*, branch_id=None, is_active=None):
        qs = Court.active_objects().select_related("branch")
        qs = FutsalService._branch_filter(qs, branch_id)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs.order_by("name")

    @staticmethod
    def create_court(*, data, user=None):
        return Court.objects.create(**data, created_by=user)

    @staticmethod
    def update_court(*, court, data, user=None):
        for key, value in data.items():
            setattr(court, key, value)
        court.updated_by = user
        court.save()
        return court

    # Teams
    @staticmethod
    def list_teams(*, branch_id=None, search=None):
        qs = Team.active_objects().select_related("branch").annotate(player_count=Count("players"))
        qs = FutsalService._branch_filter(qs, branch_id)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(captain_name__icontains=search))
        return qs.order_by("name")

    @staticmethod
    def create_team(*, data, user=None):
        return Team.objects.create(**data, created_by=user)

    @staticmethod
    def update_team(*, team, data, user=None):
        for key, value in data.items():
            setattr(team, key, value)
        team.updated_by = user
        team.save()
        return team

    # Players
    @staticmethod
    def list_players(*, branch_id=None, team_id=None, search=None):
        qs = Player.active_objects().select_related("team", "branch")
        qs = FutsalService._branch_filter(qs, branch_id)
        if team_id:
            qs = qs.filter(team_id=team_id)
        if search:
            qs = qs.filter(Q(full_name__icontains=search) | Q(phone__icontains=search))
        return qs.order_by("full_name")

    @staticmethod
    def create_player(*, data, user=None):
        return Player.objects.create(**data, created_by=user)

    @staticmethod
    def update_player(*, player, data, user=None):
        for key, value in data.items():
            setattr(player, key, value)
        player.updated_by = user
        player.save()
        return player

    # Bookings
    @staticmethod
    def list_bookings(*, branch_id=None, court_id=None, status=None, date_from=None, date_to=None):
        qs = CourtBooking.active_objects().select_related("court", "team", "customer", "branch")
        qs = FutsalService._branch_filter(qs, branch_id)
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
    @transaction.atomic
    def create_booking(*, data, user=None):
        court = Court.active_objects().get(pk=data["court_id"])
        start = _parse_dt(data["start_at"])
        end = _parse_dt(data["end_at"])
        hours = data.get("hours")
        if hours is None and start and end:
            hours = Decimal(str(max((end - start).total_seconds() / 3600, 0)))
        hourly_rate = data.get("hourly_rate", court.hourly_rate)
        booking = CourtBooking(
            court=court,
            branch_id=data.get("branch_id") or court.branch_id,
            team_id=data.get("team_id"),
            customer_id=data.get("customer_id"),
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
            FutsalLedgerEntry.objects.create(
                branch=booking.branch,
                entry_type=FutsalLedgerEntry.TYPE_INCOME,
                category="booking_payment",
                amount=booking.amount_paid,
                entry_date=booking.start_at.date(),
                description=f"Booking payment — {booking}",
                booking=booking,
                created_by=user,
            )
        return booking

    @staticmethod
    @transaction.atomic
    def update_booking(*, booking, data, user=None):
        for key in ("team_id", "customer_id", "title", "status", "notes"):
            if key in data:
                setattr(booking, key, data[key])
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
    def list_ledger(*, branch_id=None, entry_type=None, date_from=None, date_to=None):
        qs = FutsalLedgerEntry.active_objects().select_related("branch", "booking")
        qs = FutsalService._branch_filter(qs, branch_id)
        if entry_type:
            qs = qs.filter(entry_type=entry_type)
        if date_from:
            qs = qs.filter(entry_date__gte=date_from)
        if date_to:
            qs = qs.filter(entry_date__lte=date_to)
        return qs.order_by("-entry_date", "-created_at")

    @staticmethod
    def create_ledger_entry(*, data, user=None):
        return FutsalLedgerEntry.objects.create(**data, created_by=user)

    @staticmethod
    def summary(*, branch_id=None):
        today = timezone.localdate()
        month_start = today.replace(day=1)
        bookings = FutsalService.list_bookings(branch_id=branch_id)
        ledger = FutsalService.list_ledger(branch_id=branch_id)

        today_bookings = bookings.filter(start_at__date=today).exclude(status=CourtBooking.STATUS_CANCELLED)
        month_bookings = bookings.filter(start_at__date__gte=month_start).exclude(
            status=CourtBooking.STATUS_CANCELLED
        )

        income_qs = ledger.filter(entry_type=FutsalLedgerEntry.TYPE_INCOME)
        expense_qs = ledger.filter(entry_type=FutsalLedgerEntry.TYPE_EXPENSE)
        month_income = income_qs.filter(entry_date__gte=month_start).aggregate(total=Sum("amount"))["total"] or 0
        month_expense = expense_qs.filter(entry_date__gte=month_start).aggregate(total=Sum("amount"))["total"] or 0

        return {
            "courts": FutsalService.list_courts(branch_id=branch_id, is_active=True).count(),
            "teams": FutsalService.list_teams(branch_id=branch_id).count(),
            "players": FutsalService.list_players(branch_id=branch_id).count(),
            "bookings_today": today_bookings.count(),
            "hours_today": float(
                today_bookings.aggregate(total=Sum("hours"))["total"] or 0
            ),
            "bookings_month": month_bookings.count(),
            "income_month": float(month_income),
            "expense_month": float(month_expense),
            "profit_month": float(month_income) - float(month_expense),
        }
