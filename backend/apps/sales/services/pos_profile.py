"""Universal POS profile codes + capability flags (PHASE 13).

One POS engine — profiles toggle floor/pharmacy/gym affordances.
Inferred from enabled modules when not explicitly set on the cashier profile.
"""

from __future__ import annotations

POS_PROFILE_CODES = (
    "RETAIL",
    "SUPERMARKET",
    "PHARMACY",
    "CAFETERIA",
    "RESTAURANT",
    "GYM",
    "HOTEL_SERVICE",
)

POS_CAPABILITIES: dict[str, dict[str, bool]] = {
    "RETAIL": {
        "waiters": True,
        "tables": False,
        "batches": False,
        "modifiers": False,
        "kitchen_ticket": False,
        "membership_skus": False,
        "charge_to_room": False,
    },
    "SUPERMARKET": {
        "waiters": False,
        "tables": False,
        "batches": False,
        "modifiers": False,
        "kitchen_ticket": False,
        "membership_skus": False,
        "charge_to_room": False,
    },
    "PHARMACY": {
        "waiters": False,
        "tables": False,
        "batches": True,
        "expiry": True,
        "rx": True,
        "modifiers": False,
        "kitchen_ticket": False,
        "membership_skus": False,
        "charge_to_room": False,
    },
    "CAFETERIA": {
        "waiters": True,
        "tables": True,
        "batches": False,
        "modifiers": False,
        "kitchen_ticket": False,
        "membership_skus": False,
        "charge_to_room": False,
    },
    "RESTAURANT": {
        "waiters": True,
        "tables": True,
        "batches": False,
        "modifiers": True,
        "kitchen_ticket": True,
        "membership_skus": False,
        "charge_to_room": False,
    },
    "GYM": {
        "waiters": False,
        "tables": False,
        "batches": False,
        "modifiers": False,
        "kitchen_ticket": False,
        "membership_skus": True,
        "charge_to_room": False,
    },
    "HOTEL_SERVICE": {
        "waiters": True,
        "tables": True,
        "batches": False,
        "modifiers": False,
        "kitchen_ticket": False,
        "membership_skus": False,
        "charge_to_room": True,
    },
}


def resolve_pos_profile_code(
    *,
    enabled_modules: set[str] | list[str] | None = None,
    explicit_code: str | None = None,
) -> str:
    """Pick a POS profile code from cashier override or enabled modules."""
    raw = (explicit_code or "").strip().upper()
    if raw in POS_CAPABILITIES:
        return raw
    mods = {str(m).strip().lower() for m in (enabled_modules or []) if m}
    if "hotel" in mods and "restaurant" in mods:
        return "HOTEL_SERVICE"
    if "hotel" in mods and "pos" in mods:
        return "HOTEL_SERVICE"
    if "restaurant" in mods:
        return "RESTAURANT"
    if "pharmacy" in mods:
        return "PHARMACY"
    if "gym" in mods and "pos" in mods and not mods.intersection({"restaurant", "pharmacy"}):
        return "GYM"
    if "futsal" in mods and "pos" in mods:
        return "RETAIL"
    return "RETAIL"


def get_pos_capabilities(
    *,
    enabled_modules: set[str] | list[str] | None = None,
    explicit_code: str | None = None,
) -> dict:
    code = resolve_pos_profile_code(
        enabled_modules=enabled_modules, explicit_code=explicit_code
    )
    caps = dict(POS_CAPABILITIES.get(code) or POS_CAPABILITIES["RETAIL"])
    mods = {str(m).strip().lower() for m in (enabled_modules or []) if m}
    # Hotel module always unlocks charge-to-room even on other profiles
    if "hotel" in mods:
        caps["charge_to_room"] = True
    if "restaurant" in mods:
        caps["tables"] = True
        caps["waiters"] = True
    return {"code": code, "capabilities": caps, "modules": sorted(mods)}
