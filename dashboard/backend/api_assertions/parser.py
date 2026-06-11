"""Parse manager-friendly plain English into a deterministic UW test assertion spec."""

from __future__ import annotations

import re

from dashboard.backend.api_assertions.lob_config import LobConfig, get_lob_config
from dashboard.backend.api_assertions.schemas import ApiAssertion, ApiAssertionSpec


def parse_plain_english_api_assertion(prompt: str, lob: str = "auto") -> ApiAssertionSpec:
    cfg = get_lob_config(lob)
    text = " ".join((prompt or "").split())
    if not text:
        raise ValueError("Enter a plain-English UW test request.")

    lower = text.lower()
    assertions: list[ApiAssertion] = []

    # Premium
    premium_assertion = _parse_premium_assertion(lower)
    if premium_assertion:
        assertions.append(premium_assertion)

    # Coverage tier
    for coverage in cfg.coverages:
        if re.search(rf"\b{coverage}\b", lower):
            assertions.append(
                ApiAssertion(
                    type="coverage",
                    operator="equals",
                    expected=coverage.title(),
                    evidence_path="persona.PolicyCoverage",
                )
            )
            break

    # Flow blocked / unblocked
    flow_blocked = _parse_flow_blocked(lower)
    if flow_blocked:
        assertions.append(flow_blocked)

    # UW condition count — handles "N conditions" and "no conditions"; takes
    # priority over the individual contains/absent checks below
    condition_count = _parse_condition_count(lower)
    uw_handled = False
    if condition_count is not None:
        assertions.append(ApiAssertion(
            type="uw_condition_count",
            operator="equals",
            expected=float(condition_count),
            evidence_path=f"flow_result.stage_ui_data.{cfg.uw_stage_key}.grids.rows",
        ))
        uw_handled = True

    # General negative UW intent, e.g. "should not trigger underwriting".
    if not uw_handled:
        negative_uw_assertions = _parse_negative_uw_assertions(lower, cfg)
        if negative_uw_assertions:
            assertions.extend(negative_uw_assertions)
            uw_handled = True

    # Specific UW condition absent - negation word paired with a configured hint.
    if not uw_handled:
        absent = _parse_uw_absent(lower, cfg)
        if absent:
            assertions.append(absent)
            uw_handled = True

    # Positive UW assertions (original logic, skipped when count/absent already set)
    if not uw_handled:
        if any(word in lower for word in ("uw", "underwriting", "referral", "refer")):
            assertions.append(
                ApiAssertion(
                    type="page_contains",
                    operator="contains",
                    expected="underwriting",
                    evidence_path="flow_result.last_page",
                )
            )

        quoted_condition = _quoted_after_contains(text)
        if quoted_condition:
            assertions.append(
                ApiAssertion(
                    type="uw_condition_contains",
                    operator="contains",
                    expected=quoted_condition,
                    evidence_path=f"flow_result.stage_ui_data.{cfg.uw_stage_key}.grids.rows",
                )
            )
        elif "all drivers under 25" in lower:
            assertions.append(
                ApiAssertion(
                    type="uw_condition_contains",
                    operator="contains",
                    expected="All drivers under 25 years of age",
                    evidence_path=f"flow_result.stage_ui_data.{cfg.uw_stage_key}.grids.rows",
                )
            )
        else:
            for hint, condition in cfg.uw_hints:
                if hint in lower and any(word in lower for word in ("uw", "underwriting", "referral", "refer", "condition")):
                    assertions.append(
                        ApiAssertion(
                            type="uw_condition_contains",
                            operator="contains",
                            expected=condition,
                            evidence_path=f"flow_result.stage_ui_data.{cfg.uw_stage_key}.grids.rows",
                        )
                    )
                    break

    # Action button availability
    action = _parse_action_available(lower, cfg)
    if action:
        assertions.append(action)

    # Total cost (premium + taxes + fees)
    total_cost = _parse_total_cost(lower)
    if total_cost:
        assertions.append(total_cost)

    # Policy status field
    policy_status = _parse_policy_status(lower)
    if policy_status:
        assertions.append(policy_status)

    # Base rate for a specific coverage (forces stop_after=rating-detail)
    base_rate = _parse_base_rate(lower)
    if base_rate:
        assertions.append(base_rate)

    # Rating factor (forces stop_after=rating-detail)
    factor = _parse_premium_factor(lower)
    if factor:
        assertions.append(factor)

    if not assertions:
        assertions.append(
            ApiAssertion(
                type="completed",
                operator="equals",
                expected=True,
                evidence_path="flow_result.completed",
            )
        )

    if any(a.type in ("premium_factor", "base_rate") for a in assertions):
        stage = "rating-detail"
    elif any(a.type == "premium" for a in assertions):
        stage = "verify-billing"
    else:
        stage = cfg.default_stage
    return ApiAssertionSpec(
        lob=lob,
        prompt=text,
        persona_prompt=_persona_prompt(text, cfg),
        stage=stage,
        assertions=assertions,
    )


def _parse_condition_count(lower: str) -> int | None:
    """Return an integer if the prompt specifies a UW condition count."""
    # "exactly N conditions"
    match = re.search(r"\bexactly\s+(\d+)\b.*\bconditions?\b", lower)
    if match:
        return int(match.group(1))
    # "N uw/referral conditions" — require N to be preceded by whitespace or
    # start of string so that "sr-22 condition" doesn't match as "22 condition"
    match = re.search(
        r"(?:^|(?<=\s))(\d+)\s+(?:uw\s+|underwriting\s+|referral\s+)?conditions?\b",
        lower,
    )
    if match:
        return int(match.group(1))
    # "no conditions" / "zero conditions"
    if re.search(r"\bno\b\s+(?:uw\s+|underwriting\s+|referral\s+)?conditions?\b", lower):
        return 0
    if re.search(r"\bzero\b\s+(?:uw\s+|underwriting\s+|referral\s+)?conditions?\b", lower):
        return 0
    return None


def _parse_negative_uw_assertions(lower: str, cfg: LobConfig) -> list[ApiAssertion]:
    """Return assertions for prompts that expect no UW referral to fire."""
    if not _has_negative_uw_intent(lower):
        return []

    assertions: list[ApiAssertion] = []
    specific_absent = _parse_uw_absent(lower, cfg)
    if specific_absent:
        assertions.append(specific_absent)

    assertions.extend([
        ApiAssertion(
            type="page_not_contains",
            operator="not_contains",
            expected="underwriting",
            evidence_path="flow_result.last_page",
        ),
        ApiAssertion(
            type="uw_condition_count",
            operator="equals",
            expected=0.0,
            evidence_path=f"flow_result.stage_ui_data.{cfg.uw_stage_key}.grids.rows",
        ),
    ])
    return assertions


def _has_negative_uw_intent(lower: str) -> bool:
    uw_word = r"(?:uw|underwriting|referral|refer(?:ral|red)?|referred)"
    trigger_word = r"(?:trigger|create|cause|produce|raise|hit|reach|route\s+to|land\s+on|go\s+to|fire|refer(?:red)?|be\s+referred)"
    negation = r"(?:should(?:n't|\s+not)|must\s+not|does(?:n't|\s+not)|do(?:n't|\s+not)|will\s+not|won't|never)"
    patterns = (
        rf"\b{negation}\b[^.?!]{{0,80}}\b{trigger_word}\b[^.?!]{{0,80}}\b{uw_word}\b",
        rf"\b{negation}\b[^.?!]{{0,80}}\b{uw_word}\b",
        rf"\b(?:not|never|without|absent)\b[^.?!]{{0,40}}\b{uw_word}\b",
        r"\b(?:no|zero)\s+(?:uw\s+|underwriting\s+|referral\s+)?(?:referrals?|issues?|rows?|conditions?)\b",
        rf"\b{uw_word}\b[^.?!]{{0,80}}\b{negation}\b",
    )
    return any(re.search(pattern, lower) for pattern in patterns)


def _parse_uw_absent(lower: str, cfg: LobConfig) -> ApiAssertion | None:
    """Return uw_condition_absent when a negation word is paired with a specific UW hint."""
    if not re.search(r"\b(?:no|not|without|absent|never)\b", lower):
        return None
    for hint, condition in cfg.uw_hints:
        if hint in lower:
            return ApiAssertion(
                type="uw_condition_absent",
                operator="contains",
                expected=condition,
                evidence_path=f"flow_result.stage_ui_data.{cfg.uw_stage_key}.grids.rows",
            )
    return None


def _parse_flow_blocked(lower: str) -> ApiAssertion | None:
    if re.search(r"\b(?:should\s+be\s+blocked|flow\s+is\s+blocked|gets?\s+blocked)\b", lower):
        return ApiAssertion(
            type="flow_blocked",
            operator="equals",
            expected=True,
            evidence_path="flow_result.blocked_reason",
        )
    if re.search(
        r"\b(?:not\s+blocked|should(?:n't|\s+not)\s+be\s+blocked|quote\s+should\s+complete|flow\s+completes?)\b",
        lower,
    ):
        return ApiAssertion(
            type="flow_blocked",
            operator="equals",
            expected=False,
            evidence_path="flow_result.blocked_reason",
        )
    return None


def _parse_action_available(lower: str, cfg: LobConfig) -> ApiAssertion | None:
    if not re.search(r"\b(?:available|present|exists?|button|action|enabled)\b", lower):
        return None
    for action in cfg.known_actions:
        if action.lower() in lower:
            return ApiAssertion(
                type="action_available",
                operator="contains",
                expected=action,
                evidence_path="flow_result.ui_data.actions",
            )
    return None


def _parse_premium_factor(lower: str) -> ApiAssertion | None:
    # "factor Base Rate exists" / "rating factor Policy Term Factor present"
    match = re.search(
        r"(?:rating\s+)?factor\s+[\"']?([a-z][^\"',.\n]{2,40}?)[\"']?\s+"
        r"(?:exists?|present|found|available|appears?)",
        lower,
    )
    if match:
        return ApiAssertion(
            type="premium_factor",
            operator="contains",
            expected=match.group(1).strip().title(),
            evidence_path="flow_result.rating_factors.factors",
        )
    # "factor contains Base Rate"
    match = re.search(
        r"\bfactor\b.*?\bcontains?\s+[\"']?([a-z][^\"',.\n]{2,40}?)[\"']?(?:\s|$)", lower
    )
    if match:
        return ApiAssertion(
            type="premium_factor",
            operator="contains",
            expected=match.group(1).strip().title(),
            evidence_path="flow_result.rating_factors.factors",
        )
    return None


def _parse_total_cost(lower: str) -> ApiAssertion | None:
    if not re.search(r"\btotal\s+cost\b", lower):
        return None
    comparison = re.search(
        r"\btotal\s+cost\b.*?\b(less than|under|below|greater than|over|above|at least|more than|equals?|is)\s+\$?\s*([0-9][0-9,]*(?:\.\d+)?)",
        lower,
    )
    if comparison:
        phrase = comparison.group(1)
        operator = {
            "less than": "lt", "under": "lt", "below": "lt",
            "greater than": "gt", "over": "gt", "above": "gt", "more than": "gt",
            "at least": "gte", "equals": "equals", "equal": "equals", "is": "equals",
        }.get(phrase, "lt")
        return ApiAssertion(
            type="total_cost",
            operator=operator,
            expected=_money(comparison.group(2)),
            evidence_path="flow_result.ui_data.field_values.Total Cost",
        )
    return ApiAssertion(type="total_cost", operator="exists", evidence_path="flow_result.ui_data.field_values.Total Cost")


def _parse_policy_status(lower: str) -> ApiAssertion | None:
    if not re.search(r"\bpolicy\s+status\b", lower):
        return None
    match = re.search(r"\bpolicy\s+status\b.*?\b(?:is|equals?)\s+([a-z]+)", lower)
    if match:
        return ApiAssertion(
            type="policy_status",
            operator="equals",
            expected=match.group(1).title(),
            evidence_path="flow_result.ui_data.field_values.Status",
        )
    return ApiAssertion(type="policy_status", operator="exists", evidence_path="flow_result.ui_data.field_values.Status")


def _parse_base_rate(lower: str) -> ApiAssertion | None:
    # "base rate for Bodily Injury is 281" / "base rate for BI equals 281"
    match = re.search(
        r"base\s+rate\s+(?:for\s+)?[\"']?([a-z][^\"',.\n]{2,30}?)[\"']?\s+"
        r"(?:is|equals?|=|should\s+be)\s+\$?\s*([0-9][0-9,]*(?:\.\d+)?)",
        lower,
    )
    if match:
        return ApiAssertion(
            type="base_rate",
            operator="equals",
            field_name=match.group(1).strip().title(),
            expected=_money(match.group(2)),
            evidence_path="flow_result.rating_factors.business_values.base_rates",
        )
    # "base rate for Bodily Injury under/over/between ..."
    match = re.search(
        r"base\s+rate\s+(?:for\s+)?[\"']?([a-z][^\"',.\n]{2,30}?)[\"']?\s+"
        r"(?:less than|under|below|greater than|over|above|at least|more than)\s+\$?\s*([0-9][0-9,]*(?:\.\d+)?)",
        lower,
    )
    if match:
        phrase = re.search(r"(less than|under|below|greater than|over|above|at least|more than)", lower)
        operator = {
            "less than": "lt", "under": "lt", "below": "lt",
            "greater than": "gt", "over": "gt", "above": "gt",
            "more than": "gt", "at least": "gte",
        }[phrase.group(1)] if phrase else "lt"
        return ApiAssertion(
            type="base_rate",
            operator=operator,
            field_name=match.group(1).strip().title(),
            expected=_money(match.group(2)),
            evidence_path="flow_result.rating_factors.business_values.base_rates",
        )
    # "base rate for Bodily Injury exists"
    match = re.search(
        r"base\s+rate\s+(?:for\s+)?[\"']?([a-z][^\"',.\n]{2,30}?)[\"']?\s+"
        r"(?:exists?|present|found|available)",
        lower,
    )
    if match:
        return ApiAssertion(
            type="base_rate",
            operator="exists",
            field_name=match.group(1).strip().title(),
            evidence_path="flow_result.rating_factors.business_values.base_rates",
        )
    return None


_PREMIUM_EVIDENCE_PATH = "flow_result.ui_data.field_values.Total Policy Premium"


def _parse_premium_assertion(lower: str) -> ApiAssertion | None:
    if not re.search(r"\b(?:premium|price|cost)\b", lower):
        return None

    between = re.search(
        r"\b(?:premium|price|cost|rate)\b.*?\bbetween\s+\$?\s*([0-9][0-9,]*(?:\.\d+)?)\s+(?:and|to|-)\s+\$?\s*([0-9][0-9,]*(?:\.\d+)?)",
        lower,
    )
    if between:
        return ApiAssertion(
            type="premium",
            operator="between",
            min_value=_money(between.group(1)),
            max_value=_money(between.group(2)),
            evidence_path=_PREMIUM_EVIDENCE_PATH,
        )

    comparison = re.search(
        r"\b(?:premium|price|cost|rate)\b.*?\b(less than|under|below|greater than|over|above|at least|more than)\s+\$?\s*([0-9][0-9,]*(?:\.\d+)?)",
        lower,
    )
    if comparison:
        phrase = comparison.group(1)
        operator = {
            "less than": "lt",
            "under": "lt",
            "below": "lt",
            "greater than": "gt",
            "over": "gt",
            "above": "gt",
            "more than": "gt",
            "at least": "gte",
        }[phrase]
        return ApiAssertion(
            type="premium",
            operator=operator,
            expected=_money(comparison.group(2)),
            evidence_path=_PREMIUM_EVIDENCE_PATH,
        )

    amount = re.search(
        r"\b(?:premium|price|cost|rate)\b.*?(?:is|equals|equal to|around|about|approximately|approx|should be|=)\s+\$?\s*([0-9][0-9,]*(?:\.\d+)?)",
        lower,
    )
    if not amount:
        amount = re.search(r"\$?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(?:usd|dollars?)", lower)
    if amount:
        expected = _money(amount.group(1))
        tolerance = _parse_tolerance(lower)
        operator = "approx" if tolerance is not None or any(word in lower for word in ("around", "about", "approximately", "approx")) else "equals"
        return ApiAssertion(
            type="premium",
            operator=operator,
            expected=expected,
            tolerance=tolerance if tolerance is not None else (0.02 if operator == "approx" else None),
            evidence_path=_PREMIUM_EVIDENCE_PATH,
        )

    return ApiAssertion(
        type="premium",
        operator="exists",
        evidence_path="flow_result.premium",
    )


def _parse_tolerance(lower: str) -> float | None:
    abs_tol = re.search(r"(?:\+/-|plus or minus|within)\s+\$?\s*([0-9][0-9,]*(?:\.\d+)?)", lower)
    if abs_tol:
        return _money(abs_tol.group(1))
    pct_tol = re.search(r"(?:\+/-|plus or minus|within)\s+([0-9]+(?:\.\d+)?)\s*%", lower)
    if pct_tol:
        return float(pct_tol.group(1)) / 100.0
    return None


def _quoted_after_contains(text: str) -> str:
    match = re.search(r"contains?\s+[\"']([^\"']+)[\"']", text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _persona_prompt(text: str, cfg: LobConfig) -> str:
    clean = text
    assertion_marker = re.search(r"\bassert(?:ion)?\b", clean, flags=re.IGNORECASE)
    if assertion_marker and assertion_marker.start() > 0:
        clean = clean[:assertion_marker.start()]
    clean = re.sub(r"\bassert(?:ion)?\b", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"^\s*(?:that\s+)?(?:for\s+)?", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bpremium\b.*", "", clean, flags=re.IGNORECASE).strip(" ,.;")
    clean = re.sub(r"\b(?:and|then|with)\s*$", "", clean, flags=re.IGNORECASE).strip(" ,.;")
    lower_text = text.lower()
    for coverage in cfg.coverages:
        if re.search(rf"\b{coverage}\b", lower_text) and coverage not in clean.lower():
            clean = f"{clean} with {coverage.title()} coverage".strip()
            break
    return clean or text


def _money(raw: str) -> float:
    return float(str(raw).replace(",", ""))
