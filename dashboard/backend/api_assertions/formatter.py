"""Compact markdown formatter for plain-English UW test assertion reports."""

from __future__ import annotations

from dashboard.backend.api_assertions.schemas import ApiAssertionRunResult


def format_api_assertion_report(result: ApiAssertionRunResult) -> str:
    status = "PASS" if result.passed else "FAIL"
    flow = result.flow_result
    primary = result.findings[0] if result.findings else None
    lines = [
        f"# UW Test Result - {status}",
        "",
        f"**Status:** {status}",
        "",
        "**Prompt:**",
        "",
        "```text",
        result.spec.prompt,
        "```",
        "",
        f"**Check:** {_plain(_check_label(primary))}",
        f"**Expected:** {_plain(primary.expected if primary else '')}",
        f"**Actual:** {_plain(primary.actual if primary else '')}",
        f"**Page:** {_plain(flow.get('last_page', ''))}",
        "",
        "## Assertion Details",
        "",
    ]
    for finding in result.findings:
        finding_status = "PASS" if finding.passed else "FAIL"
        lines.extend(
            [
                f"- **{_plain(_check_label(finding))}:** {finding_status}",
                f"  - Expected: `{_plain(finding.expected)}`",
                f"  - Actual: `{_plain(finding.actual)}`",
            ]
        )
        if finding.message:
            lines.append(f"  - Note: {_plain(finding.message)}")

    blocked = flow.get("blocked_reason")
    if blocked:
        lines += ["", f"**Blocked:** {_plain(blocked)}"]

    return "\n".join(lines)


def _check_label(finding) -> str:
    if not finding:
        return ""
    labels = {
        "premium": "Premium",
        "coverage": "Coverage",
        "page_contains": "Page contains",
        "uw_condition_contains": "UW condition contains",
        "completed": "Flow completed",
        "field_value": "Field value",
        "uw_condition_absent": "UW condition absent",
        "uw_condition_count": "UW condition count",
        "action_available": "Action available",
        "flow_blocked": "Flow blocked",
        "premium_factor": "Rating factor",
    }
    operator = "" if finding.operator in ("exists", "equals") else f" {finding.operator}"
    return f"{labels.get(finding.type, finding.type)}{operator}"


def _plain(value) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|")
