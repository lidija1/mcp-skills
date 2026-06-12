"""Deterministic assertions over Sandbox replay results."""

from __future__ import annotations

import re
from typing import Any

from dashboard.backend.api_assertions.lob_config import get_lob_config
from dashboard.backend.api_assertions.schemas import ApiAssertion, AssertionFinding


def evaluate_assertions(
    assertions: list[ApiAssertion],
    persona: dict[str, Any],
    flow_result: dict[str, Any],
    lob: str = "auto",
) -> list[AssertionFinding]:
    cfg = get_lob_config(lob)
    return [_evaluate(assertion, persona, flow_result, cfg.uw_stage_key, cfg.premium_path) for assertion in assertions]


def _evaluate(
    assertion: ApiAssertion,
    persona: dict[str, Any],
    flow_result: dict[str, Any],
    uw_stage_key: str,
    premium_path: str,
) -> AssertionFinding:
    if assertion.type == "premium":
        actual = _premium_value(flow_result, premium_path)
        return _numeric_finding(assertion, actual)

    if assertion.type == "coverage":
        actual = persona.get("PolicyCoverage") or flow_result.get("summary", {}).get("Policy Coverage Option")
        return _string_finding(assertion, actual)

    if assertion.type == "page_contains":
        actual = flow_result.get("last_page", "")
        return _string_finding(assertion, actual)

    if assertion.type == "page_not_contains":
        actual = flow_result.get("last_page", "")
        actual_text = str(actual or "")
        expected_text = str(assertion.expected or "")
        passed = expected_text.lower() not in actual_text.lower()
        return AssertionFinding(
            type=assertion.type,
            operator=assertion.operator,
            expected=assertion.expected,
            actual=actual,
            evidence_path=assertion.evidence_path,
            passed=passed,
            message="" if passed else f"Page contains '{assertion.expected}' but expected it absent.",
        )

    if assertion.type == "uw_condition_contains":
        actual_rows = _uw_row_texts(flow_result, uw_stage_key)
        passed = any(str(assertion.expected).lower() in row.lower() for row in actual_rows)
        return AssertionFinding(
            type=assertion.type,
            operator=assertion.operator,
            expected=assertion.expected,
            actual=" | ".join(actual_rows[:5]) if actual_rows else "(no UW rows)",
            evidence_path=assertion.evidence_path,
            passed=passed,
            message="" if passed else f"Condition text not found in {len(actual_rows)} UW row(s).",
        )

    if assertion.type == "completed":
        actual = bool(flow_result.get("completed"))
        return AssertionFinding(
            type=assertion.type,
            operator=assertion.operator,
            expected=assertion.expected,
            actual=actual,
            evidence_path=assertion.evidence_path,
            passed=actual is bool(assertion.expected),
        )

    # ── New assertion types ──────────────────────────────────────────────────

    if assertion.type == "field_value":
        field_label = assertion.field_name
        field_values = _field_values_at_any_stage(flow_result)
        actual_list = field_values.get(field_label, [])
        actual = ", ".join(str(v) for v in actual_list) if actual_list else None
        if actual is None:
            return AssertionFinding(
                type=assertion.type,
                operator=assertion.operator,
                expected=assertion.expected,
                actual=None,
                evidence_path=assertion.evidence_path,
                passed=False,
                message=f"Field '{field_label}' not found in page state.",
            )
        return _string_finding(assertion, actual)

    if assertion.type == "uw_condition_absent":
        actual_rows = _uw_row_texts(flow_result, uw_stage_key)
        search = str(assertion.expected or "").lower()
        found = any(search in row.lower() for row in actual_rows)
        passed = not found
        return AssertionFinding(
            type=assertion.type,
            operator=assertion.operator,
            expected=assertion.expected,
            actual=" | ".join(actual_rows[:5]) if actual_rows else "(no UW rows)",
            evidence_path=assertion.evidence_path,
            passed=passed,
            message="" if passed else "Condition text found in UW rows — expected absent.",
        )

    if assertion.type == "uw_condition_count":
        actual_rows = _uw_row_texts(flow_result, uw_stage_key)
        uw_rows = [r for r in actual_rows if "Underwriting" in r]
        return _numeric_finding(assertion, float(len(uw_rows)))

    if assertion.type == "action_available":
        actions = _action_labels(flow_result)
        actual = ", ".join(actions) if actions else "(no actions)"
        if assertion.operator == "exists":
            passed = bool(actions)
        else:
            expected_label = str(assertion.expected or "").lower()
            passed = any(expected_label in label.lower() for label in actions)
        return AssertionFinding(
            type=assertion.type,
            operator=assertion.operator,
            expected=assertion.expected,
            actual=actual,
            evidence_path=assertion.evidence_path,
            passed=passed,
            message="" if passed else f"Action '{assertion.expected}' not found in: {actual}",
        )

    if assertion.type == "flow_blocked":
        blocked_reason = flow_result.get("blocked_reason") or ""
        is_blocked = bool(blocked_reason)
        expected_blocked = bool(assertion.expected) if assertion.expected is not None else True
        passed = is_blocked == expected_blocked
        return AssertionFinding(
            type=assertion.type,
            operator=assertion.operator,
            expected=assertion.expected,
            actual=blocked_reason if is_blocked else False,
            evidence_path=assertion.evidence_path,
            passed=passed,
        )

    if assertion.type == "total_cost":
        field_values = flow_result.get("ui_data", {}).get("field_values", {})
        raw_values = next(
            (v for k, v in field_values.items() if "total cost" in k.lower()),
            None,
        )
        raw = raw_values[0] if raw_values else None
        actual = _parse_money(raw)
        return _numeric_finding(assertion, actual)

    if assertion.type == "policy_status":
        field_values = flow_result.get("ui_data", {}).get("field_values", {})
        values = field_values.get("Status", [])
        actual = values[0] if values else None
        return _string_finding(assertion, actual)

    if assertion.type == "base_rate":
        coverage_name = (assertion.field_name or "").strip()
        base_rates = flow_result.get("rating_factors", {}).get("business_values", {}).get("base_rates", [])
        if not base_rates:
            return AssertionFinding(
                type=assertion.type,
                operator=assertion.operator,
                expected=assertion.expected,
                actual=None,
                evidence_path=assertion.evidence_path,
                passed=False,
                message="No base rates found — stop_after must be 'rating-detail'.",
            )
        match = next(
            (r for r in base_rates if coverage_name.lower() in str(r.get("coverage", "")).lower()),
            None,
        )
        if match is None:
            available = ", ".join(str(r.get("coverage", "")) for r in base_rates)
            return AssertionFinding(
                type=assertion.type,
                operator=assertion.operator,
                expected=assertion.expected,
                actual=None,
                evidence_path=assertion.evidence_path,
                passed=False,
                message=f"Coverage '{coverage_name}' not found in base rates. Available: {available}",
            )
        actual = None
        try:
            actual = float(str(match.get("value") or "").replace(",", ""))
        except (TypeError, ValueError):
            pass
        return _numeric_finding(assertion, actual)

    if assertion.type == "premium_factor":
        factor_texts = _premium_factor_texts(flow_result)
        if not factor_texts:
            return AssertionFinding(
                type=assertion.type,
                operator=assertion.operator,
                expected=assertion.expected,
                actual="(no rating factors — stop_after must be rating-detail)",
                evidence_path=assertion.evidence_path,
                passed=False,
                message="Rating factors are only available when stop_after=rating-detail.",
            )
        search = str(assertion.expected or "").lower()
        if assertion.operator == "exists":
            passed = bool(factor_texts)
        else:
            passed = any(search in text.lower() for text in factor_texts)
        return AssertionFinding(
            type=assertion.type,
            operator=assertion.operator,
            expected=assertion.expected,
            actual=" | ".join(factor_texts[:3]),
            evidence_path=assertion.evidence_path,
            passed=passed,
            message="" if passed else f"Factor '{assertion.expected}' not found in {len(factor_texts)} factor rows.",
        )

    return AssertionFinding(
        type=assertion.type,
        operator=assertion.operator,
        expected=assertion.expected,
        actual=None,
        evidence_path=assertion.evidence_path,
        passed=False,
        message=f"Unsupported assertion type: {assertion.type}",
    )


def _delta_note(actual: float, target: float) -> str:
    delta = actual - target
    pct = (delta / target * 100) if target != 0 else 0.0
    sign = "+" if delta >= 0 else ""
    return f"delta {sign}${delta:,.2f} ({sign}{pct:.1f}%)"


def _numeric_finding(assertion: ApiAssertion, actual: float | None) -> AssertionFinding:
    expected = assertion.expected
    passed = False
    message = ""

    if assertion.operator == "exists":
        passed = actual is not None
    elif actual is None:
        message = "No numeric premium value was extracted."
    elif assertion.operator == "equals":
        passed = actual == float(expected)
        if not passed:
            message = _delta_note(actual, float(expected))
    elif assertion.operator == "approx":
        tolerance = assertion.tolerance if assertion.tolerance is not None else 0.02
        if 0 < tolerance < 1:
            allowed = abs(float(expected)) * tolerance
        else:
            allowed = float(tolerance)
        passed = abs(actual - float(expected)) <= allowed
        message = f"Allowed ±${allowed:,.2f} — {_delta_note(actual, float(expected))}"
    elif assertion.operator == "lt":
        passed = actual < float(expected)
        if not passed:
            message = _delta_note(actual, float(expected))
    elif assertion.operator == "lte":
        passed = actual <= float(expected)
        if not passed:
            message = _delta_note(actual, float(expected))
    elif assertion.operator == "gt":
        passed = actual > float(expected)
        if not passed:
            message = _delta_note(actual, float(expected))
    elif assertion.operator == "gte":
        passed = actual >= float(expected)
        if not passed:
            message = _delta_note(actual, float(expected))
    elif assertion.operator == "between":
        lo = assertion.min_value
        hi = assertion.max_value
        passed = lo is not None and hi is not None and lo <= actual <= hi
        expected = f"{lo}..{hi}"
        if not passed and lo is not None and hi is not None:
            if actual < lo:
                message = f"Below range — {_delta_note(actual, lo)}"
            else:
                message = f"Above range — {_delta_note(actual, hi)}"
    else:
        message = f"Unsupported numeric operator: {assertion.operator}"

    return AssertionFinding(
        type=assertion.type,
        operator=assertion.operator,
        expected=expected,
        actual=actual,
        evidence_path=assertion.evidence_path,
        passed=passed,
        message=message,
    )


def _string_finding(assertion: ApiAssertion, actual: Any) -> AssertionFinding:
    actual_text = "" if actual is None else str(actual)
    expected_text = "" if assertion.expected is None else str(assertion.expected)

    if assertion.operator == "contains":
        passed = expected_text.lower() in actual_text.lower()
    elif assertion.operator == "not_contains":
        passed = expected_text.lower() not in actual_text.lower()
    elif assertion.operator == "equals":
        passed = expected_text.lower() == actual_text.lower()
    elif assertion.operator == "exists":
        passed = bool(actual_text)
    else:
        passed = False

    return AssertionFinding(
        type=assertion.type,
        operator=assertion.operator,
        expected=assertion.expected,
        actual=actual,
        evidence_path=assertion.evidence_path,
        passed=passed,
    )


def _field_values_at_any_stage(flow_result: dict[str, Any]) -> dict[str, list[Any]]:
    """Merge field_values from all stages; current ui_data wins on label collision."""
    merged: dict[str, list[Any]] = {}
    for stage_data in flow_result.get("stage_ui_data", {}).values():
        for label, values in stage_data.get("field_values", {}).items():
            if label not in merged:
                merged[label] = values
    for label, values in flow_result.get("ui_data", {}).get("field_values", {}).items():
        merged[label] = values
    return merged


def _action_labels(flow_result: dict[str, Any]) -> list[str]:
    return flow_result.get("ui_data", {}).get("actions", [])


def _premium_factor_texts(flow_result: dict[str, Any]) -> list[str]:
    factors = flow_result.get("rating_factors", {}).get("factors", [])
    return [
        " | ".join(str(v) for v in row.values())
        for row in factors
        if isinstance(row, dict)
    ]


def _premium_value(flow_result: dict[str, Any], premium_path: str) -> float | None:
    # Walk the dotted premium_path; fall back to summary page field, then regex.
    parts = premium_path.split(".")
    node: Any = flow_result
    for part in parts:
        if not isinstance(node, dict):
            node = None
            break
        node = node.get(part)
    if node is not None:
        try:
            return float(node)
        except (TypeError, ValueError):
            pass

    # Read "Total Policy Premium" from the Verify Billing / summary page field_values.
    field_values = flow_result.get("ui_data", {}).get("field_values", {})
    for label, values in field_values.items():
        if "total policy premium" in label.lower():
            raw = values[0] if values else None
            result = _parse_money(raw)
            if result is not None:
                return result

    summary = flow_result.get("rating_factors", {}).get("summary_premium") or flow_result.get("premium", "")
    return _parse_money(summary)


def _parse_money(raw: Any) -> float | None:
    digits = re.sub(r"[^\d.]", "", str(raw or ""))
    if not digits:
        return None
    try:
        return float(digits)
    except ValueError:
        return None


def _uw_row_texts(flow_result: dict[str, Any], uw_stage_key: str) -> list[str]:
    stage_ui = flow_result.get("stage_ui_data", {}).get(uw_stage_key, flow_result.get("ui_data", {}))
    return [
        " | ".join(str(value) for value in row.values())
        for grid in stage_ui.get("grids", [])
        for row in grid.get("rows", [])
    ]
