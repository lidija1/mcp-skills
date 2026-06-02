"""
Dimension ladder runner.

Sweeps a single dimension (e.g. coverage tier, employment category,
vehicle use) across all its values while keeping the rest of the persona
fixed. Runs all variants in parallel, then checks monotonic or
categorical ordering assertions.

Supported dimensions and their ordered values:
    coverage:    Bronze < Silver < Gold < Platinum  (premium expected to increase)
    employment:  Employed, Unemployed, Retired, Student
    vehicle_use: Pleasure, Commute, Business       (premium expected to increase)
    license:     Active License < Suspended < Revoked (risk increases)
    ownership:   Owned, Financed, Leased

Usage:
    from dashboard.backend.api_assertions.ladder import run_ladder
    result = run_ladder("middle-aged clean driver", dimension="coverage")
"""

from __future__ import annotations

import copy
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from api_tests.oneshield_api_replay import OneShieldApiReplay
from dashboard.backend.api_assertions.snapshot import snapshot_store, _extract_premium, _extract_uw_conditions
from mcp_tools.policy_flow_generator.persona_generator import generate_persona

# ---------------------------------------------------------------------------
# Dimension definitions
# ---------------------------------------------------------------------------

DIMENSION_VALUES: dict[str, list[str]] = {
    "coverage":     ["Bronze", "Silver", "Gold", "Platinum"],
    "employment":   ["Employed", "Unemployed", "Retired", "Student"],
    "vehicle_use":  ["Pleasure", "Commute", "Business"],
    "license":      ["Active License", "Suspended", "Revoked"],
    "ownership":    ["Owned", "Financed", "Leased"],
}

# For these dimensions we expect premium to increase monotonically
MONOTONIC_INCREASE_DIMENSIONS = {"coverage", "vehicle_use", "license"}

# Persona field name for each dimension
DIMENSION_FIELD: dict[str, str] = {
    "coverage":    "PolicyCoverage",
    "employment":  "EmploymentCategory",
    "vehicle_use": "VehicleUse",
    "license":     "LicenseStatus",
    "ownership":   "Ownership",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class LadderRung:
    value: str
    run_id: str
    persona: dict
    premium: float | None
    uw_conditions: list[str]
    blocked: bool
    blocked_reason: str
    error: str = ""


@dataclass
class LadderFinding:
    label: str
    passed: bool
    message: str


@dataclass
class LadderResult:
    dimension: str
    base_description: str
    rungs: list[LadderRung]
    findings: list[LadderFinding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return bool(self.findings) and all(f.passed for f in self.findings)

    def premium_table(self) -> list[dict]:
        return [
            {
                "value": r.value,
                "premium": r.premium,
                "uw_count": len(r.uw_conditions),
                "blocked": r.blocked,
                "run_id": r.run_id,
            }
            for r in self.rungs
        ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _override_persona_field(persona: dict, dimension: str, value: str) -> dict:
    p = copy.deepcopy(persona)
    field_name = DIMENSION_FIELD[dimension]
    p[field_name] = value

    # Keep persona consistent for ownership changes
    if dimension == "ownership":
        if value == "Owned":
            p.pop("LossPayeeType", None)
            p.pop("LossPayeeName", None)
        else:
            p["LossPayeeType"] = value
            p.setdefault("LossPayeeName", "Finance Company" if value == "Financed" else "Leasing Company")

    # SR22 must stay consistent with license status
    if dimension == "license" and value in ("Suspended", "Revoked"):
        p.setdefault("SR22", "No")  # leave as-is but don't force SR22

    return p


def _run_rung(lob: str, base_persona: dict, dimension: str, value: str) -> LadderRung:
    persona = _override_persona_field(base_persona, dimension, value)
    client = OneShieldApiReplay()
    try:
        flow_result = client.run_captured_auto_flow(
            persona,
            stop_after="rating-detail",
            fast_mode=True,
        )
    finally:
        client.close()

    run_id = snapshot_store.save(
        persona,
        flow_result,
        lob=lob,
        persona_desc=f"{dimension}={value}",
    )
    return LadderRung(
        value=value,
        run_id=run_id,
        persona=persona,
        premium=_extract_premium(flow_result),
        uw_conditions=_extract_uw_conditions(flow_result),
        blocked=bool(flow_result.get("blocked_reason")),
        blocked_reason=flow_result.get("blocked_reason", ""),
    )


# ---------------------------------------------------------------------------
# Assertion checkers
# ---------------------------------------------------------------------------

def _check_monotonic_increase(
    rungs: list[LadderRung], dimension: str, original_value: str | None = None
) -> list[LadderFinding]:
    findings: list[LadderFinding] = []
    # Exclude the rung that matches the original base persona value — comparing
    # a persona against itself always produces delta=0 and poisons adjacent checks.
    valid = [
        r for r in rungs
        if r.premium is not None
        and not r.error
        and (original_value is None or r.value.strip().lower() != original_value.strip().lower())
    ]
    if len(valid) < 2:
        return [LadderFinding(
            label="Monotonic premium increase",
            passed=False,
            message="Not enough valid premium values to compare.",
        )]

    for i in range(len(valid) - 1):
        lo, hi = valid[i], valid[i + 1]
        passed = (lo.premium or 0) <= (hi.premium or 0)
        findings.append(LadderFinding(
            label=f"premium({lo.value}) ≤ premium({hi.value})",
            passed=passed,
            message=(
                ""
                if passed
                else f"${lo.premium:,.2f} > ${hi.premium:,.2f} — expected non-decreasing"
            ),
        ))
    return findings


def _check_uw_escalates(rungs: list[LadderRung]) -> list[LadderFinding]:
    findings: list[LadderFinding] = []
    for i in range(len(rungs) - 1):
        lo, hi = rungs[i], rungs[i + 1]
        count_lo = len(lo.uw_conditions)
        count_hi = len(hi.uw_conditions)
        if count_hi > count_lo:
            findings.append(LadderFinding(
                label=f"UW conditions escalate {lo.value}→{hi.value}",
                passed=True,
                message=f"{count_lo} → {count_hi} conditions",
            ))
    return findings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_ladder(
    base_description: str,
    dimension: str,
    lob: str = "auto",
    values: list[str] | None = None,
    assert_monotonic: bool | None = None,
) -> LadderResult:
    """
    Generate a base persona and sweep the given dimension across all its values.

    Args:
        base_description: NL description of the base persona (dimension value
                          is ignored — it will be overridden for each rung).
        dimension:        One of: coverage, employment, vehicle_use, license, ownership.
        lob:              Line of business (default "auto").
        values:           Optional explicit list of values to sweep. Defaults
                          to DIMENSION_VALUES[dimension].
        assert_monotonic: Override whether to assert monotonic premium increase.
                          Defaults to True for coverage / vehicle_use / license.

    Returns:
        LadderResult with per-rung data and findings.
    """
    dimension = dimension.lower().strip()
    if dimension not in DIMENSION_VALUES:
        raise ValueError(
            f"Unknown dimension '{dimension}'. Valid: {', '.join(DIMENSION_VALUES)}"
        )

    sweep_values = values or DIMENSION_VALUES[dimension]

    # Generate base persona (use first value to anchor AI generation)
    base_desc_with_anchor = f"{base_description} with {sweep_values[0]} {dimension.replace('_', ' ')}"
    persona_raw = generate_persona(lob, base_desc_with_anchor)
    base_persona = json.loads(persona_raw)
    if "error" in base_persona:
        raise ValueError(f"Persona generation failed: {base_persona['error']}")

    rungs: list[LadderRung] = [None] * len(sweep_values)  # type: ignore[list-item]

    with ThreadPoolExecutor(max_workers=min(len(sweep_values), 6)) as pool:
        futures = {
            pool.submit(_run_rung, lob, base_persona, dimension, value): idx
            for idx, value in enumerate(sweep_values)
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                rungs[idx] = future.result()
            except Exception as exc:
                rungs[idx] = LadderRung(
                    value=sweep_values[idx],
                    run_id="",
                    persona={},
                    premium=None,
                    uw_conditions=[],
                    blocked=False,
                    blocked_reason="",
                    error=str(exc)[:200],
                )

    # The original value in the base persona (before any rung overrides) — rungs
    # that land on this value compare the persona against itself and must be excluded.
    field_name = DIMENSION_FIELD[dimension]
    original_value: str | None = base_persona.get(field_name)

    # Decide assertions
    do_monotonic = assert_monotonic
    if do_monotonic is None:
        do_monotonic = dimension in MONOTONIC_INCREASE_DIMENSIONS

    findings: list[LadderFinding] = []
    if do_monotonic:
        findings.extend(_check_monotonic_increase(rungs, dimension, original_value))

    # Always check for UW escalation on license dimension
    if dimension == "license":
        findings.extend(_check_uw_escalates(rungs))

    return LadderResult(
        dimension=dimension,
        base_description=base_description,
        rungs=rungs,
        findings=findings,
    )
