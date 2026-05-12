"""
Result formatter: converts flow_runner result dicts into readable Markdown reports.
Multi-LOB aware — shows LOB badge, persona type, premium (where available).
"""

from __future__ import annotations

# Known UW rule definitions: (condition_substring, rule_id, rule_name, lob)
# Condition substrings are case-sensitive, matching UWReferralPage.assert_uw_condition logic.
_KNOWN_RULES: list[tuple[str, str, str, str]] = [
    # Auto
    (
        "SR-22 / Certificate of Insurance Indicator is checked",
        "AUTO_SR22",
        "SR-22 Certificate Required",
        "auto",
    ),
    (
        "driver license status that is revoked or suspended",
        "AUTO_LICENSE",
        "Suspended/Revoked License",
        "auto",
    ),
    (
        "All drivers under 25 years of age",
        "AUTO_UNDER25",
        "Driver Under 25 Years of Age",
        "auto",
    ),
]


def _match_rules(raw_cells: list[str]) -> list[dict]:
    """Return list of matched rule dicts for the given raw UW grid cells."""
    matched = []
    seen_ids: set[str] = set()
    for substring, rule_id, rule_name, lob in _KNOWN_RULES:
        if rule_id not in seen_ids and any(substring in cell for cell in raw_cells):
            matched.append({"rule_id": rule_id, "rule_name": rule_name, "lob": lob})
            seen_ids.add(rule_id)
    return matched


_STATUS_LABEL = {
    "passed": "PASSED",
    "failed": "FAILED",
    "uw_referral": "UW REFERRAL (soft-stop)",
}

_STATUS_EMOJI = {
    "passed": "✅",
    "failed": "❌",
    "uw_referral": "⚠️",
}

_STEP_ICON = {
    "passed": "✓",
    "failed": "✗",
}

_OUTCOME_LABEL = {
    "policy_bound": "Policy Bound",
    "uw_referral": "UW Referral",
    "error": "Policy Creation Failed",
}

_LOB_LABEL = {
    "auto": "Personal Auto",
    "cyber": "Cyber",
    "homeowner": "Homeowner",
}

# UW referral gridcell columns: Asset | Condition | Type | Comments | Overridden?
_UW_COL_NAMES = ["Asset", "Condition", "Type", "Comments", "Overridden?"]


def _parse_uw_rows(raw_cells: list[str]) -> list[dict]:
    if not raw_cells or len(raw_cells) % len(_UW_COL_NAMES) != 0:
        return []
    rows = []
    for i in range(0, len(raw_cells), len(_UW_COL_NAMES)):
        rows.append(dict(zip(_UW_COL_NAMES, raw_cells[i: i + len(_UW_COL_NAMES)])))
    return rows


def format_result(result: dict) -> str:
    """
    Convert a run_flow() result dict into a Markdown string.

    Args:
        result: Dict from flow_runner.run_flow()

    Returns:
        Multi-line Markdown report.
    """
    lob = result.get("lob", "unknown")
    lob_label = _LOB_LABEL.get(lob, lob.upper())
    status = result.get("overall_status", "failed")
    status_label = _STATUS_LABEL.get(status, status.upper())
    status_emoji = _STATUS_EMOJI.get(status, "")
    outcome = result.get("outcome", "unknown")
    outcome_label = _OUTCOME_LABEL.get(outcome, str(outcome).replace("_", " ").title())
    persona_type = result.get("persona_type", "custom")
    tc_id = result.get("tc_id", "UNKNOWN")
    policy_summary = result.get("policy_summary") or {}
    policy_number = policy_summary.get("Policy Number")

    lines: list[str] = [
        f"## {status_emoji} Policy Flow Result — `{tc_id}`",
        "",
        f"| | |",
        f"|---|---|",
        f"| **LOB** | {lob_label} |",
        f"| **Persona** | {persona_type} |",
        f"| **Status** | {status_label} |",
        f"| **Outcome** | {outcome_label} |",
        f"| **Total Duration** | {result.get('total_duration_s', 0)}s |",
    ]

    if result.get("premium"):
        lines.append(f"| **Premium** | {result['premium']} |")
    if policy_number:
        lines.append(f"| **Policy Number** | {policy_number} |")

    lines += ["", "---", "", "### Steps", ""]
    lines += [
        "| # | Step | Status | Duration |",
        "|---|------|--------|----------|",
    ]
    for i, step in enumerate(result.get("steps", []), 1):
        icon = _STEP_ICON.get(step["status"], "?")
        detail = f"<br>_{step['detail']}_" if step.get("detail") else ""
        lines.append(
            f"| {i} | {step['step']}{detail} | {icon} {step['status']} | {step['duration_s']}s |"
        )

    # UW rules
    if result.get("uw_conditions"):
        matched = _match_rules(result["uw_conditions"])
        lines += ["", "---", "", "### UW Rules Triggered", ""]
        if matched:
            for m in matched:
                lines.append(f"- {m['rule_name']}")
        else:
            lines.append("_No known rules matched — condition text may be unrecognized or LOB-specific._")

    # Error
    if result.get("error"):
        lines += ["", "---", "", "### Error", "", "```", result["error"].strip(), "```"]

    # Screenshot
    if result.get("screenshot_path"):
        lines += [
            "",
            f"> **Failure screenshot:** `{result['screenshot_path']}`",
        ]

    return "\n".join(lines)


def format_batch_summary(results: list[dict]) -> str:
    """Format a compact summary table for multiple policy flow results."""
    if not results:
        return "_No results._"

    lines = [
        "## Batch Flow Summary",
        "",
        "| TC ID | LOB | Persona | Outcome | Duration |",
        "|-------|-----|---------|---------|----------|",
    ]
    for r in results:
        lob = _LOB_LABEL.get(r.get("lob", ""), r.get("lob", "").upper())
        outcome = r.get("outcome", "error").replace("_", " ").title()
        emoji = _STATUS_EMOJI.get(r.get("overall_status", "failed"), "")
        lines.append(
            f"| `{r.get('tc_id', '?')}` | {lob} | {r.get('persona_type', '?')} "
            f"| {emoji} {outcome} | {r.get('total_duration_s', 0)}s |"
        )

    total = len(results)
    passed = sum(1 for r in results if r.get("overall_status") == "passed")
    uw = sum(1 for r in results if r.get("overall_status") == "uw_referral")
    failed = sum(1 for r in results if r.get("overall_status") == "failed")

    lines += [
        "",
        f"**Total:** {total} | "
        f"✅ Bound: {passed} | "
        f"⚠️ UW Referral: {uw} | "
        f"❌ Failed: {failed}",
    ]
    return "\n".join(lines)
