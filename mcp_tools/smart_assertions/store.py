"""Standalone in-memory snapshot store (1-hour TTL, no external dependencies)."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

TTL_SECONDS = 3600


@dataclass
class Snapshot:
    run_id: str
    persona_description: str
    persona: dict[str, Any]
    lob: str
    created_at: float
    stop_after: str

    total_premium: float | None
    total_cost: float | None
    coverage_premiums: dict[str, float]   # {coverage_name: premium} from Policy Term Factor rows
    uw_conditions: list[str]
    blocked: bool
    blocked_reason: str

    raw: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > TTL_SECONDS

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "persona_description": self.persona_description,
            "lob": self.lob,
            "created_at": self.created_at,
            "stop_after": self.stop_after,
            "total_premium": self.total_premium,
            "total_cost": self.total_cost,
            "coverage_premiums": self.coverage_premiums,
            "uw_conditions": self.uw_conditions,
            "blocked": self.blocked,
            "blocked_reason": self.blocked_reason,
            "persona": self.persona,
        }


class SnapshotStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, Snapshot] = {}

    def save(self, snapshot: Snapshot) -> str:
        with self._lock:
            self._evict()
            self._entries[snapshot.run_id] = snapshot
        return snapshot.run_id

    def get(self, run_id: str) -> Snapshot | None:
        with self._lock:
            entry = self._entries.get(run_id)
            if entry and entry.is_expired():
                del self._entries[run_id]
                return None
            return entry

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            self._evict()
            entries = sorted(self._entries.values(), key=lambda e: e.created_at, reverse=True)
        return [e.as_dict() for e in entries[:limit]]

    def _evict(self) -> None:
        expired = [k for k, v in self._entries.items() if v.is_expired()]
        for k in expired:
            del self._entries[k]


# Module-level singleton shared across all tool calls in this process
store = SnapshotStore()
