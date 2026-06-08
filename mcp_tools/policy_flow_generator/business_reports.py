"""Business-facing report helpers for policy flow MCP tools."""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
POLICY_SUMMARY_DIR = PROJECT_ROOT / "policy_summary"

LOB_REPORT_FILES = {
    "auto": "policy_reports_personal_auto.csv",
    "personal auto": "policy_reports_personal_auto.csv",
    "homeowner": "policy_reports_homeowner.csv",
    "homeowners": "policy_reports_homeowner.csv",
}

IMPORTANT_FIELDS = [
    "Policy Number",
    "Program",
    "Customer Name",
    "Status",
    "Total Policy Premium",
    "Payment Plan",
    "Payment Method",
    "Primary Jurisdiction",
    "Policy Coverage Option",
    "Vehicle Year",
    "Vehicle Make",
    "Vehicle Model",
    "Vehicle Use",
    "Ownership",
]


def summarize_policy_from_reports(
    lob: str = "",
    policy_number: str = "",
    customer_name: str = "",
    query: str = "",
    latest: bool = True,
) -> str:
    """Find a saved policy summary row and return a compact Markdown summary."""
    policy_number = policy_number or _extract_policy_number(query)
    customer_name = customer_name or _extract_customer_name(query)
    rows = _load_candidate_rows(lob)

    matches = []
    for row in rows:
        if policy_number and row.get("Policy Number", "").lower() != policy_number.lower():
            continue
        if customer_name and customer_name.lower() not in row.get("Customer Name", "").lower():
            continue
        matches.append(row)

    if not matches:
        searched = []
        if lob:
            searched.append(f"lob={lob}")
        if policy_number:
            searched.append(f"policy_number={policy_number}")
        if customer_name:
            searched.append(f"customer_name={customer_name}")
        if query:
            searched.append(f"query={query}")
        criteria = ", ".join(searched) or "latest saved policy"
        return f"**No saved policy summary found** for {criteria}."

    row = matches[-1] if latest else matches[0]
    return format_policy_summary(row)


def format_policy_summary(row: dict[str, str]) -> str:
    """Format one policy-summary CSV row for BA/customer-facing use."""
    title = row.get("Policy Number") or "Policy Summary"
    lines = [f"## Policy Summary - `{title}`", "", "| Field | Value |", "|---|---|"]

    used = set()
    for field in IMPORTANT_FIELDS:
        value = row.get(field)
        if value:
            lines.append(f"| {field} | {value} |")
            used.add(field)

    extra_fields = [
        key for key in row
        if key not in used and key != "Timestamp" and row.get(key)
    ]
    if extra_fields:
        lines += ["", "### Additional Fields", "", "| Field | Value |", "|---|---|"]
        for field in extra_fields:
            lines.append(f"| {field} | {row[field]} |")

    if row.get("Timestamp"):
        lines += ["", f"_Saved from live run at {row['Timestamp']}._"]
    return "\n".join(lines)


def format_scenario_comparison(results: list[dict[str, Any]]) -> str:
    """Return a compact comparison report for live scenario results."""
    if not results:
        return "**No scenario results to compare.**"

    lines = [
        "## Scenario Comparison",
        "",
        "| # | Scenario | LOB | Outcome | Policy | Premium | UW / Error | Duration |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for index, result in enumerate(results, 1):
        summary = result.get("policy_summary") or {}
        outcome = str(result.get("outcome", "error")).replace("_", " ").title()
        lob = str(result.get("lob", "")).title()
        scenario = _escape_table(result.get("persona_type") or result.get("description") or "custom")
        policy = summary.get("Policy Number") or ""
        premium = summary.get("Total Policy Premium") or result.get("premium") or ""
        issue = _short_issue(result)
        duration = f"{result.get('total_duration_s', 0)}s"
        lines.append(
            f"| {index} | {scenario} | {lob} | {outcome} | {policy} | "
            f"{premium} | {issue} | {duration} |"
        )

    lines += ["", "### Bound Policy Details"]
    bound_rows = [
        result.get("policy_summary") for result in results
        if result.get("policy_summary") and result.get("outcome") == "policy_bound"
    ]
    if not bound_rows:
        lines.append("")
        lines.append("_No bound policy summaries were captured._")
    else:
        for row in bound_rows:
            lines += ["", format_policy_summary(row)]

    return "\n".join(lines)


def _load_candidate_rows(lob: str) -> list[dict[str, str]]:
    files = []
    normalized_lob = lob.lower().strip()
    if normalized_lob:
        file_name = LOB_REPORT_FILES.get(normalized_lob)
        if file_name:
            files = [POLICY_SUMMARY_DIR / file_name]
        else:
            return []
    else:
        files = sorted(POLICY_SUMMARY_DIR.glob("policy_reports*.csv"))

    rows: list[dict[str, str]] = []
    for path in files:
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            rows.extend(csv.DictReader(handle))
    return rows


def _extract_policy_number(query: str) -> str:
    match = re.search(r"\b[A-Z]{2,4}\d{8,}-\d{2}\b", query or "", re.I)
    return match.group(0) if match else ""


def _extract_customer_name(query: str) -> str:
    match = re.search(r"(?:customer|insured|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", query or "")
    return match.group(1) if match else ""


def _short_issue(result: dict[str, Any]) -> str:
    if result.get("uw_conditions"):
        cells = [cell for cell in result["uw_conditions"] if cell]
        return _escape_table("; ".join(cells[:2]))
    if result.get("error"):
        first_line = str(result["error"]).strip().splitlines()[-1]
        return _escape_table(first_line[:120])
    return ""


def _escape_table(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")
