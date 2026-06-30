"""Optional Claude reasoner for narrative synthesis (numbers stay in tools).

Used only if `anthropic` is installed and ANTHROPIC_API_KEY is set. Safe to ignore
for the deterministic pipeline.
"""
from __future__ import annotations

from typing import Optional

from .config import Settings


class ClaudeReasoner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = None

    def _ensure(self):
        if self._client is not None:
            return self._client
        if not self.settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set.")
        try:
            import anthropic
        except ImportError as e:
            raise ImportError("Install extra: pip install 'dbx-cost-optimizer[llm]'") from e
        self._client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        return self._client

    def summarize(self, report_md: str, max_tokens: int = 1024) -> str:
        client = self._ensure()
        msg = client.messages.create(
            model=self.settings.llm_model,
            max_tokens=max_tokens,
            system=("You are a Databricks FinOps lead. Summarize the cost report into a crisp "
                    "executive brief. Do NOT invent or alter any dollar figure — use only the "
                    "numbers given."),
            messages=[{"role": "user", "content": report_md}],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
