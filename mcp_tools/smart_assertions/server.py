"""
Smart Assertions MCP server — two tools only.

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
from dashboard.backend.api_assertions.regression_sweep import run_sweep, SweepResult, VariantResult, SweepAnalysis

mcp = FastMCP("smart-assertions")

# ---------------------------------------------------------------------------
# Stop-stage per assertion type
# ---------------------------------------------------------------------------

STOP_AFTER: dict[str, str] = {
    "premium":    "rating-detail",
    "total_cost": "verify-billing",
}

# ---------------------------------------------------------------------------
# Value extraction
# ---------------------------------------------------------------------------

def _total_premium(flow: dict) -> float | None:
    bv = flow.get("rating_factors", {}).get("business_values", {})
    val = bv.get("calculated_total_premium")
    if val is not None:
        try:
            return float(val)
        except (ValueError, TypeError):
            pass
    raw = (
        flow.get("rating_factors", {}).get("summary_premium")
        or flow.get("premium", "")
    )
    digits = re.sub(r"[^\d.]", "", str(raw or ""))
    if digits:
        try:
            return float(digits)
        except ValueError:
            pass
    return None


def _coverage_premiums(flow: dict) -> dict[str, float]:
    return (
        flow.get("rating_factors", {})
        .get("business_values", {})
        .get("coverage_premiums", {})
    )


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
    actual = snap.total_premium if assertion_type == "premium" else snap.total_cost
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
    - Total premium (sum of Policy Term Factor rows from Rating Detail)
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
        premium     — total premium from the Rating Detail page
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

    actual = snap.total_premium if assertion_type == "premium" else snap.total_cost
    passed, message = _assert(actual, expected_value, operator, tolerance_pct)

    return _fmt_assert(snap, assertion_type, expected_value, operator, tolerance_pct, passed, message)


# ---------------------------------------------------------------------------
# Regression sweep report formatter
# ---------------------------------------------------------------------------

def _fmt_sweep(sweep: SweepResult) -> str:
    base_str = f"${sweep.baseline_premium:,.2f}" if sweep.baseline_premium else "N/A"
    status = "✅ ALL PASS" if sweep.passed else f"❌ {sweep.fail_count} FAILED"
    lines = [
        f"## Regression Sweep `{sweep.sweep_id}` — {status}",
        f"**Baseline:** {sweep.baseline_description}",
        f"**Baseline premium:** {base_str}",
        f"**Variants:** {len(sweep.results)} total | ✅ {sweep.pass_count}  ❌ {sweep.fail_count}",
        "",
    ]

    # Group results by category
    categories = ["risk_adding", "ladder", "discount", "hard_stop"]
    cat_labels = {
        "risk_adding": "RISK ADDING",
        "ladder":      "LADDER (monotonic)",
        "discount":    "DISCOUNTS",
        "hard_stop":   "HARD STOPS",
    }

    for cat in categories:
        cat_results = [r for r in sweep.results if r.variant.category == cat]
        if not cat_results:
            continue
        lines.append(f"### {cat_labels.get(cat, cat.upper())}")
        lines += ["| Variant | Premium | Delta | Direction | Magnitude | Result |",
                  "|---|---|---|---|---|---|"]
        for r in cat_results:
            if r.error:
                lines.append(f"| {r.variant.label} | — | — | — | — | ❌ `{r.error[:50]}` |")
                continue
            actual = f"${r.actual_premium:,.2f}" if r.actual_premium else ("blocked" if r.blocked else "N/A")
            delta = f"{r.delta_pct:+.1f}%" if r.delta_pct is not None else "—"
            dir_ok = "✅" if r.direction_passed else f"❌ expected {r.variant.expected_direction}"
            mag_ok = "✅" if r.magnitude_passed else ("—" if r.magnitude_passed is None else "❌")
            ok = "✅" if r.passed else "❌"
            msg = f" `{r.message}`" if r.message and not r.passed else ""
            lines.append(f"| {r.variant.label} | {actual} | {delta} | {dir_ok} | {mag_ok} | {ok}{msg} |")
        lines.append("")

    # Ladder monotonic check inline
    from dashboard.backend.api_assertions.regression_sweep import _check_ladder_monotonic
    ladder_violations = _check_ladder_monotonic(sweep.results)
    if ladder_violations:
        lines += ["### Ladder Violations"] + [f"- ❌ {v}" for v in ladder_violations] + [""]

    # AI analysis
    if sweep.analysis:
        a = sweep.analysis
        lines.append("### AI Analysis")
        if a.patterns:
            lines.append("**Patterns detected:**")
            lines += [f"- {p}" for p in a.patterns]
            lines.append("")
        if a.root_causes:
            lines.append("**Likely root causes:**")
            lines += [f"- {c}" for c in a.root_causes]
            lines.append("")
        if a.follow_up_variants:
            lines.append("**Suggested follow-up variants:**")
            for v in a.follow_up_variants:
                mag = ""
                if v.min_delta_pct is not None:
                    mag = f", min {v.min_delta_pct}%"
                if v.max_delta_pct is not None:
                    mag += f" max {v.max_delta_pct}%"
                lines.append(f"- **{v.label}** — expected `{v.expected_direction}`{mag}")
            lines.append("")

    lines.append(f"_sweep_id: `{sweep.sweep_id}`  |  baseline run_id: `{sweep.baseline_run_id}`_")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MCP tool: batch_regression_sweep
# ---------------------------------------------------------------------------

@mcp.tool()
def batch_regression_sweep(
    baseline_description: str,
    lob: str = "auto",
    focus: str | None = None,
) -> str:
    """
    Full AI-driven premium regression sweep against a clean baseline persona.

    Phase 1 — AI generates a variant list covering risk-adding mutations,
               discounts, hard stops, and ladder sequences.
    Phase 2 — Baseline snapshot captured via OneShield API replay.
    Phase 3 — All variants run in parallel; rule assertions check premium
               direction (gt/lt/blocked) and magnitude bands.
    Phase 4 — AI reads the full result table and identifies cross-row patterns,
               likely root causes, and follow-up variants to probe anomalies.

    Args:
        baseline_description: Plain-English clean baseline persona, e.g.
            "35-year-old married driver, Gold coverage, clean record, pleasure use"
        lob:    Line of business — currently only "auto" is supported.
        focus:  Optional category filter. One of: "risk_adding", "discount",
                "hard_stop", "ladder". Omit for a full sweep across all categories.
    """
    try:
        sweep = run_sweep(baseline_description, lob=lob, focus=focus)
    except Exception as exc:
        return f"❌ Sweep failed: {exc}"
    return _fmt_sweep(sweep)


if __name__ == "__main__":
    mcp.run()
