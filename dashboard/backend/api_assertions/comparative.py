"""
Comparative assertion runner.

Runs two persona descriptions through replay in parallel, then
evaluates relational assertions between them — e.g.:
  - premium_a_gt_b   : A's premium is higher than B's
  - premium_a_lt_b   : A's premium is lower than B's
  - uw_fires_for_a   : A triggers a UW referral
  - uw_absent_for_a  : A does NOT trigger a UW referral
  - uw_fires_for_b   : B triggers a UW referral
  - uw_absent_for_b  : B does NOT trigger a UW referral
  - both_blocked     : both flows are blocked
  - neither_blocked  : neither flow is blocked
  - a_blocked        : only A is blocked
  - b_blocked        : only B is blocked

Usage:
    from dashboard.backend.api_assertions.comparative import run_comparative
    result = run_comparative("young SR-22 driver", "clean 35-year-old", ["premium_a_gt_b", "uw_fires_for_a"])
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from api_tests.oneshield_api_replay import OneShieldApiReplay
from dashboard.backend.api_assertions.snapshot import snapshot_store, _extract_premium, _extract_uw_conditions
from mcp_tools.policy_flow_generator.persona_generator import generate_persona

SUPPORTED_RELATIONS = [
    "premium_a_gt_b",
    "premium_a_lt_b",
    "premium_a_approx_b",
    "uw_fires_for_a",
    "uw_absent_for_a",
    "uw_fires_for_b",
    "uw_absent_for_b",
    "both_blocked",
    "neither_blocked",
    "a_blocked",
    "b_blocked",
]


@dataclass
class ComparativeFinding:
    relation: str
    passed: bool
    label_a: str
    label_b: str
    value_a: Any
    value_b: Any
    message: str = ""


@dataclass
class ComparativeResult:
    label_a: str
    label_b: str
    run_id_a: str
    run_id_b: str
    persona_a: dict
    persona_b: dict
    premium_a: float | None
    premium_b: float | None
    uw_conditions_a: list[str]
    uw_conditions_b: list[str]
    blocked_a: bool
    blocked_b: bool
    findings: list[ComparativeFinding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return bool(self.findings) and all(f.passed for f in self.findings)


def _run_one(lob: str, description: str) -> tuple[dict, dict]:
    """Generate persona and run replay. Returns (persona, flow_result)."""
    persona_raw = generate_persona(lob, description)
    persona = json.loads(persona_raw)
    if "error" in persona:
        raise ValueError(f"Persona generation failed: {persona['error']}")

    client = OneShieldApiReplay()
    try:
        flow_result = client.run_captured_auto_flow(
            persona,
            stop_after="rating-detail",
            fast_mode=True,
        )
    finally:
        client.close()
    return persona, flow_result


def _uw_fired(uw_conditions: list[str]) -> bool:
    return bool(uw_conditions)


def _evaluate_relation(
    relation: str,
    premium_a: float | None,
    premium_b: float | None,
    uw_a: list[str],
    uw_b: list[str],
    blocked_a: bool,
    blocked_b: bool,
    label_a: str,
    label_b: str,
) -> ComparativeFinding:
    def finding(passed: bool, val_a: Any, val_b: Any, msg: str = "") -> ComparativeFinding:
        return ComparativeFinding(
            relation=relation,
            passed=passed,
            label_a=label_a,
            label_b=label_b,
            value_a=val_a,
            value_b=val_b,
            message=msg,
        )

    if relation == "premium_a_gt_b":
        if premium_a is None or premium_b is None:
            return finding(False, premium_a, premium_b, "Premium not available for comparison.")
        passed = premium_a > premium_b
        msg = "" if passed else f"A (${premium_a:,.2f}) is not greater than B (${premium_b:,.2f})"
        return finding(passed, premium_a, premium_b, msg)

    if relation == "premium_a_lt_b":
        if premium_a is None or premium_b is None:
            return finding(False, premium_a, premium_b, "Premium not available for comparison.")
        passed = premium_a < premium_b
        msg = "" if passed else f"A (${premium_a:,.2f}) is not less than B (${premium_b:,.2f})"
        return finding(passed, premium_a, premium_b, msg)

    if relation == "premium_a_approx_b":
        if premium_a is None or premium_b is None:
            return finding(False, premium_a, premium_b, "Premium not available for comparison.")
        if premium_b == 0:
            return finding(False, premium_a, premium_b, "B premium is zero.")
        pct_diff = abs(premium_a - premium_b) / premium_b
        passed = pct_diff <= 0.10
        msg = f"±{pct_diff*100:.1f}% difference (threshold 10%)"
        return finding(passed, premium_a, premium_b, msg)

    if relation == "uw_fires_for_a":
        passed = _uw_fired(uw_a)
        return finding(passed, bool(uw_a), None, "" if passed else "No UW conditions found for A.")

    if relation == "uw_absent_for_a":
        passed = not _uw_fired(uw_a)
        return finding(passed, bool(uw_a), None, "" if passed else f"UW conditions found for A: {uw_a[:2]}")

    if relation == "uw_fires_for_b":
        passed = _uw_fired(uw_b)
        return finding(passed, None, bool(uw_b), "" if passed else "No UW conditions found for B.")

    if relation == "uw_absent_for_b":
        passed = not _uw_fired(uw_b)
        return finding(passed, None, bool(uw_b), "" if passed else f"UW conditions found for B: {uw_b[:2]}")

    if relation == "both_blocked":
        passed = blocked_a and blocked_b
        return finding(passed, blocked_a, blocked_b, "" if passed else f"A blocked={blocked_a}, B blocked={blocked_b}")

    if relation == "neither_blocked":
        passed = not blocked_a and not blocked_b
        return finding(passed, blocked_a, blocked_b, "" if passed else f"A blocked={blocked_a}, B blocked={blocked_b}")

    if relation == "a_blocked":
        passed = blocked_a and not blocked_b
        return finding(passed, blocked_a, blocked_b, "" if passed else f"A blocked={blocked_a}, B blocked={blocked_b}")

    if relation == "b_blocked":
        passed = blocked_b and not blocked_a
        return finding(passed, blocked_a, blocked_b, "" if passed else f"A blocked={blocked_a}, B blocked={blocked_b}")

    return ComparativeFinding(
        relation=relation, passed=False,
        label_a=label_a, label_b=label_b,
        value_a=None, value_b=None,
        message=f"Unknown relation: {relation}",
    )


def run_comparative(
    description_a: str,
    description_b: str,
    relations: list[str],
    lob: str = "auto",
    label_a: str = "",
    label_b: str = "",
) -> ComparativeResult:
    """
    Run two personas in parallel, then evaluate the given relational assertions.

    Args:
        description_a: NL persona description for scenario A
        description_b: NL persona description for scenario B
        relations: list of relation strings from SUPPORTED_RELATIONS
        lob: line of business (default "auto")
        label_a: display label for A (auto-derived if empty)
        label_b: display label for B (auto-derived if empty)

    Returns:
        ComparativeResult with per-relation findings and snapshot run IDs.
    """
    label_a = label_a or description_a[:50]
    label_b = label_b or description_b[:50]

    results: dict[str, tuple[dict, dict]] = {}
    errors: dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(_run_one, lob, description_a): "a",
            pool.submit(_run_one, lob, description_b): "b",
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as exc:
                errors[key] = str(exc)

    if "a" in errors or "b" in errors:
        msg_parts = []
        if "a" in errors:
            msg_parts.append(f"A failed: {errors['a']}")
        if "b" in errors:
            msg_parts.append(f"B failed: {errors['b']}")
        raise RuntimeError("; ".join(msg_parts))

    persona_a, flow_a = results["a"]
    persona_b, flow_b = results["b"]

    run_id_a = snapshot_store.save(persona_a, flow_a, lob=lob, persona_desc=description_a)
    run_id_b = snapshot_store.save(persona_b, flow_b, lob=lob, persona_desc=description_b)

    premium_a = _extract_premium(flow_a)
    premium_b = _extract_premium(flow_b)
    uw_a = _extract_uw_conditions(flow_a)
    uw_b = _extract_uw_conditions(flow_b)
    blocked_a = bool(flow_a.get("blocked_reason"))
    blocked_b = bool(flow_b.get("blocked_reason"))

    findings = [
        _evaluate_relation(
            relation, premium_a, premium_b,
            uw_a, uw_b, blocked_a, blocked_b,
            label_a, label_b,
        )
        for relation in (relations or [])
    ]

    return ComparativeResult(
        label_a=label_a,
        label_b=label_b,
        run_id_a=run_id_a,
        run_id_b=run_id_b,
        persona_a=persona_a,
        persona_b=persona_b,
        premium_a=premium_a,
        premium_b=premium_b,
        uw_conditions_a=uw_a,
        uw_conditions_b=uw_b,
        blocked_a=blocked_a,
        blocked_b=blocked_b,
        findings=findings,
    )
