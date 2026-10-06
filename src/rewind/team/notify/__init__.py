"""Notification channels and dispatcher."""

from __future__ import annotations

from .discord import DiscordChannel
from .dispatcher import NotificationDispatcher
from .email import EmailChannel
from .slack import SlackChannel
from .webhook import WebhookChannel, escape_untrusted

__all__ = [
    "DiscordChannel",
    "EmailChannel",
    "NotificationDispatcher",
    "SlackChannel",
    "WebhookChannel",
    "escape_untrusted",
]
