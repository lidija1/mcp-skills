"""OneShield API rate-to-premium tests."""

from __future__ import annotations

import pytest

from api_tests.oneshield_api_replay import (
    DEFAULT_AUTO_DATA,
    load_all_auto_tc_ids,
    load_auto_test_data,
)

pytestmark = pytest.mark.api

_TC_IDS = load_all_auto_tc_ids(DEFAULT_AUTO_DATA)


@pytest.mark.parametrize("tc_id", _TC_IDS)
def test_oneshield_api_rate_quote(oneshield_api_client, tc_id):
    """Drive the captured Auto flow to rating and assert a premium is returned.

    Stops before request-issue — no policy is issued or bound.
    Creates a live OneShield quote record.
    """
    test_data = load_auto_test_data(DEFAULT_AUTO_DATA, tc_id)
    result = oneshield_api_client.run_captured_auto_flow(test_data, stop_after="rate", fast_mode=True)

    assert result["completed"] is True, f"Flow did not complete: {result['blocked_reason']}"
    assert result["blocked_reason"] == ""
    assert result["last_page"], "No last_page returned — replay may have stalled"
    assert result["premium"], "No premium captured after rating"


@pytest.mark.parametrize("tc_id", _TC_IDS)
def test_oneshield_api_rate_returns_premium_summary_page(oneshield_api_client, tc_id):
    """Verify the flow lands on the Premium Summary page after rating."""
    test_data = load_auto_test_data(DEFAULT_AUTO_DATA, tc_id)
    result = oneshield_api_client.run_captured_auto_flow(test_data, stop_after="rate", fast_mode=True)

    last_page = (result["last_page"] or "").lower()
    assert "premium" in last_page or "summary" in last_page, (
        f"Expected Premium/Summary page after rate, got: {result['last_page']!r}"
    )


@pytest.mark.parametrize("tc_id", _TC_IDS)
def test_oneshield_api_rate_no_uw_block(oneshield_api_client, tc_id):
    """Confirm each clean profile is not UW-blocked at rating."""
    test_data = load_auto_test_data(DEFAULT_AUTO_DATA, tc_id)
    result = oneshield_api_client.run_captured_auto_flow(test_data, stop_after="rate", fast_mode=True)

    assert result["blocked_reason"] == "", (
        f"Unexpected UW block for {tc_id}: {result['blocked_reason']}"
    )
    assert result["completed"] is True
