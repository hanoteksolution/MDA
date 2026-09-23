import uuid

from apps.integrations.providers.base import (
    OK,
    PERMANENT,
    TRANSIENT,
    OutboundSms,
    SendResult,
    SmsProviderAdapter,
)


class MockProvider(SmsProviderAdapter):
    """Deterministic provider for development and tests. ``config["mode"]`` picks the outcome:
    ``success`` (default), ``timeout``, ``server_error``, ``malformed``, ``rejected``."""

    type_code = "MOCK"
    outbox: list = []  # what a real gateway would have received (process-local, for tests)

    def send(self, message: OutboundSms) -> SendResult:
        mode = self.config.get("mode", "success")
        if mode == "timeout":
            return SendResult(TRANSIENT, error="Provider timed out.")
        if mode == "server_error":
            return SendResult(TRANSIENT, error="Provider returned HTTP 503.")
        if mode == "malformed":
            return SendResult(TRANSIENT, error="Provider returned an unreadable response.")
        if mode == "rejected":
            return SendResult(PERMANENT, error="Provider rejected the number.")
        MockProvider.outbox.append(message)
        return SendResult(OK, reference=f"mock-{uuid.uuid4().hex[:12]}")
