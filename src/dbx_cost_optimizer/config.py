"""Configuration loaded from environment / .env.

Single typed settings object passed everywhere. Extend by adding fields here.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # dotenv optional
    pass


def _bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _list(key: str) -> List[str]:
    raw = os.getenv(key, "")
    return [x.strip() for x in raw.split(",") if x.strip()]


@dataclass
class DatabricksConfig:
    server_hostname: Optional[str] = field(default_factory=lambda: os.getenv("DBX_SERVER_HOSTNAME"))
    http_path: Optional[str] = field(default_factory=lambda: os.getenv("DBX_HTTP_PATH"))
    access_token: Optional[str] = field(default_factory=lambda: os.getenv("DBX_ACCESS_TOKEN"))

    @property
    def is_configured(self) -> bool:
        return bool(self.server_hostname and self.http_path and self.access_token)


@dataclass
class SmtpConfig:
    host: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_HOST"))
    port: int = field(default_factory=lambda: _int("SMTP_PORT", 587))
    username: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_USERNAME"))
    password: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_PASSWORD"))
    use_tls: bool = field(default_factory=lambda: _bool("SMTP_USE_TLS", True))
    sender: Optional[str] = field(default_factory=lambda: os.getenv("ALERT_FROM"))
    recipients: List[str] = field(default_factory=lambda: _list("ALERT_RECIPIENTS"))

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.sender and self.recipients)


@dataclass
class AlertThresholds:
    """Each threshold is a USD ceiling; breach -> alert."""

    monthly_spend_usd: float = field(default_factory=lambda: _float("ALERT_MONTHLY_SPEND_USD", 50000))
    single_entity_usd: float = field(default_factory=lambda: _float("ALERT_SINGLE_ENTITY_USD", 5000))
    identified_waste_usd: float = field(default_factory=lambda: _float("ALERT_IDENTIFIED_WASTE_USD", 10000))


@dataclass
class Settings:
    databricks: DatabricksConfig = field(default_factory=DatabricksConfig)
    smtp: SmtpConfig = field(default_factory=SmtpConfig)
    thresholds: AlertThresholds = field(default_factory=AlertThresholds)

    lookback_days: int = field(default_factory=lambda: _int("DBX_LOOKBACK_DAYS", 30))
    util_lookback_days: int = field(default_factory=lambda: _int("DBX_UTIL_LOOKBACK_DAYS", 14))

    llm_model: str = field(default_factory=lambda: os.getenv("DBX_LLM_MODEL", "claude-opus-4-8"))
    anthropic_api_key: Optional[str] = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))

    pdf_output_path: str = field(default_factory=lambda: os.getenv("DBX_PDF_PATH", "dbx_cost_report.pdf"))

    @classmethod
    def load(cls) -> "Settings":
        return cls()
