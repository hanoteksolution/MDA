"""SMS provider adapter contract.

An adapter turns one message into one provider call and reports what happened as a
``SendResult``. It must never raise for a provider-side problem — timeouts, 5xx, garbage
bodies are *results* (``TRANSIENT`` / ``PERMANENT``), so the framework can retry or stop
without ever breaking the business transaction that triggered the SMS.
"""

from __future__ import annotations

from dataclasses import dataclass

OK = "OK"
TRANSIENT = "TRANSIENT"  # worth retrying: timeout, network, 5xx, 429
PERMANENT = "PERMANENT"  # will never succeed as configured: 4xx, bad config, rejected


@dataclass
class OutboundSms:
    to: str
    body: str
    sender_id: str = ""


@dataclass
class SendResult:
    outcome: str
    reference: str = ""
    error: str = ""


class SmsProviderAdapter:
    type_code = ""

    def __init__(self, *, config: dict, secret: str | None):
        self.config = config or {}
        self.secret = secret

    def send(self, message: OutboundSms) -> SendResult:  # pragma: no cover - interface
        raise NotImplementedError

    def validate_config(self) -> list[str]:
        """Human-readable configuration problems (empty = fine)."""
        return []
