"""Email notification channel via SMTP."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ...contracts import ApprovalChannel, NotificationEvent
from .webhook import escape_untrusted

logger = logging.getLogger(__name__)


class EmailChannel(ApprovalChannel):
    name: str = "email"

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        from_addr: str,
        to_addrs: list[str],
        username: str | None = None,
        password: str | None = None,
        starttls: bool = True,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.username = username
        self.password = password
        self.starttls = starttls

    def notify(self, event: NotificationEvent) -> None:
        msg = MIMEMultipart()
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(self.to_addrs)
        msg["Subject"] = f"[Rewind] {event.type.value.upper()}: {event.summary}"

        body_parts = [
            f"Event: {event.type.value}",
            f"Severity: {event.severity}",
            f"Summary: {event.summary}",
        ]
        if event.link:
            body_parts.append(f"Dashboard Link: {event.link}")
        if event.untrusted:
            body_parts.append("\n--- Untrusted Agent Input ---")
            for k, v in event.untrusted.items():
                body_parts.append(f"{k}: {escape_untrusted(v)}")

        msg.attach(MIMEText("\n".join(body_parts), "plain"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10.0) as server:
                if self.starttls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
        except Exception as e:
            logger.warning("Failed to send email notification: %s", e)
