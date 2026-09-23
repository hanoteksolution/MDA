import uuid
from decimal import Decimal

from apps.integrations.providers.payment_base import (
    OK,
    PERMANENT,
    TRANSIENT,
    CreateResult,
    ParsedEvent,
    PaymentProviderAdapter,
    RemoteStatus,
    to_decimal,
)


class MockPaymentProvider(PaymentProviderAdapter):
    """Deterministic gateway for development and tests. ``config["mode"]``: ``success`` (default),
    ``timeout``, ``server_error``, ``rejected`` (all on create). ``remote`` plays the provider's
    own books, which tests mutate to simulate a payment completing (or diverging)."""

    type_code = "MOCK"
    remote: dict = {}  # reference -> {"status", "amount"} (process-local)

    def create_payment(self, *, amount, currency, reference) -> CreateResult:
        mode = self.config.get("mode", "success")
        if mode == "timeout":
            return CreateResult(TRANSIENT, error="Provider timed out.")
        if mode == "server_error":
            return CreateResult(TRANSIENT, error="Provider returned HTTP 503.")
        if mode == "rejected":
            return CreateResult(PERMANENT, error="Provider rejected the payment.")
        ref = f"mockpay-{uuid.uuid4().hex[:12]}"
        MockPaymentProvider.remote[ref] = {"status": "pending", "amount": Decimal(amount)}
        return CreateResult(OK, reference=ref)

    def fetch_status(self, reference) -> RemoteStatus:
        if self.config.get("status_mode") == "timeout":
            return RemoteStatus(TRANSIENT, error="Provider timed out.")
        row = MockPaymentProvider.remote.get(reference)
        if row is None:
            return RemoteStatus(PERMANENT, error="Unknown reference.")
        return RemoteStatus(OK, status=row["status"], amount=row["amount"])

    def parse_webhook(self, payload) -> ParsedEvent | None:
        if not isinstance(payload, dict) or not payload.get("event_id") or not payload.get("reference"):
            return None
        kind = {"payment.succeeded": "succeeded", "payment.failed": "failed"}.get(payload.get("type"), "other")
        return ParsedEvent(
            event_id=str(payload["event_id"])[:190], kind=kind, reference=str(payload["reference"]),
            amount=to_decimal(payload.get("amount")),
        )
