"""Premium extraction from OneShield replay results."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PremiumEvidence:
    value: float | None
    source: str
    ui_value: float | None
    rating_detail_value: float | None
    mismatch: bool


def extract_premium_evidence(flow_result: dict[str, Any]) -> PremiumEvidence:
    """Use the Premium Summary UI value as the premium source of truth."""
    ui_value, ui_source = _ui_summary_premium(flow_result)
    rating_detail_value = _rating_detail_total(flow_result)
    mismatch = (
        ui_value is not None
        and rating_detail_value is not None
        and abs(ui_value - rating_detail_value) > 0.01
    )

    if ui_value is not None:
        return PremiumEvidence(
            value=ui_value,
            source=ui_source,
            ui_value=ui_value,
            rating_detail_value=rating_detail_value,
            mismatch=mismatch,
        )

    return PremiumEvidence(
        value=None,
        source="unavailable",
        ui_value=None,
        rating_detail_value=rating_detail_value,
        mismatch=False,
    )


def _ui_summary_premium(flow_result: dict[str, Any]) -> tuple[float | None, str]:
    stage_ui_data = flow_result.get("stage_ui_data", {})
    for stage in ("rate", "rating-detail", "request-issue"):
        value = _premium_from_field_values(
            stage_ui_data.get(stage, {}).get("field_values", {})
        )
        if value is not None:
            return value, f"stage_ui_data.{stage}.field_values.Premium"

    value = _premium_from_field_values(
        flow_result.get("ui_data", {}).get("field_values", {})
    )
    if value is not None:
        return value, "ui_data.field_values.Premium"

    summary = flow_result.get("rating_factors", {}).get("summary_premium")
    value = parse_money(summary)
    if value is not None:
        return value, "rating_factors.summary_premium"

    value = parse_money(flow_result.get("premium"))
    if value is not None:
        return value, "premium"

    return None, "unavailable"


def _premium_from_field_values(field_values: dict[str, Any]) -> float | None:
    normalized = {
        re.sub(r"\s+", " ", str(label).strip().lower()): values
        for label, values in field_values.items()
    }
    for label in ("premium", "total policy premium"):
        values = normalized.get(label, [])
        if not isinstance(values, list):
            values = [values]
        for raw in values:
            value = parse_money(raw)
            if value is not None:
                return value
    return None


def _rating_detail_total(flow_result: dict[str, Any]) -> float | None:
    raw = (
        flow_result.get("rating_factors", {})
        .get("business_values", {})
        .get("calculated_total_premium")
    )
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def parse_money(raw: Any) -> float | None:
    digits = re.sub(r"[^\d.]", "", str(raw or ""))
    if not digits:
        return None
    try:
        return float(digits)
    except ValueError:
        return None
