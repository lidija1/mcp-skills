"""
Result formatter: converts flow_runner result dicts into readable Markdown reports.
Multi-LOB aware — shows LOB badge, persona type, premium (where available).
"""

from __future__ import annotations

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
    outcome_label = result.get("outcome", "unknown").replace("_", " ").title()
    persona_type = result.get("persona_type", "custom")
    tc_id = result.get("tc_id", "UNKNOWN")

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

    # UW conditions
    if result.get("uw_conditions"):
        lines += ["", "---", "", "### UW Conditions Triggered", ""]
        rows = _parse_uw_rows(result["uw_conditions"])
        if rows:
            lines += ["| Type | Condition |", "|------|-----------|"]
            for row in rows:
                lines.append(f"| {row.get('Type', '')} | {row.get('Condition', '')} |")
        else:
            for cell in result["uw_conditions"]:
                if cell:
                    lines.append(f"- {cell}")

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
