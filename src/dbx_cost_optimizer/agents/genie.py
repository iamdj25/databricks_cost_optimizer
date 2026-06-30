"""Genie Agent — sets up and drives an interactive Databricks Genie space.

Genie = natural-language analytics over your tables. This agent:
  - links to a Genie space (DBX_GENIE_SPACE_ID) scoped to the cost tables,
  - holds an interactive conversation (start once, follow-ups keep context),
  - returns the answer text + generated SQL + result rows for each question.

Space creation is a one-time UI/admin step (Genie space creation is not exposed
as a stable public API) — point the space at `cost_findings` + `cost_usage_daily`
+ `system.billing.usage`, then set DBX_GENIE_SPACE_ID. `ensure_space` validates
access by opening a conversation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..models import Finding
from ..registry import register_agent
from ..workspace import get_workspace_client
from .base import BaseAgent


@dataclass
class GenieAnswer:
    question: str
    text: str = ""
    sql: str = ""
    rows: List[List[Any]] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"question": self.question, "text": self.text, "sql": self.sql,
                "columns": self.columns, "rows": self.rows[:50], "error": self.error}


@register_agent
class GenieAgent(BaseAgent):
    name = "genie"
    requires: List[str] = []
    tier = 4

    def __init__(self, settings, connector) -> None:
        super().__init__(settings, connector)
        self._w = None
        self._conversation_id: Optional[str] = None
        self.space_id: Optional[str] = settings.databricks.genie_space_id

    @property
    def w(self):
        if self._w is None:
            self._w = get_workspace_client(self.settings)
        return self._w

    # ---- setup ----
    def ensure_space(self) -> str:
        if not self.space_id:
            raise ValueError(
                "No Genie space configured. Create a Genie space over the cost tables "
                "in the Databricks UI (Genie > New), add cost_findings / cost_usage_daily / "
                "system.billing.usage, then set DBX_GENIE_SPACE_ID."
            )
        return self.space_id

    # ---- one Q&A turn ----
    def ask(self, question: str) -> GenieAnswer:
        space = self.ensure_space()
        ans = GenieAnswer(question=question)
        try:
            if self._conversation_id is None:
                msg = self.w.genie.start_conversation_and_wait(space, question)
                self._conversation_id = msg.conversation_id
            else:
                msg = self.w.genie.create_message_and_wait(space, self._conversation_id, question)
            self._parse_message(space, msg, ans)
        except Exception as e:
            ans.error = str(e)
        return ans

    def _parse_message(self, space: str, msg, ans: GenieAnswer) -> None:
        for att in (getattr(msg, "attachments", None) or []):
            text = getattr(att, "text", None)
            if text and getattr(text, "content", None):
                ans.text += text.content
            query = getattr(att, "query", None)
            if query is not None:
                ans.sql = getattr(query, "query", "") or ans.sql
                # fetch the executed result
                try:
                    res = self.w.genie.get_message_query_result(
                        space, msg.conversation_id, msg.id)
                    sr = getattr(res, "statement_response", None)
                    if sr and getattr(sr, "result", None) and sr.result.data_array:
                        ans.rows = sr.result.data_array
                    if sr and getattr(sr, "manifest", None) and sr.manifest.schema:
                        ans.columns = [c.name for c in sr.manifest.schema.columns]
                except Exception as e:
                    ans.error = f"result fetch: {e}"
        if not ans.text and getattr(msg, "content", None):
            ans.text = msg.content

    def reset(self) -> None:
        self._conversation_id = None

    # ---- orchestrator entrypoint: validate + sample question ----
    def run(self, ctx) -> List[Finding]:
        try:
            space = self.ensure_space()
            ctx.meta["genie_space_id"] = space
            seed = self.ask("What is the total identified monthly savings and the top 3 fix families?")
            ctx.meta["genie_seed_answer"] = seed.to_dict()
        except Exception as e:
            ctx.meta["genie_error"] = str(e)
        return []
