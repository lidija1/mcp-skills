"""
Temporary in-memory snapshot cache for replay results.

Every successful replay run can be stored here under a UUID key.
Entries expire after TTL_SECONDS (default 1 hour). The store is
process-local (no Redis / DB) — sufficient for dashboard single-server use.

Usage:
    run_id = snapshot_store.save(persona, flow_result)
    entry  = snapshot_store.get(run_id)   # None if expired / missing
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

TTL_SECONDS = 3600  # 1 hour


@dataclass
class SnapshotEntry:
    run_id: str
    persona: dict[str, Any]
    flow_result: dict[str, Any]
    lob: str
    persona_desc: str
    created_at: float = field(default_factory=time.time)

    # Derived convenience fields (extracted at save time so callers don't
    # need to know the flow_result schema).
    premium: float | None = None
    uw_conditions: list[str] = field(default_factory=list)
    coverage: str | None = None
    blocked: bool = False
    blocked_reason: str = ""

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > TTL_SECONDS

    def as_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "lob": self.lob,
            "persona_desc": self.persona_desc,
            "created_at": self.created_at,
            "premium": self.premium,
            "uw_conditions": self.uw_conditions,
            "coverage": self.coverage,
            "blocked": self.blocked,
            "blocked_reason": self.blocked_reason,
            "persona": self.persona,
        }


def _extract_premium(flow_result: dict) -> float | None:
    raw = (
        flow_result.get("rating_factors", {})
        .get("business_values", {})
        .get("calculated_total_premium")
    )
    if raw is not None:
        try:
            return float(raw)
        except (TypeError, ValueError):
            pass
    # Fallback: summary_premium string
    summary = (
        flow_result.get("rating_factors", {}).get("summary_premium")
        or flow_result.get("premium", "")
    )
    import re
    digits = re.sub(r"[^\d.]", "", str(summary or ""))
    if digits:
        try:
            return float(digits)
        except ValueError:
            pass
    return None


def _extract_uw_conditions(flow_result: dict) -> list[str]:
    rows: list[str] = []
    for stage_data in flow_result.get("stage_ui_data", {}).values():
        for grid in stage_data.get("grids", []):
            for row in grid.get("rows", []):
                text = " | ".join(str(v) for v in row.values())
                if "Underwriting" in text and text not in rows:
                    rows.append(text)
    return rows


class _SnapshotStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, SnapshotEntry] = {}

    def save(
        self,
        persona: dict,
        flow_result: dict,
        lob: str = "auto",
        persona_desc: str = "",
    ) -> str:
        run_id = str(uuid.uuid4())
        entry = SnapshotEntry(
            run_id=run_id,
            persona=persona,
            flow_result=flow_result,
            lob=lob,
            persona_desc=persona_desc,
            premium=_extract_premium(flow_result),
            uw_conditions=_extract_uw_conditions(flow_result),
            coverage=persona.get("PolicyCoverage") or persona.get("PolicyCoverageOption"),
            blocked=bool(flow_result.get("blocked_reason")),
            blocked_reason=flow_result.get("blocked_reason", ""),
        )
        with self._lock:
            self._entries[run_id] = entry
            self._evict_expired()
        return run_id

    def get(self, run_id: str) -> SnapshotEntry | None:
        with self._lock:
            entry = self._entries.get(run_id)
            if entry and entry.is_expired():
                del self._entries[run_id]
                return None
            return entry

    def list_recent(self, limit: int = 20) -> list[dict]:
        with self._lock:
            self._evict_expired()
            entries = sorted(self._entries.values(), key=lambda e: e.created_at, reverse=True)
        return [e.as_dict() for e in entries[:limit]]

    def _evict_expired(self) -> None:
        expired = [rid for rid, e in self._entries.items() if e.is_expired()]
        for rid in expired:
            del self._entries[rid]


# Module-level singleton
snapshot_store = _SnapshotStore()
