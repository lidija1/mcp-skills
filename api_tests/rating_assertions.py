"""Helpers for asserting Rating Detail premium values from API replay results."""

from __future__ import annotations

import re
from typing import Any


def compute_coverage_premiums(result: dict[str, Any]) -> dict[str, float]:
    """Extract final per-coverage premiums from a rating-detail result.

    Sums the 'Out' value of every 'Policy Term Factor' row across all
    coverages. Returns a dict with one key per coverage plus '_total'.

    Args:
        result: The dict returned by run_captured_auto_flow(stop_after="rating-detail").

    Returns:
        Example: {"Bodily Injury": 369.0, "Property Damage": 215.0, "_total": 584.0}
        Empty dict if rating_factors is missing or has no Policy Term Factor rows.
    """
    factors = result.get("rating_factors", {}).get("factors", [])
    by_coverage: dict[str, float] = {}
    for row in factors:
        if row.get("Factor") != "Policy Term Factor":
            continue
        coverage = row.get("Coverage", "")
        try:
            out = float(str(row.get("Out", "")).replace(",", ""))
        except (ValueError, TypeError):
            continue
        by_coverage[coverage] = out

    summary_premium_str = result.get("rating_factors", {}).get("summary_premium", "")
    if summary_premium_str:
        try:
            by_coverage["_summary_total"] = float(re.sub(r"[^\d.]", "", summary_premium_str))
        except ValueError:
            pass

    if by_coverage:
        factor_total = round(sum(v for k, v in by_coverage.items() if not k.startswith("_")), 2)
        by_coverage["_total"] = factor_total
    return by_coverage


def assert_coverage_premium(
    premiums: dict[str, float],
    expected_total: float,
    tolerance: float = 0.02,
) -> None:
    """Assert the total rated premium is within tolerance of expected.

    Args:
        premiums: Output of compute_coverage_premiums().
        expected_total: Known-good total (sum of all Policy Term Factor Out values).
        tolerance: Fractional tolerance, default 2 % (0.02).

    Raises:
        AssertionError with a breakdown table on failure.
    """
    actual = premiums.get("_summary_total") or premiums.get("_total")
    assert actual is not None, (
        "No premium total in premiums dict — rating_factors may be empty. "
        f"Got: {premiums!r}"
    )
    delta = abs(actual - expected_total) / expected_total if expected_total else 0
    breakdown = "\n".join(
        f"  {cov}: {val}" for cov, val in premiums.items() if not cov.startswith("_")
    )
    assert delta <= tolerance, (
        f"Total rated premium drifted {delta:.1%} from baseline\n"
        f"  expected: {expected_total:,.2f}\n"
        f"  actual:   {actual:,.2f}\n"
        f"Coverage breakdown:\n{breakdown}"
    )


def _parse_premium_str(raw: str) -> float:
    """Convert '$  2,049.45' → 2049.45."""
    digits = re.sub(r"[^\d.]", "", raw)
    if not digits:
        raise ValueError(f"Cannot parse premium from: {raw!r}")
    return float(digits)
