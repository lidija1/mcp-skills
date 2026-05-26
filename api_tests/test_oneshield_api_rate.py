"""OneShield API rate-to-premium tests."""

from __future__ import annotations

import json
import re

import pytest

from api_tests.conftest import PREMIUM_BASELINES_PATH
from api_tests.oneshield_api_replay import (
    DEFAULT_AUTO_DATA,
    load_all_auto_tc_ids,
    load_auto_test_data,
)

pytestmark = pytest.mark.api

_TC_IDS = load_all_auto_tc_ids(DEFAULT_AUTO_DATA)

PREMIUM_TOLERANCE = 0.02  # 2 % — covers rounding noise, catches engine regressions


def _parse_premium(raw: str) -> float:
    """Convert '$  2,049.45' → 2049.45. Raises ValueError on bad input."""
    digits = re.sub(r"[^\d.]", "", raw)
    if not digits:
        raise ValueError(f"Could not parse premium from: {raw!r}")
    return float(digits)


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


@pytest.mark.parametrize("tc_id", _TC_IDS)
def test_oneshield_api_premium_regression(request, oneshield_api_client, tc_id):
    """Premium regression sentinel — assert the rated premium matches a known-good baseline.

    First run (or after a deliberate re-baseline):
        pytest -m api -k premium_regression --update-premium-baselines
        → captures live premiums into api_tests/artifacts/premium_baselines.json

    Subsequent runs (CI / regression check):
        pytest -m api -k premium_regression
        → asserts each TC_ID's premium is within PREMIUM_TOLERANCE of the baseline.
        A null baseline entry is skipped so partially-populated files still work.
    """
    updating = request.config.getoption("--update-premium-baselines")
    baselines: dict = json.loads(PREMIUM_BASELINES_PATH.read_text(encoding="utf-8"))

    if not updating and baselines.get(tc_id) is None:
        pytest.skip(f"No baseline for {tc_id} — run with --update-premium-baselines first")

    test_data = load_auto_test_data(DEFAULT_AUTO_DATA, tc_id)
    result = oneshield_api_client.run_captured_auto_flow(test_data, stop_after="rate", fast_mode=True)

    assert result["completed"] is True, f"Flow did not complete: {result['blocked_reason']}"
    assert result["premium"], "No premium captured after rating"

    actual = _parse_premium(result["premium"])

    if updating:
        baselines[tc_id] = round(actual, 2)
        PREMIUM_BASELINES_PATH.write_text(
            json.dumps(baselines, indent=2), encoding="utf-8"
        )
        return  # no assertion — we're recording, not checking

    expected = float(baselines[tc_id])
    delta = abs(actual - expected) / expected if expected else 0
    assert delta <= PREMIUM_TOLERANCE, (
        f"{tc_id}: premium drifted {delta:.1%} from baseline "
        f"(expected ${expected:,.2f}, got ${actual:,.2f}) — "
        f"rating engine may have changed"
    )
