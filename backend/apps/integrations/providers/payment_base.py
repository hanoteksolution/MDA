"""Payment provider adapter contract.

Like the SMS adapters, an adapter never raises for a provider-side problem: it returns a
result the framework can act on. Webhook authenticity is **not** the adapter's business by
default — the framework verifies an HMAC over ``"<timestamp>.<raw body>"`` (see
``verify_signature``) so every provider gets the same replay protection.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

OK = "OK"
TRANSIENT = "TRANSIENT"
PERMANENT = "PERMANENT"

SIGNATURE_HEADER = "X-Payment-Signature"
TIMESTAMP_HEADER = "X-Payment-Timestamp"
TOLERANCE_SECONDS = 300  # both directions: rejects stale (replayed) and far-future timestamps


@dataclass
class CreateResult:
    outcome: str
    reference: str = ""
    error: str = ""


@dataclass
class RemoteStatus:
    outcome: str  # OK | TRANSIENT | PERMANENT
    status: str = ""  # pending | succeeded | failed
    amount: Decimal | None = None
    error: str = ""


@dataclass
class ParsedEvent:
    event_id: str
    kind: str  # succeeded | failed | other
    reference: str
    amount: Decimal | None = None


def sign(secret: str, timestamp: str, raw_body: bytes) -> str:
    return hmac.new(secret.encode(), timestamp.encode() + b"." + raw_body, hashlib.sha256).hexdigest()


def verify_signature(*, secret: str | None, timestamp: str, signature: str, raw_body: bytes,
                     now: float) -> str:
    """Return ``""`` when the webhook is authentic and fresh, else a short reason."""
    if not secret:
        return "No webhook secret is configured for this provider."
    if not signature or not timestamp:
        return "Missing signature or timestamp."
    try:
        age = abs(now - int(timestamp))
    except (TypeError, ValueError):
        return "Malformed timestamp."
    if age > TOLERANCE_SECONDS:
        return "Timestamp outside the accepted window (possible replay)."
    if not hmac.compare_digest(sign(secret, timestamp, raw_body), signature.strip().lower()):
        return "Signature does not match."
    return ""


def to_decimal(value) -> Decimal | None:
    try:
        return Decimal(str(value)) if value is not None else None
    except (InvalidOperation, ValueError):
        return None


class PaymentProviderAdapter:
    type_code = ""

    def __init__(self, *, config: dict, secret: str | None):
        self.config = config or {}
        self.secret = secret

    def create_payment(self, *, amount: Decimal, currency: str, reference: str) -> CreateResult:  # pragma: no cover
        raise NotImplementedError

    def fetch_status(self, reference: str) -> RemoteStatus:  # pragma: no cover
        raise NotImplementedError

    def parse_webhook(self, payload: dict) -> ParsedEvent | None:  # pragma: no cover
        """``None`` when the body is not a recognisable event."""
        raise NotImplementedError

    def validate_config(self) -> list[str]:
        return []
