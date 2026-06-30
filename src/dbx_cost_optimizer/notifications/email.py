"""SMTP email notifier — sends alerts to the recipient list."""
from __future__ import annotations

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from ..config import SmtpConfig
from .base import Notifier


class EmailNotifier(Notifier):
    def __init__(self, cfg: SmtpConfig, recipients: Optional[List[str]] = None,
                 dry_run: bool = False) -> None:
        self.cfg = cfg
        self.recipients = recipients or cfg.recipients
        self.dry_run = dry_run

    def send(self, subject: str, body_text: str, body_html: str = "") -> bool:
        if not self.recipients and not self.dry_run:
            raise ValueError("No alert recipients configured (ALERT_RECIPIENTS).")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.cfg.sender or self.cfg.username or "dbx-cost-optimizer"
        msg["To"] = ", ".join(self.recipients)
        msg.attach(MIMEText(body_text, "plain"))
        if body_html:
            msg.attach(MIMEText(body_html, "html"))

        if self.dry_run:
            print(f"[DRY-RUN] would email {self.recipients or '(no recipients set)'}: {subject}")
            print(body_text)
            return True

        if not self.cfg.is_configured:
            raise ValueError("SMTP not configured (SMTP_HOST / ALERT_FROM / ALERT_RECIPIENTS).")

        context = ssl.create_default_context()
        with smtplib.SMTP(self.cfg.host, self.cfg.port, timeout=30) as server:
            if self.cfg.use_tls:
                server.starttls(context=context)
            if self.cfg.username and self.cfg.password:
                server.login(self.cfg.username, self.cfg.password)
            server.sendmail(msg["From"], self.recipients, msg.as_string())
        return True
