"""
Personal Auto E2E runner.

Workflow:
  1. Login
  2. New Quote
  3. Customer
  4. Quote Registration
  5. Quote Summary
  6. Driver Info
  7. Vehicle Info
  8. Coverage & Rate (includes UW referral detection)
  9. Outcome: UW Referral  OR  Policy Bind
"""

import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from playwright.sync_api import Page  # noqa: E402


def _record(steps, name, status, elapsed, detail=""):
    steps.append({
        "step": name,
        "status": status,
        "duration_s": round(elapsed, 2),
        "detail": detail,
    })


def _is_uw_referral_visible(page: Page, timeout: int = 2_000) -> bool:
    """Return whether the current page is an underwriting referral screen."""
    from ui.pages.auto.uw_referral_page import UWReferralPage

    return UWReferralPage(page).is_visible(timeout=timeout)


def _capture_uw_conditions(page: Page) -> list[str]:
    """Capture the UW issue grid cells from the visible referral screen."""
    from ui.pages.auto.uw_referral_page import UWReferralPage

    return UWReferralPage(page).capture_conditions(timeout=5_000)


def _record_uw_outcome(steps, name: str, elapsed: float, page: Page, detail: str) -> dict:
    uw_conditions = _capture_uw_conditions(page)
    _record(steps, name, "passed", elapsed, detail)
    _record(
        steps,
        "Outcome: UW Referral",
        "passed",
        0,
        f"{len(uw_conditions)} condition cell(s) captured",
    )
    return {
        "outcome": "uw_referral",
        "uw_conditions": uw_conditions,
        "error": None,
        "screenshot_path": None,
        "policy_summary": None,
        "premium": None,
    }


def _create_policy_or_uw(page: Page, steps: list, started_at: float) -> dict | None:
    """Run issue/billing/bind actions, stopping early if UW appears."""
    from ui.pages.auto.create_policy_page import CreatePolicyPage

    create_policy = CreatePolicyPage(page)
    actions = [
        ("Request Issue", create_policy.click_issue),
        ("Delivery Preferences", create_policy.click_next),
        ("Billing Plan", create_policy.click_next),
        ("Bind", create_policy.click_bind),
    ]

    for action_name, action in actions:
        if _is_uw_referral_visible(page, timeout=1_000):
            return _record_uw_outcome(
                steps,
                f"Outcome: UW Referral ({action_name})",
                time.perf_counter() - started_at,
                page,
                f"UW referral detected before {action_name.lower()}.",
            )

        try:
            action()
            create_policy.wait_for_loader_to_disappear()
        except Exception:
            if _is_uw_referral_visible(page, timeout=8_000):
                return _record_uw_outcome(
                    steps,
                    f"Outcome: UW Referral ({action_name})",
                    time.perf_counter() - started_at,
                    page,
                    f"UW referral detected during {action_name.lower()}.",
                )
            raise

        if _is_uw_referral_visible(page, timeout=1_000):
            return _record_uw_outcome(
                steps,
                f"Outcome: UW Referral ({action_name})",
                time.perf_counter() - started_at,
                page,
                f"UW referral detected after {action_name.lower()}.",
            )

    return None


def run_auto_flow(page: Page, persona: dict, steps: list) -> dict:
    """
    Execute the Personal Auto quote workflow on an already-open browser page.

    Args:
        page: Playwright page (already launched, blank new tab)
        persona: Dict matching the AutoData.json / ai_translator schema
        steps: List to append step result dicts to (mutated in place)

    Returns:
        Partial result dict with keys: outcome, uw_conditions, error, screenshot_path
        (merged into the top-level result by flow_runner)
    """
    from ui.pages.common.login_page import LoginPage
    from ui.pages.common.new_quote_page import NewQuotePage
    from ui.pages.common.customer_page import CustomerPage
    from ui.pages.common.quote_registration_page import QuoteRegistrationPage
    from ui.pages.auto.quote_summary_page import QuoteSummaryPage
    from ui.pages.auto.driver_info_page import DriverInfoPage
    from ui.pages.auto.vehicle_info_page import VehicleInfoPage
    from ui.pages.auto.policy_term_page import PolicyTermPage
    from ui.pages.common.policy_summary_page import PolicySummary

    outcome = "error"
    uw_conditions = []
    error = None
    policy_summary = None

    try:
        # 1. Login
        t = time.perf_counter()
        login = LoginPage(page)
        login.navigate()
        login.click_splash_button()
        login.wait_for_login_page()
        login.fill_credentials_from_env()
        login.click_login()
        page.get_by_role("button", name="quotes").wait_for(state="visible", timeout=30_000)
        _record(steps, "Login", "passed", time.perf_counter() - t)

        # 2. New Quote
        t = time.perf_counter()
        NewQuotePage(page).new_quote_steps()
        _record(steps, "New Quote", "passed", time.perf_counter() - t)

        # 3. Customer
        t = time.perf_counter()
        CustomerPage(page).customer_steps(persona)
        _record(steps, "Customer", "passed", time.perf_counter() - t)

        # 4. Quote Registration
        t = time.perf_counter()
        QuoteRegistrationPage(page).quote_registration_steps(persona)
        _record(steps, "Quote Registration", "passed", time.perf_counter() - t)

        # 5. Quote Summary
        t = time.perf_counter()
        QuoteSummaryPage(page).summary_steps(persona)
        _record(steps, "Quote Summary", "passed", time.perf_counter() - t)

        # 6. Driver Info
        t = time.perf_counter()
        DriverInfoPage(page).fill_driver_info(persona)
        _record(steps, "Driver Info", "passed", time.perf_counter() - t)

        # 7. Vehicle Info
        t = time.perf_counter()
        VehicleInfoPage(page).fill_vehicle_info(persona)
        _record(steps, "Vehicle Info", "passed", time.perf_counter() - t)

        # 8. Coverage & Rate
        t = time.perf_counter()
        if _is_uw_referral_visible(page):
            uw_conditions = _capture_uw_conditions(page)
            outcome = "uw_referral"
            _record(
                steps,
                "Coverage & Rate",
                "passed",
                time.perf_counter() - t,
                "UW referral detected before rating.",
            )
            _record(
                steps,
                "Outcome: UW Referral",
                "passed",
                0,
                f"{len(uw_conditions)} condition cell(s) captured",
            )
            return {
                "outcome": outcome,
                "uw_conditions": uw_conditions,
                "error": None,
                "screenshot_path": None,
                "policy_summary": None,
                "premium": None,
            }

        try:
            PolicyTermPage(page).policy_term_steps(persona)
            _record(steps, "Coverage & Rate", "passed", time.perf_counter() - t)
        except Exception:
            if _is_uw_referral_visible(page, timeout=5_000):
                uw_conditions = _capture_uw_conditions(page)
                outcome = "uw_referral"
                _record(
                    steps,
                    "Coverage & Rate",
                    "passed",
                    time.perf_counter() - t,
                    "UW referral detected during rating.",
                )
                _record(
                    steps,
                    "Outcome: UW Referral",
                    "passed",
                    0,
                    f"{len(uw_conditions)} condition cell(s) captured",
                )
                return {
                    "outcome": outcome,
                    "uw_conditions": uw_conditions,
                    "error": None,
                    "screenshot_path": None,
                    "policy_summary": None,
                    "premium": None,
                }
            raise

        # 9. Outcome detection
        t = time.perf_counter()
        if _is_uw_referral_visible(page, timeout=6_000):
            uw_conditions = _capture_uw_conditions(page)
            outcome = "uw_referral"
            _record(
                steps, "Outcome: UW Referral", "passed",
                time.perf_counter() - t,
                f"{len(uw_conditions)} condition cell(s) captured",
            )
        else:
            uw_result = _create_policy_or_uw(page, steps, t)
            if uw_result:
                return uw_result
            outcome = "policy_bound"
            try:
                policy_page = PolicySummary(page)
                policy_summary = policy_page.extract_details(persona)
                policy_page.save_lob_report(policy_summary)
            except Exception:
                policy_summary = None
            _record(steps, "Outcome: Policy Bound", "passed", time.perf_counter() - t)

    except Exception as exc:
        if _is_uw_referral_visible(page, timeout=8_000):
            return _record_uw_outcome(
                steps,
                "Outcome: UW Referral",
                0,
                page,
                "UW referral detected while handling a normal-flow exception.",
            )

        error = traceback.format_exc()
        # Best-effort screenshot
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            tc = persona.get("TC_ID", "unknown").replace(" ", "_")
            shot_dir = _PROJECT_ROOT / "reports" / "screenshots"
            shot_dir.mkdir(parents=True, exist_ok=True)
            shot_path = str(shot_dir / f"auto_{tc}_{ts}.png")
            page.screenshot(path=shot_path, full_page=True)
        except Exception:
            shot_path = None
        return {"outcome": "error", "uw_conditions": [], "error": error, "screenshot_path": shot_path}

    return {
        "outcome": outcome,
        "uw_conditions": uw_conditions,
        "error": None,
        "screenshot_path": None,
        "policy_summary": policy_summary,
        "premium": (policy_summary or {}).get("Total Policy Premium"),
    }
