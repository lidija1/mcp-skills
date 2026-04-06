"""
Markdown report generator for accessibility audit results.
"""

from __future__ import annotations

from .engine import CRITICAL, INFO, WARNING, AccessibilityIssue, AuditReport, HeadingNode

# ---------------------------------------------------------------------------
# Emoji / badge per severity
# ---------------------------------------------------------------------------

_SEV_BADGE = {
    CRITICAL: "🔴 CRITICAL",
    WARNING:  "🟡 WARNING",
    INFO:     "🔵 INFO",
}

_CHECK_LABEL = {
    "alt_text":      "Image Alt Text",
    "form_labels":   "Form Labels",
    "heading_order": "Heading Order",
    "keyboard":      "Keyboard Navigation",
    "aria":          "ARIA / Landmarks",
    "page_meta":     "Page Metadata",
}


# ---------------------------------------------------------------------------
# Public formatters
# ---------------------------------------------------------------------------

def format_full_report(report: AuditReport) -> str:
    """Render a complete accessibility audit as Markdown."""
    lines: list[str] = []

    # ── Header ──────────────────────────────────────────────────────────────
    lines += [
        "# Accessibility Audit Report",
        "",
        f"**URL:** {report.url}  ",
        f"**Page title:** {report.title or '(missing)'}  ",
        f"**Language:** {report.language or '(missing)'}  ",
        "",
        "## Summary",
        "",
        f"| Severity | Count |",
        f"|----------|-------|",
        f"| 🔴 Critical | {report.critical_count} |",
        f"| 🟡 Warning  | {report.warning_count} |",
        f"| 🔵 Info     | {report.info_count} |",
        f"| **Total**   | **{len(report.issues)}** |",
        "",
    ]

    if not report.issues:
        lines += [
            "✅ **No accessibility issues detected.**",
            "",
        ]
    else:
        lines += _format_issues_by_category(report.issues)

    lines += _format_heading_structure(report.headings)
    lines += _format_aria_snapshot(report.aria_snapshot)

    return "\n".join(lines)


def format_category_report(
    check: str,
    issues: list[AccessibilityIssue],
    url: str,
) -> str:
    """Render issues for a single check category as Markdown."""
    label = _CHECK_LABEL.get(check, check)
    lines: list[str] = [
        f"# {label} — Accessibility Check",
        "",
        f"**URL:** {url}",
        f"**Issues found:** {len(issues)}",
        "",
    ]

    if not issues:
        lines += [f"✅ No {label.lower()} issues detected.", ""]
        return "\n".join(lines)

    for i, issue in enumerate(issues, 1):
        lines += _format_single_issue(i, issue)

    return "\n".join(lines)


def format_heading_tree(headings: list[HeadingNode], url: str) -> str:
    """Render the heading outline as an indented tree."""
    lines: list[str] = [
        "# Heading Structure",
        "",
        f"**URL:** {url}",
        f"**Total headings:** {len(headings)}",
        "",
    ]
    if not headings:
        lines += ["*(no headings found)*", ""]
        return "\n".join(lines)

    lines.append("```")
    for h in headings:
        indent = "  " * (h.level - 1)
        marker = "#" * h.level
        lines.append(f"{indent}{marker} {h.text[:100]}")
    lines += ["```", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_issues_by_category(issues: list[AccessibilityIssue]) -> list[str]:
    """Group issues by check category and render each group."""
    grouped: dict[str, list[AccessibilityIssue]] = {}
    for issue in issues:
        grouped.setdefault(issue.check, []).append(issue)

    lines: list[str] = ["## Issues by Category", ""]
    for check, group in grouped.items():
        label = _CHECK_LABEL.get(check, check)
        lines += [f"### {label} ({len(group)} issue{'s' if len(group) != 1 else ''})", ""]
        for i, issue in enumerate(group, 1):
            lines += _format_single_issue(i, issue)

    return lines


def _format_single_issue(index: int, issue: AccessibilityIssue) -> list[str]:
    badge = _SEV_BADGE.get(issue.severity, issue.severity.upper())
    lines = [
        f"#### {index}. {badge}",
        "",
        f"**Issue:** {issue.description}",
        "",
        f"**Suggestion:** {issue.suggestion}",
        "",
    ]
    if issue.element and issue.element.strip():
        truncated = issue.element[:300]
        lines += [
            f"<details><summary>Element snippet</summary>",
            "",
            f"```html",
            truncated,
            "```",
            "",
            "</details>",
            "",
        ]
    return lines


def _format_heading_structure(headings: list[HeadingNode]) -> list[str]:
    if not headings:
        return ["## Heading Structure", "", "*(no headings found)*", ""]
    lines = ["## Heading Structure", "", "```"]
    for h in headings:
        indent = "  " * (h.level - 1)
        marker = "#" * h.level
        lines.append(f"{indent}{marker} {h.text[:100]}")
    lines += ["```", ""]
    return lines


def _format_aria_snapshot(snapshot: str) -> list[str]:
    if not snapshot:
        return []
    lines = [
        "## Accessibility Tree Snapshot",
        "",
        "*(Playwright accessibility tree — interesting nodes only)*",
        "",
        "<details><summary>Expand accessibility tree</summary>",
        "",
        "```",
    ]
    # Limit to first 200 lines to avoid very large outputs
    tree_lines = snapshot.splitlines()
    lines.extend(tree_lines[:200])
    if len(tree_lines) > 200:
        lines.append(f"… ({len(tree_lines) - 200} more lines omitted)")
    lines += ["```", "", "</details>", ""]
    return lines
