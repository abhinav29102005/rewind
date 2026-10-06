"""Discord webhook notification channel."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ...contracts import ApprovalChannel, NotificationEvent
from .webhook import escape_untrusted

logger = logging.getLogger(__name__)


class DiscordChannel(ApprovalChannel):
    name: str = "discord"

    def __init__(self, webhook_url: str, timeout_seconds: float = 5.0) -> None:
        self.webhook_url = webhook_url
        self.timeout = timeout_seconds

    def notify(self, event: NotificationEvent) -> None:
        color = 0xED4245 if event.severity == "critical" else (0xFEE75C if event.severity == "warning" else 0x5865F2)
        embed: dict[str, Any] = {
            "title": f"Rewind: {event.type.value}",
            "description": event.summary,
            "color": color,
            "fields": [],
        }

        if event.link:
            embed["fields"].append({"name": "Dashboard Link", "value": event.link, "inline": False})

        if event.untrusted:
            untrusted_text = "\n".join(f"{k}: {escape_untrusted(v)}" for k, v in event.untrusted.items())
            embed["fields"].append({"name": "Untrusted Agent Input", "value": f"```\n{untrusted_text}\n```", "inline": False})

        payload = {"embeds": [embed]}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(self.webhook_url, json=payload)
                resp.raise_for_status()
        except Exception as e:
            logger.warning("Failed to deliver Discord notification: %s", e)
