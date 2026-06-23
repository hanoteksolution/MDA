from apps.futsal.models import Court, CourtBooking, FutsalLedgerEntry, Player, Team


def serialize_court(c: Court) -> dict:
    return {
        "id": str(c.id),
        "name": c.name,
        "code": c.code,
        "branch_id": str(c.branch_id),
        "branch_name": c.branch.name if c.branch_id else "",
        "hourly_rate": float(c.hourly_rate),
        "is_active": c.is_active,
        "notes": c.notes,
    }


def serialize_team(t: Team) -> dict:
    return {
        "id": str(t.id),
        "name": t.name,
        "branch_id": str(t.branch_id),
        "captain_name": t.captain_name,
        "contact_phone": t.contact_phone,
        "player_count": getattr(t, "player_count", t.players.filter(deleted_at__isnull=True).count()),
        "is_active": t.is_active,
        "notes": t.notes,
    }


def serialize_player(p: Player) -> dict:
    return {
        "id": str(p.id),
        "full_name": p.full_name,
        "team_id": str(p.team_id) if p.team_id else None,
        "team_name": p.team.name if p.team_id else "",
        "branch_id": str(p.branch_id),
        "phone": p.phone,
        "jersey_number": p.jersey_number,
        "is_active": p.is_active,
        "notes": p.notes,
    }


def serialize_booking(b: CourtBooking) -> dict:
    return {
        "id": str(b.id),
        "court_id": str(b.court_id),
        "court_name": b.court.name,
        "branch_id": str(b.branch_id),
        "team_id": str(b.team_id) if b.team_id else None,
        "team_name": b.team.name if b.team_id else "",
        "customer_id": str(b.customer_id) if b.customer_id else None,
        "customer_name": b.customer.full_name if b.customer_id else "",
        "title": b.title,
        "start_at": b.start_at.isoformat(),
        "end_at": b.end_at.isoformat(),
        "hours": float(b.hours),
        "hourly_rate": float(b.hourly_rate),
        "amount": float(b.amount),
        "amount_paid": float(b.amount_paid),
        "status": b.status,
        "notes": b.notes,
    }


def serialize_ledger(e: FutsalLedgerEntry) -> dict:
    return {
        "id": str(e.id),
        "branch_id": str(e.branch_id),
        "entry_type": e.entry_type,
        "category": e.category,
        "amount": float(e.amount),
        "entry_date": e.entry_date.isoformat(),
        "description": e.description,
        "booking_id": str(e.booking_id) if e.booking_id else None,
    }
