"""
UW Rules Validator — compares actual flow results against expected outcomes.

Acts like a strict underwriter: any deviation from the expected behaviour
is a finding. Severity reflects real-world risk of the inconsistency.

Finding types
─────────────
  FALSE_APPROVE    🔴 CRITICAL — expected UW referral, got policy bound.
                   A risky profile was approved without underwriting review.

  FALSE_REFER      🟡 WARNING  — expected policy bound, got UW referral.
                   An acceptable profile was unnecessarily flagged.

  MISSING_CONDITION 🟠 HIGH    — UW referral fired but expected condition
                   text not found in the referral grid.
                   Right outcome, wrong/incomplete rule displayed.

  WRONG_COUNT      🟡 WARNING  — fewer UW condition rows than expected.
                   Some rules may have silently stopped firing.

  EXTRA_CONDITIONS ℹ️  INFO    — more conditions than expected.
                   Possibly a new rule firing on this profile.

  FLOW_ERROR       🔴 CRITICAL — the browser flow failed before a decision
                   could be reached. Result is indeterminate.

  PASS             ✅          — all checks passed.
"""

from __future__ import annotations

_UW_COL_COUNT = 5   # Asset | Condition | Type | Comments | Overridden?
_CONDITION_IDX = 1  # "Condition" is the second column (0-indexed)


# ---------------------------------------------------------------------------
# Condition parsing helpers
# ---------------------------------------------------------------------------

def _parse_condition_rows(raw_cells: list[str]) -> list[dict]:
    """Group flat gridcell list into structured rows (5 columns each)."""
    col_names = ["Asset", "Condition", "Type", "Comments", "Overridden?"]
    if not raw_cells or len(raw_cells) % _UW_COL_COUNT != 0:
        return []
    rows = []
    for i in range(0, len(raw_cells), _UW_COL_COUNT):
        rows.append(dict(zip(col_names, raw_cells[i: i + _UW_COL_COUNT])))
    return rows


def _condition_text_found(expected: str, raw_cells: list[str]) -> bool:
    """
    Return True if `expected` is a case-sensitive substring of ANY gridcell text.
    Mirrors UWReferralPage.assert_uw_condition logic.
    """
    return any(expected in cell for cell in raw_cells)


# ---------------------------------------------------------------------------
# Core validation function
# ---------------------------------------------------------------------------

def validate_case(rule_case: dict, flow_result: dict) -> list[dict]:
    """
    Compare actual flow_result against the rule_case expectations.

    Args:
        rule_case:   A case dict from rule_registry.RULE_CASES
        flow_result: Result dict from flow_runner.run_flow()

    Returns:
        List of finding dicts, each with keys:
          type, severity, message, case_id, rule_id, rule_name
    """
    findings = []

    def _finding(ftype: str, severity: str, message: str) -> dict:
        return {
            "type": ftype,
            "severity": severity,
            "message": message,
            "case_id": rule_case["case_id"],
            "rule_id": rule_case["rule_id"],
            "rule_name": rule_case["rule_name"],
            "lob": rule_case["lob"],
            "case_type": rule_case["case_type"],
            "description": rule_case["description"],
            "expected_outcome": rule_case["expected_outcome"],
            "actual_outcome": flow_result.get("outcome", "error"),
            "duration_s": flow_result.get("total_duration_s", 0),
        }

    # ── FLOW_ERROR ──────────────────────────────────────────────────────────
    if flow_result.get("outcome") == "error" or flow_result.get("error"):
        findings.append(_finding(
            "FLOW_ERROR", "critical",
            f"Browser flow failed before a decision was reached. "
            f"Error: {str(flow_result.get('error', ''))[:200]}",
        ))
        return findings

    expected = rule_case["expected_outcome"]
    actual = flow_result.get("outcome")
    raw_cells = flow_result.get("uw_conditions", [])
    expected_conditions = rule_case.get("expected_conditions", [])
    min_conditions = rule_case.get("min_conditions")

    # ── Outcome mismatch ────────────────────────────────────────────────────
    if expected == "uw_referral" and actual != "uw_referral":
        findings.append(_finding(
            "FALSE_APPROVE", "critical",
            f"Rule engine FAILED to flag this profile. "
            f"Expected UW referral but policy was BOUND. "
            f"A risky profile was approved without underwriting review.",
        ))
        return findings  # No point checking conditions if outcome is wrong

    if expected == "policy_bound" and actual != "policy_bound":
        findings.append(_finding(
            "FALSE_REFER", "warning",
            f"Rule engine over-triggered on a clean profile. "
            f"Expected policy to bind but UW referral was raised instead. "
            f"Conditions found: {raw_cells[:10]}",
        ))
        return findings

    # ── Outcome matched — now check condition text (for UW referrals) ───────
    if actual == "uw_referral":

        for expected_text in expected_conditions:
            if not _condition_text_found(expected_text, raw_cells):
                findings.append(_finding(
                    "MISSING_CONDITION", "high",
                    f"UW referral fired but expected condition not found in grid. "
                    f"Missing: \"{expected_text}\"  "
                    f"Actual gridcells: {raw_cells}",
                ))

        # Count check
        if min_conditions is not None:
            condition_rows = _parse_condition_rows(raw_cells)
            actual_count = len(condition_rows) if condition_rows else max(1, len(raw_cells) // _UW_COL_COUNT)
            if actual_count < min_conditions:
                findings.append(_finding(
                    "WRONG_COUNT", "warning",
                    f"Expected at least {min_conditions} UW condition row(s) "
                    f"but found {actual_count}. Some rules may have stopped firing.",
                ))
            elif actual_count > (min_conditions or 0) + 2:
                findings.append(_finding(
                    "EXTRA_CONDITIONS", "info",
                    f"Found {actual_count} UW condition rows, expected ~{min_conditions}. "
                    f"Additional rules may be firing on this profile.",
                ))

    # ── All checks passed ───────────────────────────────────────────────────
    if not findings:
        findings.append(_finding(
            "PASS", "pass",
            f"All checks passed. Outcome={actual}, "
            f"conditions validated={len(expected_conditions)}.",
        ))

    return findings


# ---------------------------------------------------------------------------
# Aggregate helpers
# ---------------------------------------------------------------------------

_SEVERITY_ORDER = {"critical": 0, "high": 1, "warning": 2, "info": 3, "pass": 4}


def severity_sort_key(finding: dict) -> int:
    return _SEVERITY_ORDER.get(finding["severity"], 99)


def summarise_findings(all_findings: list[dict]) -> dict:
    """
    Build a summary dict from a flat list of findings across multiple cases.

    Returns:
        {
          "total_cases": int,
          "passed": int,
          "critical": int,
          "high": int,
          "warning": int,
          "info": int,
          "by_type": {type: count},
          "false_approvals": [finding, ...]   # most dangerous — listed separately
        }
    """
    counts = {"critical": 0, "high": 0, "warning": 0, "info": 0, "pass": 0}
    by_type: dict[str, int] = {}
    false_approvals = []
    case_ids_seen: set = set()

    for f in all_findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
        by_type[f["type"]] = by_type.get(f["type"], 0) + 1
        case_ids_seen.add(f["case_id"])
        if f["type"] == "FALSE_APPROVE":
            false_approvals.append(f)

    return {
        "total_cases": len(case_ids_seen),
        "passed": counts["pass"],
        "critical": counts["critical"],
        "high": counts["high"],
        "warning": counts["warning"],
        "info": counts["info"],
        "by_type": by_type,
        "false_approvals": false_approvals,
    }
