"""LOB-keyed configuration registry for the API assertion pipeline.

Adding a new LOB requires only a new LobConfig entry in LOB_REGISTRY — the
parser, engine, and runner all look up config by lob string at call time.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LobConfig:
    coverages: tuple[str, ...]
    # Each hint is (trigger_keyword, full_condition_text_to_match_in_uw_rows)
    uw_hints: tuple[tuple[str, str], ...]
    known_actions: tuple[str, ...]
    valid_stages: tuple[str, ...]
    default_stage: str
    # Key in flow_result["stage_ui_data"] that holds UW grid rows
    uw_stage_key: str
    # Dotted path in flow_result for the calculated premium value
    premium_path: str


LOB_REGISTRY: dict[str, LobConfig] = {
    "auto": LobConfig(
        coverages=("bronze", "silver", "gold", "platinum"),
        uw_hints=(
            ("sr-22", "SR-22 / Certificate of Insurance Indicator is checked"),
            ("sr22", "SR-22 / Certificate of Insurance Indicator is checked"),
            ("under 25", "All drivers under 25 years of age"),
            ("young driver", "All drivers under 25 years of age"),
            ("suspended", "driver license status that is revoked or suspended"),
            ("revoked", "driver license status that is revoked or suspended"),
        ),
        known_actions=("Request Issue", "Bind", "Request Approval", "Cancel", "Renew"),
        valid_stages=("rate", "rating-detail", "request-issue", "billing-plan", "verify-billing"),
        default_stage="rate",
        uw_stage_key="rate",
        premium_path="stage_ui_data.rate.field_values.Premium",
    ),
}


def get_lob_config(lob: str) -> LobConfig:
    if lob not in LOB_REGISTRY:
        raise ValueError(
            f"Unsupported LOB: {lob!r}. Supported: {sorted(LOB_REGISTRY)}"
        )
    return LOB_REGISTRY[lob]
