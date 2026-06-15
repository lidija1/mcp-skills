"""
Smart Assertions MCP server.

  snapshot_flow  Run a persona through OneShield API replay and save the raw
                 result (premium, per-coverage breakdown, UW conditions) to the
                 in-memory store for 1 hour.

  assert_flow    Generate a persona, run the API replay, assert your expected
                 value against the actual result. Operators: approx (±N%),
                 equals, gt, lt. Always reports all coverage premiums even when
                 asserting only the total.

Only Personal Auto is supported at this stage (lob="auto").
"""
from __future__ import annotations

import json
import re
import sys
import time
import uuid
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env", override=True)

from mcp.server.fastmcp import FastMCP
from mcp_tools.smart_assertions.store import store, Snapshot
from mcp_tools.policy_flow_generator.persona_generator import generate_persona
from api_tests.oneshield_api_replay import OneShieldApiReplay
from dashboard.backend.api_assertions.premium import extract_premium_evidence

mcp = FastMCP("smart-assertions")

# ---------------------------------------------------------------------------
# Stop-stage per assertion type
# ---------------------------------------------------------------------------

STOP_AFTER: dict[str, str] = {
    "premium":        "rating-detail",
    "total_cost":     "verify-billing",
    "base_rate_bi":   "rating-detail",
    "base_rate_pd":   "rating-detail",
    "base_rate_coll": "rating-detail",
    "base_rate_comp": "rating-detail",
    "base_rate_med":  "rating-detail",
}

# Maps UI assertion type → coverage substring used for matching Base Rate rows
BASE_RATE_COVERAGE: dict[str, str] = {
    "base_rate_bi":   "Bodily Injury",
    "base_rate_pd":   "Property Damage",
    "base_rate_coll": "Collision",
    "base_rate_comp": "Comprehensive",
    "base_rate_med":  "Medical",
}

# ---------------------------------------------------------------------------
# Value extraction
# ---------------------------------------------------------------------------

def _total_premium(flow: dict) -> float | None:
    return extract_premium_evidence(flow).value


def _coverage_premiums(flow: dict) -> dict[str, float]:
    return (
        flow.get("rating_factors", {})
        .get("business_values", {})
        .get("coverage_premiums", {})
    )


def _base_rates(flow: dict) -> dict[str, float]:
    rows = (
        flow.get("rating_factors", {})
        .get("business_values", {})
        .get("base_rates", [])
    )
    result: dict[str, float] = {}
    for r in rows:
        cov = str(r.get("coverage", "")).strip()
        val = r.get("value")
        if cov and val is not None:
            try:
                result[cov] = float(str(val).replace(",", ""))
            except (ValueError, TypeError):
                pass
    return result


def _total_cost(flow: dict) -> float | None:
    COST_KEYWORDS = ("total", "amount due", "due today", "cost", "policy total")
    for stage_data in flow.get("stage_ui_data", {}).values():
        for label, values in stage_data.get("field_values", {}).items():
            if any(kw in label.lower() for kw in COST_KEYWORDS):
                for val in values:
                    digits = re.sub(r"[^\d.]", "", str(val or ""))
                    if digits:
                        try:
                            return float(digits)
                        except ValueError:
                            pass
    for label, values in flow.get("ui_data", {}).get("field_values", {}).items():
        if any(kw in label.lower() for kw in COST_KEYWORDS):
            for val in values:
                digits = re.sub(r"[^\d.]", "", str(val or ""))
                if digits:
                    try:
                        return float(digits)
                    except ValueError:
                        pass
    return None


def _uw_conditions(flow: dict) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for stage_data in flow.get("stage_ui_data", {}).values():
        for grid in stage_data.get("grids", []):
            for row in grid.get("rows", []):
                text = " | ".join(str(v) for v in row.values() if v)
                if text and text not in seen:
                    seen.add(text)
                    rows.append(text)
    if not rows and flow.get("blocked_reason"):
        for grid in flow.get("ui_data", {}).get("grids", []):
            for row in grid.get("rows", []):
                text = " | ".join(str(v) for v in row.values() if v)
                if text and text not in seen:
                    seen.add(text)
                    rows.append(text)
    return rows


# ---------------------------------------------------------------------------
# Snapshot builder
# ---------------------------------------------------------------------------

def _build_snapshot(
    persona_description: str,
    persona: dict,
    flow: dict,
    assertion_type: str,
    lob: str,
) -> Snapshot:
    return Snapshot(
        run_id=str(uuid.uuid4()),
        persona_description=persona_description,
        persona=persona,
        lob=lob,
        created_at=time.time(),
        stop_after=STOP_AFTER.get(assertion_type, "rating-detail"),
        total_premium=_total_premium(flow),
        total_cost=_total_cost(flow),
        coverage_premiums=_coverage_premiums(flow),
        base_rates=_base_rates(flow),
        uw_conditions=_uw_conditions(flow),
        blocked=bool(flow.get("blocked_reason")),
        blocked_reason=flow.get("blocked_reason", ""),
        raw=flow,
    )


# ---------------------------------------------------------------------------
# Assertion logic
# ---------------------------------------------------------------------------

VALID_OPERATORS = {"approx", "equals", "eq", "gt", "greater_than", "lt", "less_than"}


def _assert(actual: float | None, expected: float, operator: str, tol: float) -> tuple[bool, str]:
    if actual is None:
        return False, "No value could be extracted from the API response"

    if operator == "approx":
        margin = abs(expected) * (tol / 100.0)
        passed = abs(actual - expected) <= margin
        return passed, "" if passed else f"${actual:,.2f} not within ±{tol:.0f}% of ${expected:,.2f} (±${margin:,.2f})"

    if operator in ("equals", "eq"):
        passed = actual == expected
        return passed, "" if passed else f"${actual:,.2f} ≠ ${expected:,.2f}"

    if operator in ("gt", "greater_than"):
        passed = actual > expected
        return passed, "" if passed else f"${actual:,.2f} not > ${expected:,.2f}"

    if operator in ("lt", "less_than"):
        passed = actual < expected
        return passed, "" if passed else f"${actual:,.2f} not < ${expected:,.2f}"

    return False, f"Unknown operator '{operator}'"


# ---------------------------------------------------------------------------
# Report formatters
# ---------------------------------------------------------------------------

def _op_label(operator: str, tol: float) -> str:
    return {
        "approx":       f"≈ ±{tol:.0f}%",
        "equals":       "= (exact)",
        "eq":           "= (exact)",
        "gt":           ">",
        "greater_than": ">",
        "lt":           "<",
        "less_than":    "<",
    }.get(operator, operator)


def _coverage_table_lines(coverage_premiums: dict[str, float], total: float | None) -> list[str]:
    if not coverage_premiums:
        return []
    lines = ["| Coverage | Premium |", "|---|---|"]
    for cov, prem in coverage_premiums.items():
        lines.append(f"| {cov} | ${prem:,.2f} |")
    if total is not None:
        lines.append(f"| **Total** | **${total:,.2f}** |")
    return lines


def _fmt_snapshot(snap: Snapshot) -> str:
    lines = [
        f"## Snapshot — `{snap.run_id[:8]}…`",
        f"**Persona:** {snap.persona_description[:100]}",
        f"**LOB:** {snap.lob}  |  **Stop:** {snap.stop_after}",
        "",
    ]

    if snap.blocked:
        lines += [f"⚠️ **Blocked:** {snap.blocked_reason}", ""]

    prem_str = f"${snap.total_premium:,.2f}" if snap.total_premium is not None else "N/A"
    lines.append(f"**Total premium:** {prem_str}")
    evidence = extract_premium_evidence(snap.raw)
    lines.append(f"**Premium source:** `{evidence.source}`")
    if evidence.mismatch:
        lines.append(
            "**Rating Detail diagnostic:** "
            f"${evidence.rating_detail_value:,.2f} (does not match Premium Summary)"
        )
    if snap.total_cost is not None:
        lines.append(f"**Total cost:** ${snap.total_cost:,.2f}")
    lines.append("")

    cov_lines = _coverage_table_lines(snap.coverage_premiums, snap.total_premium)
    if cov_lines:
        lines += ["### Coverage premiums"] + cov_lines + [""]

    if snap.uw_conditions:
        lines += ["### UW conditions"] + [f"- {c[:160]}" for c in snap.uw_conditions[:10]] + [""]

    lines.append(f"_run_id: `{snap.run_id}`  (valid 1 hour)_")
    return "\n".join(lines)


def _fmt_assert(
    snap: Snapshot,
    assertion_type: str,
    expected: float,
    operator: str,
    tol: float,
    passed: bool,
    message: str,
) -> str:
    if assertion_type == "premium":
        actual = snap.total_premium
    elif assertion_type in BASE_RATE_COVERAGE:
        actual = snap.base_rates.get(BASE_RATE_COVERAGE[assertion_type])
    else:
        actual = snap.total_cost
    actual_str = f"${actual:,.2f}" if actual is not None else "N/A"
    status = "✅ PASS" if passed else "❌ FAIL"

    lines = [
        f"## Assert {assertion_type.replace('_', ' ').title()} — {status}",
        f"**Persona:** {snap.persona_description[:100]}",
        "",
        "| | Value |",
        "|---|---|",
        f"| Expected | ${expected:,.2f} |",
        f"| Actual   | {actual_str} |",
        f"| Operator | {_op_label(operator, tol)} |",
        f"| Result   | {status} |",
    ]
    if message:
        lines.append(f"| Detail   | {message} |")
    lines.append("")

    evidence = extract_premium_evidence(snap.raw)
    lines += [f"**Premium source:** `{evidence.source}`", ""]
    if evidence.mismatch:
        lines += [
            (
                "**Rating Detail diagnostic:** "
                f"${evidence.rating_detail_value:,.2f} does not match "
                f"Premium Summary ${evidence.ui_value:,.2f}; assertion used Premium Summary."
            ),
            "",
        ]

    if snap.blocked:
        lines += [f"⚠️ **Blocked:** {snap.blocked_reason}", ""]

    cov_lines = _coverage_table_lines(snap.coverage_premiums, snap.total_premium)
    if cov_lines:
        lines += ["### Coverage premiums (informational)"] + cov_lines + [""]

    if snap.uw_conditions:
        lines += ["### UW conditions"] + [f"- {c[:160]}" for c in snap.uw_conditions[:10]] + [""]

    lines.append(f"_run_id: `{snap.run_id}`  (valid 1 hour)_")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

@mcp.tool()
def snapshot_flow(
    persona_description: str,
    lob: str = "auto",
) -> str:
    """
    Generate a Personal Auto persona from a natural-language description, run it
    through the OneShield API replay (no browser), and save the result in-memory
    for 1 hour.

    The report shows:
    - Total premium from the Premium Summary UI model
    - Per-coverage premium breakdown (Bodily Injury, Collision, Comprehensive, etc.)
    - UW conditions if any fired
    - Blocked status and reason
    - run_id for reference

    Args:
        persona_description: Plain-English description, e.g.
            "35-year-old married driver, Gold coverage, clean record, pleasure use"
        lob: Line of business — currently only "auto" is supported.
    """
    persona_raw = generate_persona(lob, persona_description)
    try:
        persona = json.loads(persona_raw)
    except Exception:
        return f"❌ Could not parse persona JSON: {persona_raw[:200]}"
    if "error" in persona:
        return f"❌ Persona generation failed: {persona['error']}"

    client = OneShieldApiReplay()
    try:
        flow = client.run_captured_auto_flow(persona, stop_after="rating-detail", fast_mode=True)
    except Exception as exc:
        return f"❌ API flow error: {exc}"
    finally:
        client.close()

    snap = _build_snapshot(persona_description, persona, flow, "premium", lob)
    store.save(snap)
    return _fmt_snapshot(snap)


@mcp.tool()
def assert_flow(
    persona_description: str,
    assertion_type: str,
    expected_value: float,
    operator: str = "approx",
    tolerance_pct: float = 5.0,
    lob: str = "auto",
) -> str:
    """
    Generate a Personal Auto persona, run the OneShield API replay, and assert
    your expected value against the actual result. Also saves the snapshot.

    Assertion types:
        premium     — total premium from the Premium Summary UI model
        total_cost  — total policy cost from the Verify Billing page

    Operators:
        approx       — actual within ±tolerance_pct% of expected  (default ±5%)
        equals / eq  — exact numeric match
        gt           — actual > expected
        lt           — actual < expected

    The report always includes per-coverage premiums as informational data
    regardless of which assertion type you choose.

    Args:
        persona_description: Plain-English driver/policy description.
        assertion_type:      "premium" or "total_cost".
        expected_value:      The value you expect (e.g. 1247.00).
        operator:            approx / equals / eq / gt / lt.  Default: approx.
        tolerance_pct:       Tolerance % for "approx". Default: 5.0.
        lob:                 Line of business — currently only "auto".
    """
    if assertion_type not in STOP_AFTER:
        return f"❌ Unknown assertion_type '{assertion_type}'. Valid: {sorted(STOP_AFTER)}"
    if operator not in VALID_OPERATORS:
        return f"❌ Unknown operator '{operator}'. Valid: {sorted(VALID_OPERATORS)}"

    persona_raw = generate_persona(lob, persona_description)
    try:
        persona = json.loads(persona_raw)
    except Exception:
        return f"❌ Could not parse persona JSON: {persona_raw[:200]}"
    if "error" in persona:
        return f"❌ Persona generation failed: {persona['error']}"

    client = OneShieldApiReplay()
    try:
        flow = client.run_captured_auto_flow(
            persona, stop_after=STOP_AFTER[assertion_type], fast_mode=True
        )
    except Exception as exc:
        return f"❌ API flow error: {exc}"
    finally:
        client.close()

    snap = _build_snapshot(persona_description, persona, flow, assertion_type, lob)
    store.save(snap)

    if assertion_type == "premium":
        actual = snap.total_premium
    elif assertion_type in BASE_RATE_COVERAGE:
        actual = snap.base_rates.get(BASE_RATE_COVERAGE[assertion_type])
    else:
        actual = snap.total_cost
    passed, message = _assert(actual, expected_value, operator, tolerance_pct)

    return _fmt_assert(snap, assertion_type, expected_value, operator, tolerance_pct, passed, message)


if __name__ == "__main__":
    mcp.run()
