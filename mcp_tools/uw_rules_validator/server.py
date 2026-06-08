"""
MCP Server — UW Rules Validator.

A strict underwriter with zero patience. Every rule case is judged against
a known expected outcome. Deviations are classified, severity-rated, and
reported as actionable findings.

Exposes five tools:

  list_uw_rules         Show all registered rules and their case IDs
  run_uw_audit          Run all pre-defined cases for a LOB → violation report
  run_rule_cases        Run cases for a single rule → focused report
  test_custom_boundary  Feed any NL persona + expected outcome → validate result
  run_full_audit        Run every LOB → comprehensive cross-LOB audit

──────────────────────────────────────────────────────────────────────────────
REGISTER IN CLAUDE CODE  (~/.claude/settings.json or project .claude/settings.json)
──────────────────────────────────────────────────────────────────────────────

  "mcpServers": {
    "uw-rules-validator": {
      "command": "python",
      "args": ["-m", "mcp_tools.uw_rules_validator.server"],
      "cwd": "C:/Projects/SandboxPlaywright"
    }
  }

──────────────────────────────────────────────────────────────────────────────
USAGE EXAMPLES
──────────────────────────────────────────────────────────────────────────────

  # See all rules
  list_uw_rules()
  list_uw_rules("auto")

  # Run all Auto UW cases — finds false approvals, missing conditions, etc.
  run_uw_audit("auto")

  # Validate a single rule (e.g. only SR-22 cases)
  run_rule_cases("auto", "AUTO_SR22")
  run_rule_cases("auto", "AUTO_TRIPLE_RISK")

  # Feed a custom edge case with your expected outcome
  test_custom_boundary(
      lob="auto",
      description="SR-22 driver, age 24, revoked licence, leased vehicle",
      expected_outcome="uw_referral",
      expected_conditions=["SR-22", "driver license status", "under 25"]
  )

  # Full cross-LOB audit
  run_full_audit()
──────────────────────────────────────────────────────────────────────────────
"""

import concurrent.futures
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from mcp_tools.uw_rules_validator.rule_registry import (  # noqa: E402
    RULE_CASES, CASES_BY_LOB, CASES_BY_RULE, RULE_METADATA,
)
from mcp_tools.uw_rules_validator.validator import validate_case  # noqa: E402
from mcp_tools.uw_rules_validator.report_formatter import (  # noqa: E402
    format_audit_report, format_boundary_report,
)

# Policy flow runner (reused from policy_flow_generator)
from mcp_tools.policy_flow_generator.flow_runner import run_flow  # noqa: E402
from mcp_tools.policy_flow_generator.persona_generator import generate_persona  # noqa: E402

# ---------------------------------------------------------------------------
# Server definition
# ---------------------------------------------------------------------------

MAX_AUDIT_CASES = 30  # hard cap — each case launches a browser session (~60-120 s)

mcp = FastMCP(
    "uw-rules-validator",
    instructions=(
        "Strict underwriting rules validator. Runs pre-defined edge cases and custom "
        "boundary tests against the live application, then reports any inconsistencies: "
        "false approvals (rule missed a risky profile), false referrals (clean profile "
        "incorrectly flagged), missing conditions, wrong condition counts, and flow errors. "
        "Use list_uw_rules to explore the registry, run_uw_audit for a LOB-level sweep, "
        "run_rule_cases for a specific rule, and test_custom_boundary to feed your own "
        "edge-case persona with an expected outcome."
    ),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_cases(cases: list[dict]) -> list[dict]:
    """Run a list of rule cases and return all findings.

    Each case is dispatched to a ThreadPoolExecutor so that Playwright's
    sync API does not conflict with FastMCP's running asyncio event loop.
    """
    all_findings = []
    for case in cases:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(run_flow, case["lob"], case["persona"]).result()
        findings = validate_case(case, result)
        all_findings.extend(findings)
    return all_findings


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def list_uw_rules(lob: str = "") -> str:
    """
    List all registered UW rules and their pre-defined test cases.

    Each rule entry shows: rule ID, rule name, severity, LOB, case IDs,
    and whether cases are positive (should trigger UW), negative (should bind),
    or boundary (edge-case precision test).

    Args:
        lob: Optional filter — "auto" or "homeowner".
             Omit to see all LOBs.

    Returns:
        Formatted Markdown table of rules and case counts.
    """
    target_lob = lob.lower().strip() if lob else None
    lines = ["# Registered UW Rules\n"]

    lob_groups: dict[str, list] = {}
    for rule in RULE_METADATA.values():
        if target_lob and rule["lob"] != target_lob:
            continue
        lob_groups.setdefault(rule["lob"], []).append(rule)

    lob_display = {"auto": "Personal Auto", "homeowner": "Homeowner"}

    for lob_key in ["auto", "homeowner"]:
        rules = lob_groups.get(lob_key, [])
        if not rules:
            continue

        lines.append(f"## {lob_display.get(lob_key, lob_key.upper())}\n")
        lines.append("| Rule ID | Rule Name | Severity | Cases |")
        lines.append("|---------|-----------|----------|-------|")

        for rule in sorted(rules, key=lambda r: r["rule_id"]):
            cases = CASES_BY_RULE.get(rule["rule_id"], [])
            pos = sum(1 for c in cases if c["case_type"] == "positive")
            neg = sum(1 for c in cases if c["case_type"] == "negative")
            bnd = sum(1 for c in cases if c["case_type"] == "boundary")
            detail = f"+{pos} pos, -{neg} neg, ~{bnd} boundary" if (pos + neg + bnd) else "0"
            sev_icon = {"critical": "🔴", "high": "🟠", "warning": "🟡"}.get(rule["severity"], "")
            lines.append(
                f"| `{rule['rule_id']}` | {rule['rule_name']} "
                f"| {sev_icon} {rule['severity']} | {detail} |"
            )
        lines.append("")

    # Known Auto condition strings
    if not target_lob or target_lob == "auto":
        lines += [
            "### Auto — Confirmed UW Condition Text (substring match)",
            "",
            "| Trigger | Expected condition substring |",
            "|---------|------------------------------|",
            "| SR-22 | `SR-22 / Certificate of Insurance Indicator is checked` |",
            "| Licence | `driver license status that is revoked or suspended` |",
            "| Under 25 | `All drivers under 25 years of age` |",
        ]

    return "\n".join(lines)


@mcp.tool()
def run_uw_audit(lob: str) -> str:
    """
    Run all pre-defined UW rule cases for a line of business and report violations.

    Covers positive cases (should trigger UW), negative cases (should bind),
    and boundary cases (precision edge tests). Every deviation from the expected
    outcome is classified as a finding with severity and actionable description.

    Finding types:
      🔴 FALSE_APPROVE    — Rule engine missed a risky profile (critical)
      🟠 MISSING_CONDITION — Expected condition text absent from referral (high)
      🟡 FALSE_REFER       — Clean profile incorrectly referred (warning)
      🟡 WRONG_COUNT       — Fewer conditions than expected (warning)
      ℹ️  EXTRA_CONDITIONS  — More conditions than expected (info)
      🔴 FLOW_ERROR        — Browser flow failed (critical)

    Args:
        lob: "auto" or "homeowner"

    Returns:
        Markdown audit report — verdict, summary, all findings, pass table.

    Note: Each case launches a browser session (~60-120s per case).
          Full Auto audit (15 cases) takes approximately 15-30 minutes.
    """
    lob = lob.lower().strip()
    cases = CASES_BY_LOB.get(lob, [])

    if not cases:
        return f"**ERROR** — No rule cases registered for LOB '{lob}'. Valid: auto, homeowner"

    if len(cases) > MAX_AUDIT_CASES:
        return (
            f"**ERROR** — LOB '{lob}' has {len(cases)} cases, which exceeds the "
            f"per-call limit of {MAX_AUDIT_CASES}. Use run_rule_cases() to target "
            f"individual rules instead."
        )

    all_findings = _run_cases(cases)
    return format_audit_report(lob, all_findings)


@mcp.tool()
def run_rule_cases(lob: str, rule_id: str) -> str:
    """
    Run all cases for a specific UW rule and report findings.

    Use list_uw_rules() to get valid rule_id values.
    This is faster than run_uw_audit() when you want to test one rule in isolation.

    Args:
        lob:     "auto" or "homeowner"
        rule_id: e.g. "AUTO_SR22", "AUTO_TRIPLE_RISK", "HO_PRIOR_LOSSES"

    Returns:
        Markdown audit report scoped to the specified rule.

    Examples:
        run_rule_cases("auto", "AUTO_SR22")
        run_rule_cases("auto", "AUTO_TRIPLE_RISK")
        run_rule_cases("auto", "AUTO_UNDER25")
        run_rule_cases("auto", "AUTO_CLEAN_BASELINE")
        run_rule_cases("homeowner", "HO_PRIOR_LOSSES")
        run_rule_cases("homeowner", "HO_ALL_FLAGS")
    """
    lob = lob.lower().strip()
    rule_id = rule_id.upper().strip()

    cases = [c for c in CASES_BY_RULE.get(rule_id, []) if c["lob"] == lob]
    if not cases:
        all_rule_ids = sorted(CASES_BY_RULE.keys())
        return (
            f"**ERROR** — No cases found for rule `{rule_id}` in LOB `{lob}`.\n\n"
            f"Available rule IDs: {', '.join(f'`{r}`' for r in all_rule_ids)}"
        )

    all_findings = _run_cases(cases)
    return format_audit_report(lob, all_findings, rule_filter=rule_id)


@mcp.tool()
def test_custom_boundary(
    lob: str,
    description: str,
    expected_outcome: str,
    expected_conditions: list,
) -> str:
    """
    Feed a custom edge-case persona and validate it against your expected outcome.

    The AI generates a persona from your description, the full policy flow
    executes, and the result is judged against your expectations.

    Use this to:
    - Probe rules not yet in the registry
    - Verify a specific combination of risk factors
    - Check that a borderline profile behaves correctly
    - Regression-test a fixed rule after a system change

    Args:
        lob: "auto" or "homeowner"
        description: Natural-language edge-case persona, e.g.
            "SR-22 driver aged 24, revoked licence, leased vehicle, business use"
            "Healthcare business, 50 employees, no training, past phishing attack"
            "Homeowner with losses AND refused by previous insurer, 1948 build"
        expected_outcome: "uw_referral" or "policy_bound"
        expected_conditions: List of condition text substrings you expect to appear
            in the UW referral grid. Pass an empty list [] if you don't care about
            specific condition text, or if expecting policy_bound.
            Auto known substrings:
              "SR-22 / Certificate of Insurance Indicator is checked"
              "driver license status that is revoked or suspended"
              "All drivers under 25 years of age"

    Returns:
        Markdown boundary test report — generated persona JSON, verdict,
        actual UW conditions captured, and any inconsistencies found.

    Example:
        test_custom_boundary(
            lob="auto",
            description="Triple-risk: SR-22, revoked licence, age 22",
            expected_outcome="uw_referral",
            expected_conditions=[
                "SR-22 / Certificate of Insurance Indicator is checked",
                "driver license status that is revoked or suspended",
                "All drivers under 25 years of age"
            ]
        )
    """
    lob = lob.lower().strip()
    expected_outcome = expected_outcome.lower().strip()

    if expected_outcome not in ("uw_referral", "policy_bound"):
        return "**ERROR** — expected_outcome must be 'uw_referral' or 'policy_bound'"

    # Generate persona via AI
    persona_json = generate_persona(lob, description)
    try:
        persona = json.loads(persona_json)
    except json.JSONDecodeError:
        return f"**ERROR** — AI returned non-JSON: ```{persona_json}```"

    if persona.get("error"):
        return f"**ERROR** generating persona: {persona['error']}"

    # Build a synthetic rule case for validation
    synthetic_case = {
        "case_id": persona.get("TC_ID", "CUSTOM"),
        "rule_id": "CUSTOM",
        "rule_name": "Custom Boundary Test",
        "lob": lob,
        "case_type": "boundary",
        "severity": "high",
        "description": description,
        "persona": persona,
        "expected_outcome": expected_outcome,
        "expected_conditions": expected_conditions,
        "min_conditions": len(expected_conditions) if expected_conditions else None,
    }

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        flow_result = pool.submit(run_flow, lob, persona).result()
    findings = validate_case(synthetic_case, flow_result)

    report = format_boundary_report(
        lob=lob,
        description=description,
        expected_outcome=expected_outcome,
        expected_conditions=expected_conditions,
        flow_result=flow_result,
        findings=findings,
    )

    return (
        f"## Generated Persona\n\n"
        f"```json\n{json.dumps(persona, indent=2)}\n```\n\n"
        "---\n\n"
        f"{report}"
    )


@mcp.tool()
def run_full_audit() -> str:
    """
    Run every pre-defined rule case across all LOBs and produce a combined audit report.

    This is the most comprehensive validation — it sweeps Auto and Homeowner
    in a single call and surfaces any inconsistencies across the entire rule engine.

    ⚠️  This will take a long time. Expect 15-45 minutes depending on the number
    of cases and browser/network speed. Consider using run_uw_audit(lob) or
    run_rule_cases(lob, rule_id) for targeted validation.

    Returns:
        Combined Markdown audit report — cross-LOB summary + per-LOB details.
    """
    if len(RULE_CASES) > MAX_AUDIT_CASES:
        return (
            f"**ERROR** — Full audit has {len(RULE_CASES)} cases, which exceeds the "
            f"per-call limit of {MAX_AUDIT_CASES}. Use run_uw_audit(lob) per LOB or "
            f"run_rule_cases(lob, rule_id) for targeted validation."
        )

    all_findings = _run_cases(RULE_CASES)
    return format_audit_report("all", all_findings, custom_label="Full Cross-LOB UW Rules Audit")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
