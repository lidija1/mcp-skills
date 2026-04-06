"""
Markdown report generator for FormIntelligenceEngine results.
"""

from __future__ import annotations

from .engine import FieldInfo, FieldProbeReport, FieldResult, ProbeReport

# Category display labels
_CAT_ICON = {
    "empty":     "[  ]",
    "valid":     "[OK]",
    "malformed": "[!!]",
    "boundary":  "[~~]",
    "injection": "[>>]",
}


# ---------------------------------------------------------------------------
# Public formatters
# ---------------------------------------------------------------------------

def format_analysis(fields: list[FieldInfo]) -> str:
    """Render a structural field analysis as Markdown."""
    lines = [
        "# Form Field Analysis",
        "",
        f"**{len(fields)} field(s) discovered**",
        "",
        "| # | Label | Type | Selector | Required | Constraints |",
        "|---|-------|------|----------|----------|-------------|",
    ]

    for i, fi in enumerate(fields, 1):
        constraints = _fmt_constraints(fi)
        label = fi.label or "(unlabelled)"
        lines.append(
            f"| {i} | {label} | `{fi.field_type}` | `{fi.selector}` "
            f"| {'yes' if fi.required else 'no'} | {constraints or '—'} |"
        )

    if any(fi.options for fi in fields):
        lines += ["", "## Select field options", ""]
        for fi in fields:
            if fi.options:
                opts = ", ".join(f"`{o}`" for o in fi.options[:20])
                suffix = f" … (+{len(fi.options) - 20} more)" if len(fi.options) > 20 else ""
                lines.append(f"- **{fi.label}**: {opts}{suffix}")

    return "\n".join(lines)


def format_probe(report: ProbeReport) -> str:
    """Render a full probe report as Markdown."""
    lines = [
        f"# Form Intelligence Report",
        f"",
        f"**URL:** {report.url}  ",
        f"**Fields probed:** {report.field_count}  ",
        f"**Total test cases run:** {report.test_count}  ",
        f"**Elapsed:** {report.elapsed_seconds:.1f}s",
        "",
    ]

    # ── Issue summary ──────────────────────────────────────────────────────
    if report.all_issues:
        lines += [
            f"## Issues Found ({len(report.all_issues)})",
            "",
        ]
        for issue in report.all_issues:
            lines.append(f"- {issue}")
        lines.append("")
    else:
        lines += [
            "## Issues Found",
            "",
            "_No clear validation gaps detected (all expectations matched)._",
            "",
        ]

    # ── Empty-submission results ───────────────────────────────────────────
    lines += [
        "## Empty Form Submission",
        "",
    ]
    if report.empty_submission_errors:
        lines.append(
            "Fields that surfaced errors when the form was submitted blank:"
        )
        lines.append("")
        for sel, msgs in report.empty_submission_errors.items():
            fi = _find_field(report, sel)
            label = fi.label if fi else sel
            for msg in msgs:
                lines.append(f"- **{label}** (`{sel}`): _{msg}_")
    else:
        lines.append(
            "_No validation errors were captured on empty submission "
            "(form may require a submit button selector to trigger JS validation)._"
        )
    lines.append("")

    # ── Per-field detail ───────────────────────────────────────────────────
    lines += ["## Per-Field Results", ""]

    for fr in report.field_reports:
        lines += _format_field_report(fr)

    return "\n".join(lines)


def format_field_probe(report: FieldProbeReport) -> str:
    """Render a single-field probe report."""
    lines = [
        f"# Field Probe: {report.field.label or report.field.selector}",
        f"",
        f"**Selector:** `{report.field.selector}`  ",
        f"**Type:** `{report.field.field_type}`  ",
        f"**Required:** {'yes' if report.field.required else 'no'}  ",
        f"**Constraints:** {_fmt_constraints(report.field) or '—'}",
        "",
    ]

    if report.issues:
        lines += ["## Issues", ""]
        for iss in report.issues:
            lines.append(f"- {iss}")
        lines.append("")

    lines += _format_field_report(report)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _format_field_report(fr: FieldProbeReport) -> list[str]:
    fi = fr.field
    label = fi.label or "(unlabelled)"
    lines = [
        f"### {label} (`{fi.field_type}` — `{fi.selector}`)",
        "",
    ]

    if fr.issues:
        for iss in fr.issues:
            lines.append(f"> [ISSUE]  {iss}")
        lines.append("")

    lines += [
        "| Category | Description | Value | Passed? | Errors |",
        "|----------|-------------|-------|---------|--------|",
    ]

    for r in fr.results:
        icon = _CAT_ICON.get(r.payload.category, "")
        cat = f"{icon} {r.payload.category}"
        val = _truncate(str(r.payload.value) if r.payload.value is not None else "_(empty)_", 40)
        passed = "PASS" if r.passed_client_validation else "FAIL"
        if r.error:
            passed = "ERR"
        errors = "; ".join(r.validation_messages[:2])
        if len(r.validation_messages) > 2:
            errors += f" (+{len(r.validation_messages) - 2} more)"
        errors = _truncate(errors, 60) if errors else "—"
        lines.append(
            f"| {cat} | {r.payload.description} | `{val}` | {passed} | {errors} |"
        )

    lines.append("")
    return lines


def _fmt_constraints(fi: FieldInfo) -> str:
    parts = []
    if fi.min_val is not None:
        parts.append(f"min={fi.min_val}")
    if fi.max_val is not None:
        parts.append(f"max={fi.max_val}")
    if fi.min_length is not None:
        parts.append(f"minlength={fi.min_length}")
    if fi.max_length is not None:
        parts.append(f"maxlength={fi.max_length}")
    if fi.pattern:
        parts.append(f"pattern=`{fi.pattern}`")
    if fi.required:
        parts.append("required")
    return ", ".join(parts)


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n - 1] + "…"


def _find_field(report: ProbeReport, selector: str) -> FieldInfo | None:
    for fr in report.field_reports:
        if fr.field.selector == selector:
            return fr.field
    return None
