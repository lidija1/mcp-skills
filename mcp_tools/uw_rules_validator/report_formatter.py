"""
Report formatter — produces strict-underwriter-style Markdown reports.

Tone: authoritative, zero patience for inconsistencies. Every finding is
named precisely. Critical violations are called out first and loudly.
"""

from __future__ import annotations

from mcp_tools.uw_rules_validator.validator import summarise_findings, severity_sort_key

_LOB_LABEL = {"auto": "Personal Auto", "homeowner": "Homeowner"}

_SEVERITY_ICON = {
    "critical": "🔴",
    "high":     "🟠",
    "warning":  "🟡",
    "info":     "ℹ️",
    "pass":     "✅",
}

_TYPE_LABEL = {
    "FALSE_APPROVE":     "FALSE APPROVE — Rule engine missed a risk",
    "FALSE_REFER":       "FALSE REFER — Rule engine over-triggered on clean profile",
    "MISSING_CONDITION": "MISSING CONDITION — Wrong/incomplete rule displayed",
    "WRONG_COUNT":       "WRONG COUNT — Fewer conditions than expected",
    "EXTRA_CONDITIONS":  "EXTRA CONDITIONS — Unexpected additional rules fired",
    "FLOW_ERROR":        "FLOW ERROR — Browser flow failed before decision",
    "PASS":              "PASS",
}

_CASE_TYPE_LABEL = {
    "positive": "Should trigger UW",
    "negative": "Should bind (no UW)",
    "boundary": "Boundary edge case",
}


# ---------------------------------------------------------------------------
# Single-case finding block
# ---------------------------------------------------------------------------

def _finding_block(finding: dict) -> str:
    icon = _SEVERITY_ICON.get(finding["severity"], "?")
    label = _TYPE_LABEL.get(finding["type"], finding["type"])
    sev = finding["severity"].upper()
    case_type = _CASE_TYPE_LABEL.get(finding.get("case_type", ""), "")

    if finding["type"] == "PASS":
        return (
            f"| ✅ | `{finding['case_id']}` | {finding.get('description', '')} "
            f"| {finding.get('actual_outcome', '').replace('_', ' ').title()} | — |"
        )

    lines = [
        f"",
        f"#### {icon} {sev}: {label}",
        f"",
        f"| | |",
        f"|---|---|",
        f"| **Case ID** | `{finding['case_id']}` |",
        f"| **Rule** | {finding['rule_name']} |",
        f"| **Case Type** | {case_type} |",
        f"| **Description** | {finding.get('description', '')} |",
        f"| **Expected** | {finding.get('expected_outcome', '').replace('_', ' ').title()} |",
        f"| **Actual** | {finding.get('actual_outcome', '').replace('_', ' ').title()} |",
        f"| **Duration** | {finding.get('duration_s', 0)}s |",
        f"",
        f"> {finding['message']}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Full audit report
# ---------------------------------------------------------------------------

def format_audit_report(
    lob: str,
    all_findings: list[dict],
    rule_filter: str | None = None,
    custom_label: str | None = None,
) -> str:
    """
    Produce a Markdown audit report from a list of findings.

    Args:
        lob:          "auto", "homeowner", or "all"
        all_findings: Flat list of finding dicts from validate_case()
        rule_filter:  Optional rule_id — shown when auditing a single rule
        custom_label: Optional label override for the report heading
    """
    lob_label = _LOB_LABEL.get(lob, lob.upper()) if lob != "all" else "All LOBs"
    heading = custom_label or f"UW Rules Audit — {lob_label}"
    if rule_filter:
        heading += f" / Rule: `{rule_filter}`"

    summary = summarise_findings(all_findings)
    total = summary["total_cases"]
    passed = summary["passed"]
    critical = summary["critical"]
    high = summary["high"]
    warning = summary["warning"]
    info = summary["info"]

    # ── Verdict line ────────────────────────────────────────────────────────
    if critical > 0:
        verdict = "🔴 **AUDIT FAILED — CRITICAL VIOLATIONS PRESENT**"
    elif high > 0:
        verdict = "🟠 **AUDIT FAILED — HIGH SEVERITY ISSUES FOUND**"
    elif warning > 0:
        verdict = "🟡 **AUDIT PASSED WITH WARNINGS**"
    else:
        verdict = "✅ **AUDIT CLEAN — ALL RULES BEHAVING AS EXPECTED**"

    lines = [
        f"## 🔍 {heading}",
        "",
        verdict,
        "",
        "### Summary",
        "",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Total cases run | {total} |",
        f"| ✅ Passed | {passed} |",
        f"| 🔴 Critical violations | {critical} |",
        f"| 🟠 High severity | {high} |",
        f"| 🟡 Warnings | {warning} |",
        f"| ℹ️ Informational | {info} |",
    ]

    # Finding type breakdown
    if summary["by_type"]:
        lines += ["", "**By finding type:**", ""]
        for ftype, count in sorted(summary["by_type"].items()):
            icon = _SEVERITY_ICON.get("critical" if "APPROVE" in ftype or "ERROR" in ftype else
                                       "high" if "MISSING" in ftype else
                                       "warning" if ftype in ("FALSE_REFER", "WRONG_COUNT") else
                                       "info" if "EXTRA" in ftype else "pass", "")
            lines.append(f"- {icon} `{ftype}`: {count}")

    # ── False Approvals callout (most dangerous) ─────────────────────────────
    if summary["false_approvals"]:
        lines += [
            "",
            "---",
            "",
            "### 🚨 FALSE APPROVALS — IMMEDIATE ACTION REQUIRED",
            "",
            ("> These profiles should have triggered an underwriting referral but were "
             "approved without review. This is the most dangerous class of rule engine failure."),
            "",
        ]
        for fa in summary["false_approvals"]:
            lines.append(
                f"- `{fa['case_id']}` — **{fa['rule_name']}** | "
                f"Profile: _{fa.get('description', '')}_ | "
                f"Duration: {fa.get('duration_s', 0)}s"
            )

    # ── All findings (sorted by severity, then case_id) ─────────────────────
    non_pass = [f for f in all_findings if f["type"] != "PASS"]
    pass_findings = [f for f in all_findings if f["type"] == "PASS"]

    if non_pass:
        lines += ["", "---", "", "### Violations & Warnings", ""]
        for finding in sorted(non_pass, key=severity_sort_key):
            lines.append(_finding_block(finding))

    # ── Pass table ───────────────────────────────────────────────────────────
    if pass_findings:
        lines += [
            "",
            "---",
            "",
            "### ✅ Passed Cases",
            "",
            "| | Case ID | Description | Outcome | Conditions |",
            "|---|---------|-------------|---------|------------|",
        ]
        for f in pass_findings:
            lines.append(
                f"| ✅ | `{f['case_id']}` | {f.get('description', '')[:80]} "
                f"| {f.get('actual_outcome', '').replace('_', ' ').title()} "
                f"| {f['message'].split('conditions validated=')[-1] if 'validated' in f.get('message','') else '—'} |"
            )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Custom boundary test report (single case)
# ---------------------------------------------------------------------------

def format_boundary_report(
    lob: str,
    description: str,
    expected_outcome: str,
    expected_conditions: list[str],
    flow_result: dict,
    findings: list[dict],
) -> str:
    """Compact report for a single custom boundary test."""
    lob_label = _LOB_LABEL.get(lob, lob.upper())
    actual = flow_result.get("outcome", "error")
    duration = flow_result.get("total_duration_s", 0)
    all_pass = all(f["type"] == "PASS" for f in findings)

    verdict = "✅ PASS" if all_pass else "❌ FAIL"
    lines = [
        f"## 🔍 Custom Boundary Test — {lob_label}",
        "",
        f"| | |",
        f"|---|---|",
        f"| **Verdict** | {verdict} |",
        f"| **Description** | {description} |",
        f"| **Expected Outcome** | {expected_outcome.replace('_', ' ').title()} |",
        f"| **Actual Outcome** | {actual.replace('_', ' ').title()} |",
        f"| **Expected Conditions** | {', '.join(f'\"{c}\"' for c in expected_conditions) or '(none)'} |",
        f"| **Duration** | {duration}s |",
        "",
    ]

    if flow_result.get("uw_conditions"):
        lines += ["**UW Conditions captured:**", ""]
        for cell in flow_result["uw_conditions"]:
            if cell:
                lines.append(f"- {cell}")
        lines.append("")

    if not all_pass:
        lines += ["### Findings", ""]
        for f in sorted(findings, key=severity_sort_key):
            if f["type"] != "PASS":
                icon = _SEVERITY_ICON.get(f["severity"], "?")
                label = _TYPE_LABEL.get(f["type"], f["type"])
                lines.append(f"**{icon} {f['severity'].upper()}: {label}**")
                lines.append(f"> {f['message']}")
                lines.append("")

    if flow_result.get("screenshot_path"):
        lines.append(f"> **Failure screenshot:** `{flow_result['screenshot_path']}`")

    return "\n".join(lines)
