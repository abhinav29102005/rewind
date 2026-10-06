"""Notification dispatcher: fan-out, deduplication, retry, and audit logging."""

from __future__ import annotations

import logging
import time
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...contracts import ApprovalChannel, NotificationEvent
    from ..store import TeamStore

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Dispatches NotificationEvents to configured channels with deduplication and logging."""

    def __init__(
        self,
        channels: list[ApprovalChannel],
        store: TeamStore | None = None,
        dedupe_window_seconds: int = 300,
    ) -> None:
        self.channels = list(channels)
        self.store = store
        self.dedupe_window_seconds = dedupe_window_seconds
        self._recent_events: dict[str, float] = {}  # key: hash/id -> timestamp

    def add_channel(self, channel: ApprovalChannel) -> None:
        self.channels.append(channel)

    def dispatch(self, event: NotificationEvent) -> None:
        now = time.time()
        dedupe_key = f"{event.type.value}:{event.action_id}:{event.summary}"

        # Clean old entries
        cutoff = now - self.dedupe_window_seconds
        self._recent_events = {k: v for k, v in self._recent_events.items() if v > cutoff}

        if dedupe_key in self._recent_events:
            logger.debug("Deduplicated repeated notification event: %s", dedupe_key)
            return

        self._recent_events[dedupe_key] = now

        for ch in self.channels:
            entry_id = "notif_" + uuid.uuid4().hex[:12]
            try:
                ch.notify(event)
                if self.store:
                    self.store.log_notification(
                        entry_id=entry_id,
                        event_type=event.type.value,
                        channel=ch.name,
                        request_id=event.request_id,
                        status="delivered",
                    )
            except Exception as e:
                logger.error("Channel %s failed to notify: %s", ch.name, e)
                if self.store:
                    self.store.log_notification(
                        entry_id=entry_id,
                        event_type=event.type.value,
                        channel=ch.name,
                        request_id=event.request_id,
                        status="failed",
                        last_error=str(e),
                    )
