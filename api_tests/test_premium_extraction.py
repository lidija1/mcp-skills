"""Unit tests for premium source selection."""

from __future__ import annotations

import pytest

from dashboard.backend.api_assertions.premium import extract_premium_evidence
from dashboard.backend.api_assertions.snapshot import _extract_premium

pytestmark = pytest.mark.api


def test_premium_summary_value_wins_over_rating_detail_sum():
    flow = {
        "stage_ui_data": {
            "rate": {
                "field_values": {
                    "Premium": ["$ 2,049.45"],
                }
            }
        },
        "rating_factors": {
            "summary_premium": "$ 2,049.45",
            "business_values": {
                "calculated_total_premium": 1824.0,
            },
        },
        "premium": "$ 2,049.45",
    }

    evidence = extract_premium_evidence(flow)

    assert evidence.value == 2049.45
    assert evidence.source == "stage_ui_data.rate.field_values.Premium"
    assert evidence.rating_detail_value == 1824.0
    assert evidence.mismatch is True
    assert _extract_premium(flow) == 2049.45


def test_rating_detail_sum_is_not_used_without_ui_premium():
    flow = {
        "rating_factors": {
            "business_values": {
                "calculated_total_premium": 1824.0,
            },
        },
    }

    evidence = extract_premium_evidence(flow)

    assert evidence.value is None
    assert evidence.source == "unavailable"
    assert evidence.rating_detail_value == 1824.0
    assert evidence.mismatch is False
