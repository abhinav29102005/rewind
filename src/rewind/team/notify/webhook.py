"""Signed generic webhook channel."""

from __future__ import annotations

import hashlib
import hmac
import html
import json
import logging
import time

import httpx

from ...contracts import ApprovalChannel, NotificationEvent

logger = logging.getLogger(__name__)


def escape_untrusted(text: str, max_chars: int = 500) -> str:
    """Escapes and truncates agent-supplied untrusted text."""
    if not text:
        return ""
    truncated = text[:max_chars] + ("..." if len(text) > max_chars else "")
    return html.escape(truncated)


class WebhookChannel(ApprovalChannel):
    name: str = "webhook"

    def __init__(self, url: str, secret: str, timeout_seconds: float = 5.0) -> None:
        self.url = url
        self.secret = secret.encode("utf-8")
        self.timeout = timeout_seconds

    def notify(self, event: NotificationEvent) -> None:
        # Assert safety: never leak recipient one-time codes in general webhook
        payload_data = event.model_dump(mode="json")
        # Sanitize any untrusted fields
        if "untrusted" in payload_data:
            payload_data["untrusted"] = {
                k: escape_untrusted(v) for k, v in payload_data["untrusted"].items()
            }

        body_str = json.dumps(payload_data, sort_keys=True)
        ts = str(int(time.time()))
        to_sign = f"t={ts}.{body_str}".encode()
        sig = hmac.new(self.secret, to_sign, hashlib.sha256).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Rewind-Timestamp": ts,
            "X-Rewind-Signature": f"sha256={sig}",
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(self.url, content=body_str, headers=headers)
                resp.raise_for_status()
        except Exception as e:
            logger.warning("Failed to deliver webhook notification to %s: %s", self.url, e)
            # Notification failure must not raise or change the decision
