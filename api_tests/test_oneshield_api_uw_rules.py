"""API assertions for Auto UW referral and post-issue data snapshots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from api_tests.conftest import PREMIUM_BASELINES_PATH
from api_tests.oneshield_api_replay import DEFAULT_AUTO_DATA, load_auto_test_data
from api_tests.rating_assertions import assert_coverage_premium, compute_coverage_premiums
from dashboard.backend.api_assertions.premium import extract_premium_evidence

pytestmark = pytest.mark.api

AUTO_UW_RULES_DATA = Path("testdata/static/auto/AutoUWRulesData.json")
SR22_CONDITION = "SR-22 / Certificate of Insurance Indicator is checked"
LICENSE_CONDITION = "driver license status that is revoked or suspended"
UNDER_25_CONDITION = "All drivers under 25 years of age"
LEASED_UW_CASES = {"UW_TC_008", "UW_TC_010"}
AUTO_UW_CASES = [
    ("UW_TC_001", [SR22_CONDITION]),
    ("UW_TC_002", [LICENSE_CONDITION]),
    ("UW_TC_003", [UNDER_25_CONDITION]),
    ("UW_TC_004", [LICENSE_CONDITION]),
    ("UW_TC_005", [SR22_CONDITION, UNDER_25_CONDITION]),
    ("UW_TC_006", [SR22_CONDITION, LICENSE_CONDITION]),
    ("UW_TC_007", [SR22_CONDITION, LICENSE_CONDITION, UNDER_25_CONDITION]),
    ("UW_TC_008", [UNDER_25_CONDITION]),
    ("UW_TC_009", [LICENSE_CONDITION, UNDER_25_CONDITION]),
    ("UW_TC_010", [SR22_CONDITION]),
    ("UW_TC_011", [UNDER_25_CONDITION]),
    ("UW_TC_012", [SR22_CONDITION, LICENSE_CONDITION]),
    ("UW_TC_013", [SR22_CONDITION]),
    ("UW_TC_014", [UNDER_25_CONDITION]),
]


def _grid_row_texts(ui_data: dict[str, Any]) -> list[str]:
    return [
        " | ".join(str(value) for value in row.values())
        for grid in ui_data["grids"]
        for row in grid["rows"]
    ]


@pytest.mark.uw_rules
@pytest.mark.parametrize(
    ("tc_id", "expected_conditions"),
    AUTO_UW_CASES,
    ids=[tc_id for tc_id, _expected_conditions in AUTO_UW_CASES],
)
def test_oneshield_api_uw_referral_snapshot_matches_ui_rule(
    oneshield_api_client,
    tc_id,
    expected_conditions,
):
    """Assert the UW referral page through the API model exposed to the UI."""
    test_data = load_auto_test_data(AUTO_UW_RULES_DATA, tc_id)

    result = oneshield_api_client.run_captured_auto_flow(test_data, stop_after="rate", fast_mode=True)
    rate_ui = result["stage_ui_data"]["rate"]
    row_texts = _grid_row_texts(rate_ui)

    assert result["completed"] is True
    assert result["blocked_reason"] == ""
    assert "underwriting" in rate_ui["page_name"].lower()
    for expected_condition in expected_conditions:
        assert any(
            "Underwriting" in row_text and expected_condition in row_text
            for row_text in row_texts
        ), f"{tc_id} did not expose {expected_condition!r} in API UW grids: {rate_ui['grids']!r}"
    if tc_id in LEASED_UW_CASES:
        assert any(
            item["page"] == "auto_vehicle" and item["tx_name"] == "Action.189"
            for item in result["trace"]
        ), f"{tc_id} did not replay the vehicle loss-payee Add-row action."


SR22_UW_CASES = ["UW_TC_001", "UW_TC_010", "UW_TC_013"]
SOFT_UW_PREMIUM_CASES = ["UW_TC_001", "UW_TC_003"]


@pytest.mark.uw_rules
@pytest.mark.parametrize("tc_id", SOFT_UW_PREMIUM_CASES)
def test_oneshield_api_soft_uw_continues_to_premium_summary(
    oneshield_api_client,
    tc_id,
):
    """Approve editable SR-22/young-driver referrals and capture UI premium."""
    test_data = load_auto_test_data(AUTO_UW_RULES_DATA, tc_id)

    result = oneshield_api_client.run_captured_auto_flow(
        test_data,
        stop_after="rating-detail",
        fast_mode=True,
        continue_soft_uw=True,
    )
    evidence = extract_premium_evidence(result)

    assert result["completed"] is True, result["blocked_reason"]
    assert result["soft_uw_continued"] is True
    assert "uw-referral" in result["stage_ui_data"]
    assert "premium" in result["stage_ui_data"]["rate"]["page_name"].lower()
    assert evidence.value is not None
    assert evidence.source == "stage_ui_data.rate.field_values.Premium"


@pytest.mark.uw_rules
@pytest.mark.parametrize("tc_id", SR22_UW_CASES)
def test_oneshield_api_uw_rating_detail_factors(oneshield_api_client, tc_id):
    """Assert rating factors are accessible on a UW-referred SR-22 quote.

    Even though the quote is referred, rating ran first — the Rating Detail
    tab must show a Base Rate, at least one coverage row, and a non-zero
    Out value for each coverage.
    """
    test_data = load_auto_test_data(AUTO_UW_RULES_DATA, tc_id)

    result = oneshield_api_client.run_captured_auto_flow(test_data, stop_after="rating-detail")
    rf = result["rating_factors"]

    assert result["completed"] is True, (
        f"{tc_id}: rating-detail not reached — {result['blocked_reason']}"
    )
    assert "rating detail" in result["last_page"].lower(), (
        f"{tc_id}: unexpected last page: {result['last_page']!r}"
    )

    assert rf["base_rates"], f"{tc_id}: no Base Rate rows found in Rating Detail"
    assert rf["factors"], f"{tc_id}: no factor rows parsed from Rating Detail"

    for br in rf["base_rates"]:
        assert float(str(br["value"]).replace(",", "")) > 0, (
            f"{tc_id}: Base Rate for {br['coverage']} is zero or negative"
        )

    out_vals_by_coverage: dict[str, float] = {}
    for row in rf["factors"]:
        if row.get("Factor") == "Policy Term Factor":
            try:
                out_vals_by_coverage[row.get("Coverage", "")] = float(
                    str(row.get("Out", "")).replace(",", "")
                )
            except (ValueError, TypeError):
                pass

    assert out_vals_by_coverage, f"{tc_id}: could not find final Policy Term Factor rows"
    for coverage, final_out in out_vals_by_coverage.items():
        assert final_out > 0, (
            f"{tc_id}: final Out value for {coverage!r} is zero — premium calculation may have failed"
        )


def test_oneshield_api_post_rate_request_bind_snapshots(request, oneshield_api_client):
    """Bind a clean quote and assert UI snapshot data captured at key API stages."""
    if not request.config.getoption("--oneshield-api-allow-bind"):
        pytest.skip("Re-run with --oneshield-api-allow-bind to bind a live API test policy.")

    test_data = load_auto_test_data(DEFAULT_AUTO_DATA, "TC_ID_0011")

    result = oneshield_api_client.run_captured_auto_flow(
        test_data,
        stop_after="bind",
        allow_bind=True,
    )
    stage_ui_data = result["stage_ui_data"]

    assert result["completed"] is True, result["blocked_reason"]
    assert result["policy_number"]
    assert {"rate", "request-issue", "bind"} <= stage_ui_data.keys()

    rate_ui = stage_ui_data["rate"]
    request_issue_ui = stage_ui_data["request-issue"]
    bind_ui = stage_ui_data["bind"]

    assert "premium" in rate_ui["page_name"].lower()
    assert rate_ui["field_values"]["Premium"]
    assert "delivery" in request_issue_ui["page_name"].lower()
    assert request_issue_ui["fields"] or request_issue_ui["grids"]
    assert "policy" in bind_ui["page_name"].lower()
    assert bind_ui["fields"] or bind_ui["grids"]
    assert result["ui_data"] == bind_ui


# ---------------------------------------------------------------------------
# Rating Detail premium regression — UW-referred cases
#
# First run (capture baselines):
#   pytest -m api -k uw_rating_detail_premium --update-premium-baselines
#
# Subsequent runs (regression check):
#   pytest -m api -k uw_rating_detail_premium
# ---------------------------------------------------------------------------

UW_PREMIUM_CASES = [
    "UW_TC_010",   # Gold + SR-22 + leased vehicle
]


@pytest.mark.uw_rules
@pytest.mark.parametrize("tc_id", UW_PREMIUM_CASES)
def test_uw_rating_detail_premium(request, oneshield_api_client, tc_id):
    """Assert the total rated premium from Rating Detail matches a known-good baseline.

    Drives the flow to the Rating Detail tab (runs even on UW-referred quotes
    because rating completes before UW evaluation). Sums the 'Policy Term
    Factor' Out values across all coverages to produce the total rated premium.

    Usage:
        # Capture baseline for a new case:
        pytest -m api -k uw_rating_detail_premium --update-premium-baselines

        # Simple one-shot call in a test or REPL:
        from api_tests.rating_assertions import compute_coverage_premiums, assert_coverage_premium
        result = client.run_captured_auto_flow(test_data, stop_after="rating-detail")
        premiums = compute_coverage_premiums(result)
        assert_coverage_premium(premiums, expected_total=1234.56)
    """
    updating = request.config.getoption("--update-premium-baselines")
    baselines: dict = json.loads(PREMIUM_BASELINES_PATH.read_text(encoding="utf-8"))

    if not updating and baselines.get(tc_id) is None:
        pytest.skip(f"No baseline for {tc_id} — run with --update-premium-baselines first")

    test_data = load_auto_test_data(AUTO_UW_RULES_DATA, tc_id)
    result = oneshield_api_client.run_captured_auto_flow(test_data, stop_after="rating-detail")

    assert result["completed"] is True, (
        f"{tc_id}: rating-detail not reached — {result['blocked_reason']}"
    )

    premiums = compute_coverage_premiums(result)
    assert premiums, f"{tc_id}: no Policy Term Factor rows found — rating detail may not have loaded"

    if updating:
        baselines[tc_id] = premiums["_total"]
        PREMIUM_BASELINES_PATH.write_text(json.dumps(baselines, indent=2), encoding="utf-8")
        return

    assert_coverage_premium(premiums, expected_total=float(baselines[tc_id]))
