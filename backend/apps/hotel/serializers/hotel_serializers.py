def serialize_room_type(row) -> dict:
    return {
        "id": str(row.id),
        "branch_id": str(row.branch_id),
        "branch_name": row.branch.name if row.branch_id else "",
        "name": row.name,
        "code": row.code or "",
        "base_rate": float(row.base_rate or 0),
        "capacity": row.capacity,
        "description": row.description or "",
        "is_active": row.is_active,
        "sort_order": row.sort_order,
    }


def serialize_room(row) -> dict:
    return {
        "id": str(row.id),
        "branch_id": str(row.branch_id),
        "branch_name": row.branch.name if row.branch_id else "",
        "room_type_id": str(row.room_type_id),
        "room_type_name": row.room_type.name if row.room_type_id else "",
        "code": row.code,
        "floor": row.floor or "",
        "status": row.status,
        "is_active": row.is_active,
        "notes": row.notes or "",
    }


def serialize_guest(row) -> dict:
    return {
        "id": str(row.id),
        "branch_id": str(row.branch_id) if row.branch_id else None,
        "full_name": row.full_name,
        "phone": row.phone or "",
        "email": row.email or "",
        "id_number": row.id_number or "",
        "notes": row.notes or "",
        "is_active": row.is_active,
    }


def serialize_folio_line(row) -> dict:
    return {
        "id": str(row.id),
        "line_type": row.line_type,
        "description": row.description,
        "amount": float(row.amount or 0),
        "quantity": float(row.quantity or 0),
        "posted_at": row.posted_at.isoformat() if row.posted_at else None,
        "notes": row.notes or "",
    }


def serialize_folio(row, *, include_lines=True) -> dict:
    balance = float(row.balance or 0)
    amount_paid = float(getattr(row, "amount_paid", 0) or 0)
    data = {
        "id": str(row.id),
        "reservation_id": str(row.reservation_id),
        "branch_id": str(row.branch_id),
        "status": row.status,
        "balance": balance,
        "amount_paid": amount_paid,
        "outstanding": max(0.0, balance - amount_paid),
        "payment_method": getattr(row, "payment_method", "") or "",
        "settled_at": row.settled_at.isoformat()
        if getattr(row, "settled_at", None)
        else None,
        "opened_at": row.opened_at.isoformat() if row.opened_at else None,
        "closed_at": row.closed_at.isoformat() if row.closed_at else None,
        "notes": row.notes or "",
    }
    if include_lines:
        lines = list(row.lines.filter(deleted_at__isnull=True))
        data["lines"] = [serialize_folio_line(l) for l in lines]
        data["line_count"] = len(lines)
    return data


def serialize_open_folio_for_pos(row) -> dict:
    """Compact in-house folio row for POS charge-to-room picker."""
    reservation = row.reservation
    room = reservation.room if reservation else None
    guest = reservation.guest if reservation else None
    return {
        "folio_id": str(row.id),
        "reservation_id": str(row.reservation_id),
        "reservation_number": reservation.reservation_number if reservation else "",
        "room_code": room.code if room else "",
        "guest_name": guest.full_name if guest else "",
        "balance": float(row.balance or 0),
        "branch_id": str(row.branch_id),
    }


def serialize_reservation(row, *, include_folio=True) -> dict:
    data = {
        "id": str(row.id),
        "reservation_number": row.reservation_number,
        "branch_id": str(row.branch_id),
        "guest_id": str(row.guest_id),
        "guest_name": row.guest.full_name if row.guest_id else "",
        "guest_phone": row.guest.phone if row.guest_id else "",
        "room_type_id": str(row.room_type_id),
        "room_type_name": row.room_type.name if row.room_type_id else "",
        "room_id": str(row.room_id) if row.room_id else None,
        "room_code": row.room.code if row.room_id else None,
        "status": row.status,
        "check_in_date": row.check_in_date.isoformat() if row.check_in_date else None,
        "check_out_date": row.check_out_date.isoformat() if row.check_out_date else None,
        "nights": row.nights,
        "adults": row.adults,
        "children": row.children,
        "rate_amount": float(row.rate_amount or 0),
        "notes": row.notes or "",
        "checked_in_at": row.checked_in_at.isoformat() if row.checked_in_at else None,
        "checked_out_at": row.checked_out_at.isoformat() if row.checked_out_at else None,
    }
    if include_folio:
        folio = getattr(row, "folio", None)
        if folio is None:
            try:
                folio = row.folio
            except Exception:
                folio = None
        data["folio"] = serialize_folio(folio) if folio else None
    return data
