"""Generic HTTP SMS adapter (D7): no invented vendor APIs, only what the tenant configures.

config = {
  "url": "https://gateway.example/send",          # required; https only, no private hosts
  "method": "POST",
  "body_format": "json" | "form",
  "headers": {"Authorization": "Bearer {secret}"},  # {secret} injected at send time only
  "body": {"to": "{to}", "text": "{message}", "from": "{sender}", "key": "{secret}"},
  "success_statuses": [200, 201, 202],              # default: any 2xx
  "reference_path": "data.id",                      # dotted path into a JSON reply (optional)
  "timeout_seconds": 10
}
"""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

import requests
from django.conf import settings

from apps.integrations.providers.base import (
    OK,
    PERMANENT,
    TRANSIENT,
    OutboundSms,
    SendResult,
    SmsProviderAdapter,
)

_PLACEHOLDER = re.compile(r"\{(\w+)\}")
MAX_TIMEOUT = 30


def _fill(value, ctx):
    if isinstance(value, str):
        return _PLACEHOLDER.sub(lambda m: str(ctx.get(m.group(1), m.group(0))), value)
    if isinstance(value, dict):
        return {k: _fill(v, ctx) for k, v in value.items()}
    if isinstance(value, list):
        return [_fill(v, ctx) for v in value]
    return value


def _blocked_host(host: str) -> bool:
    """SSRF guard: tenant-entered URLs must not reach loopback / private / link-local hosts."""
    if getattr(settings, "SMS_ALLOW_PRIVATE_URLS", False):
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False  # unresolvable: let the request fail as a transient network error
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return True
    return False


class CustomHttpProvider(SmsProviderAdapter):
    type_code = "CUSTOM_HTTP"

    def validate_config(self) -> list[str]:
        problems = []
        parsed = urlparse(str(self.config.get("url") or ""))
        if parsed.scheme != "https" or not parsed.hostname:
            problems.append("url must be an https URL.")
        elif _blocked_host(parsed.hostname):
            problems.append("url points to a private or internal address.")
        if str(self.config.get("method", "POST")).upper() not in ("POST", "GET"):
            problems.append("method must be POST or GET.")
        if not isinstance(self.config.get("body", {}), dict):
            problems.append("body must be an object.")
        return problems

    def send(self, message: OutboundSms) -> SendResult:
        problems = self.validate_config()
        if problems:
            return SendResult(PERMANENT, error=f"Invalid provider configuration: {problems[0]}")
        ctx = {
            "to": message.to,
            "message": message.body,
            "sender": message.sender_id,
            "secret": self.secret or "",
        }
        method = str(self.config.get("method", "POST")).upper()
        headers = _fill(self.config.get("headers") or {}, ctx)
        body = _fill(self.config.get("body") or {}, ctx)
        timeout = min(float(self.config.get("timeout_seconds") or 10), MAX_TIMEOUT)
        kwargs = {"headers": headers, "timeout": timeout, "allow_redirects": False}
        if method == "GET":
            kwargs["params"] = body
        elif self.config.get("body_format", "json") == "form":
            kwargs["data"] = body
        else:
            kwargs["json"] = body
        try:
            resp = requests.request(method, self.config["url"], **kwargs)
        except requests.Timeout:
            return SendResult(TRANSIENT, error="Provider timed out.")
        except requests.RequestException:
            # The exception text can embed the URL/headers (and so the secret): drop it.
            return SendResult(TRANSIENT, error="Could not reach the provider.")

        status = resp.status_code
        ok_statuses = self.config.get("success_statuses")
        ok = status in ok_statuses if ok_statuses else 200 <= status < 300
        if not ok:
            outcome = TRANSIENT if status >= 500 or status in (408, 429) else PERMANENT
            return SendResult(outcome, error=f"Provider returned HTTP {status}.")
        reference = ""
        path = self.config.get("reference_path")
        if path:
            try:
                node = resp.json()
                for part in str(path).split("."):
                    node = node[part]
                reference = str(node)[:190]
            except (ValueError, KeyError, TypeError, IndexError):
                # 2xx but the promised reference is missing: we cannot tell whether it was accepted.
                return SendResult(TRANSIENT, error="Provider returned an unreadable response.")
        return SendResult(OK, reference=reference)
