"""Markdown report formatters for OneShield QA MCP tools."""

from __future__ import annotations

from typing import Any


def _grid_row_texts(ui_data: dict[str, Any]) -> list[str]:
    return [
        " | ".join(str(v) for v in row.values())
        for grid in ui_data.get("grids", [])
        for row in grid.get("rows", [])
    ]


def format_uw_api_report(
    tc_id: str,
    test_data: dict[str, Any],
    result: dict[str, Any],
    expected_conditions: list[str],
) -> str:
    rate_ui = result.get("stage_ui_data", {}).get("rate", result.get("ui_data", {}))
    row_texts = _grid_row_texts(rate_ui)

    findings = []
    for cond in expected_conditions:
        found = any("Underwriting" in row and cond in row for row in row_texts)
        findings.append({"condition": cond, "found": found})

    all_pass = (
        result.get("completed", False)
        and not result.get("blocked_reason")
        and all(f["found"] for f in findings)
    )
    icon = "✅" if all_pass else "❌"
    overall = "PASS" if all_pass else "FAIL"

    lines = [
        f"# UW API Test — {tc_id} — {icon} {overall}",
        "",
        f"**Completed:** `{result.get('completed')}`  ",
        f"**Page:** `{rate_ui.get('page_name', '')}`  ",
        f"**Blocked:** {result.get('blocked_reason') or 'none'}",
        "",
        "## Expected Condition Assertions",
        "",
        "| Condition | Found |",
        "|-----------|-------|",
    ]
    for f in findings:
        icon_f = "✅" if f["found"] else "❌"
        lines.append(f"| `{f['condition']}` | {icon_f} |")

    if row_texts:
        lines += ["", "## UW Grid Rows", ""]
        for row in row_texts:
            lines.append(f"- {row}")

    if result.get("blocked_reason"):
        lines += ["", f"**Blocked reason:** {result['blocked_reason']}"]

    if rate_ui.get("messages"):
        lines += ["", "**Messages:** " + "; ".join(rate_ui["messages"])]

    return "\n".join(lines)


def format_uw_batch_report(results: list[dict[str, Any]]) -> str:
    pass_count = sum(1 for r in results if r.get("passed"))
    total = len(results)
    verdict = "✅ ALL PASS" if pass_count == total else f"❌ {total - pass_count} FAIL"

    lines = [
        f"# UW API Batch — {pass_count}/{total} PASS — {verdict}",
        "",
        "| TC_ID | Status | Expected Conditions | Page |",
        "|-------|--------|---------------------|------|",
    ]
    for r in results:
        if r.get("error"):
            lines.append(f"| `{r['tc_id']}` | ❌ ERROR | — | {r['error'][:80]} |")
            continue
        icon = "✅" if r["passed"] else "❌"
        status = "PASS" if r["passed"] else "FAIL"
        flow = r.get("result", {})
        page = flow.get("stage_ui_data", {}).get("rate", {}).get("page_name", "")
        conds = " / ".join(f"`{c}`" for c in r.get("expected", []))
        lines.append(f"| `{r['tc_id']}` | {icon} {status} | {conds} | {page} |")

    fail_results = [r for r in results if not r.get("passed") and not r.get("error")]
    if fail_results:
        lines += ["", f"## Failures ({len(fail_results)})", ""]
        for r in fail_results:
            flow = r.get("result", {})
            ui = flow.get("stage_ui_data", {}).get("rate", flow.get("ui_data", {}))
            row_texts = _grid_row_texts(ui)
            lines.append(f"### {r['tc_id']}")
            for cond in r.get("expected", []):
                found = any("Underwriting" in row and cond in row for row in row_texts)
                if not found:
                    lines.append(f"- ❌ Missing: `{cond}`")
            if flow.get("blocked_reason"):
                lines.append(f"- Blocked: {flow['blocked_reason']}")
            lines.append("")

    return "\n".join(lines)


def format_assertion_report(
    tc_id: str,
    stage: str,
    ui_data: dict[str, Any],
    assertions: dict[str, Any],
    result: dict[str, Any],
) -> str:
    field_values = ui_data.get("field_values", {})
    findings = []

    for key, expected in assertions.items():
        if key == "page_name_contains":
            actual = ui_data.get("page_name", "")
            passed = str(expected).lower() in actual.lower()
            findings.append({"key": "page_name", "expected": expected, "actual": actual, "passed": passed})
        elif key == "has_action":
            actions = ui_data.get("actions", [])
            passed = any(str(expected).lower() in a.lower() for a in actions)
            findings.append({"key": "action button", "expected": expected, "actual": ", ".join(actions), "passed": passed})
        elif key == "no_messages":
            messages = ui_data.get("messages", [])
            passed = len(messages) == 0
            findings.append({"key": "no_messages", "expected": "empty", "actual": str(messages), "passed": passed})
        else:
            actual_values = field_values.get(key, [])
            actual_str = ", ".join(str(v) for v in actual_values) if actual_values else "(not found)"
            passed = bool(actual_values) and any(str(expected) in str(v) for v in actual_values)
            findings.append({"key": key, "expected": expected, "actual": actual_str, "passed": passed})

    all_pass = bool(findings) and all(f["passed"] for f in findings)
    icon = "✅" if all_pass else "❌"
    overall = "PASS" if all_pass else "FAIL"

    lines = [
        f"# Stage Validation — {tc_id} @ {stage} — {icon} {overall}",
        "",
        f"**Page:** `{ui_data.get('page_name', '')}`  ",
        f"**Completed:** `{result.get('completed')}`  ",
        f"**Blocked:** {result.get('blocked_reason') or 'none'}",
        "",
        "## Assertions",
        "",
        "| Field | Expected | Actual | Result |",
        "|-------|----------|--------|--------|",
    ]
    for f in findings:
        icon_f = "✅" if f["passed"] else "❌"
        lines.append(
            f"| `{f['key']}` | `{f['expected']}` | `{str(f['actual'])[:80]}` | {icon_f} |"
        )

    if not findings:
        lines.append("| — | — | — | No assertions provided |")

    return "\n".join(lines)


def format_state_dump(
    tc_id: str,
    stage: str,
    ui_data: dict[str, Any],
    result: dict[str, Any],
) -> str:
    lines = [
        f"# App State — {tc_id} @ {stage}",
        "",
        f"**Page:** `{ui_data.get('page_name', 'unknown')}`  ",
        f"**Completed:** `{result.get('completed')}`  ",
        f"**Blocked:** {result.get('blocked_reason') or 'none'}",
        "",
    ]

    if ui_data.get("messages"):
        lines += ["## Messages", ""]
        for msg in ui_data["messages"]:
            lines.append(f"- {msg}")
        lines.append("")

    if ui_data.get("actions"):
        lines.append(f"**Actions:** {', '.join(f'`{a}`' for a in ui_data['actions'])}")
        lines.append("")

    if ui_data.get("tabs"):
        lines.append(f"**Tabs:** {', '.join(f'`{t}`' for t in ui_data['tabs'])}")
        lines.append("")

    fields = ui_data.get("fields", [])
    if fields:
        lines += ["## Fields", "", "| Block | Label | Value | R/O |", "|-------|-------|-------|-----|"]
        for f in fields:
            ro = "Yes" if f.get("read_only") else ""
            display = str(f.get("display_value") or f.get("value", ""))[:60]
            lines.append(f"| {f.get('block', '')} | {f['label']} | `{display}` | {ro} |")
        lines.append("")

    for grid in ui_data.get("grids", []):
        label = grid.get("label") or "Grid"
        lines += [f"## Grid: {label}", ""]
        cols = [c["label"] for c in grid.get("columns", []) if c.get("label")]
        if cols and grid.get("rows"):
            lines.append("| " + " | ".join(cols) + " |")
            lines.append("|" + "|".join("---" for _ in cols) + "|")
            for row in grid.get("rows", []):
                values = [str(row.get(col, ""))[:50] for col in cols]
                lines.append("| " + " | ".join(values) + " |")
        elif not grid.get("rows"):
            lines.append("_(no rows)_")
        lines.append("")

    return "\n".join(lines)
