"""Slack webhook notification channel."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ...contracts import ApprovalChannel, NotificationEvent
from .webhook import escape_untrusted

logger = logging.getLogger(__name__)


class SlackChannel(ApprovalChannel):
    name: str = "slack"

    def __init__(self, webhook_url: str, timeout_seconds: float = 5.0) -> None:
        self.webhook_url = webhook_url
        self.timeout = timeout_seconds

    def notify(self, event: NotificationEvent) -> None:
        blocks: list[dict[str, Any]] = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{event.type.value.upper()}*: {event.summary}\n*Severity*: {event.severity.upper()}",
                },
            }
        ]

        if event.link:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🔗 <{event.link}|View and Decide in Dashboard>",
                },
            })

        if event.untrusted:
            untrusted_text = "\n".join(f"{k}: {escape_untrusted(v)}" for k, v in event.untrusted.items())
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"> ⚠️ *Untrusted Agent Input*\n```{untrusted_text}```",
                },
            })

        payload = {"blocks": blocks}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(self.webhook_url, json=payload)
                resp.raise_for_status()
        except Exception as e:
            logger.warning("Failed to deliver Slack notification: %s", e)
