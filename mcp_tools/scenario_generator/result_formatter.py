"""
Result formatter: converts the scenario_runner result dict into a readable
Markdown report returned by the MCP tools.
"""

from __future__ import annotations


_STATUS_LABEL = {
    "passed": "PASSED",
    "failed": "FAILED",
    "uw_referral": "UW REFERRAL (soft-stop)",
}

_STEP_ICON = {
    "passed": "✓",
    "failed": "✗",
}

# Gridcell column order on the UW referral page:
# Asset | Condition | Type | Comments | Overridden?
# We pull columns by position so we can present them nicely.
_UW_COL_NAMES = ["Asset", "Condition", "Type", "Comments", "Overridden?"]


def _parse_uw_rows(raw_cells: list[str]) -> list[dict]:
    """
    Group the flat gridcell list into structured rows of 5 columns each.
    Returns an empty list if the cell count is not a multiple of 5.
    """
    if not raw_cells or len(raw_cells) % len(_UW_COL_NAMES) != 0:
        return []
    rows = []
    for i in range(0, len(raw_cells), len(_UW_COL_NAMES)):
        rows.append(dict(zip(_UW_COL_NAMES, raw_cells[i : i + len(_UW_COL_NAMES)])))
    return rows


def format_result(result: dict) -> str:
    """
    Convert a run_scenario() result dict into a Markdown string.

    Args:
        result: Dict from scenario_runner.run_scenario()

    Returns:
        Multi-line Markdown report.
    """
    status_label = _STATUS_LABEL.get(result["overall_status"], result["overall_status"].upper())
    outcome_label = result.get("outcome", "unknown").replace("_", " ").title()

    lines: list[str] = [
        f"## Scenario Result — `{result['tc_id']}`",
        "",
        f"| | |",
        f"|---|---|",
        f"| **Status** | {status_label} |",
        f"| **Outcome** | {outcome_label} |",
        f"| **Total duration** | {result['total_duration_s']}s |",
    ]

    if result.get("description"):
        lines.append(f"| **Description** | {result['description']} |")

    lines += ["", "---", "", "### Steps", ""]

    # Step table
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

    # UW conditions section
    if result.get("uw_conditions"):
        lines += ["", "---", "", "### UW Conditions Triggered", ""]
        rows = _parse_uw_rows(result["uw_conditions"])
        if rows:
            lines += [
                "| Type | Condition |",
                "|------|-----------|",
            ]
            for row in rows:
                lines.append(f"| {row.get('Type', '')} | {row.get('Condition', '')} |")
        else:
            # Fallback: dump raw cells as a bullet list
            for cell in result["uw_conditions"]:
                if cell:
                    lines.append(f"- {cell}")

    # Error section
    if result.get("error"):
        lines += ["", "---", "", "### Error", "", "```", result["error"].strip(), "```"]

    # Screenshot
    if result.get("screenshot_path"):
        lines += [
            "",
            f"> **Failure screenshot saved to:** `{result['screenshot_path']}`",
        ]

    return "\n".join(lines)
