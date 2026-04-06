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
    from ui.pages.auto.quote_registration_page import QuoteRegistrationPage
    from ui.pages.auto.quote_summary_page import QuoteSummaryPage
    from ui.pages.auto.driver_info_page import DriverInfoPage
    from ui.pages.auto.vehicle_info_page import VehicleInfoPage
    from ui.pages.auto.policy_term_page import PolicyTermPage
    from ui.pages.auto.create_policy_page import CreatePolicyPage

    outcome = "error"
    uw_conditions = []
    error = None

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
        PolicyTermPage(page).policy_term_steps(persona)
        _record(steps, "Coverage & Rate", "passed", time.perf_counter() - t)

        # 9. Outcome detection
        t = time.perf_counter()
        uw_breadcrumb = page.locator("text=underwriting referral")
        try:
            uw_breadcrumb.first.wait_for(state="visible", timeout=6_000)
            cells = page.get_by_role("gridcell").all()
            uw_conditions = [c.inner_text().strip() for c in cells if c.inner_text().strip()]
            outcome = "uw_referral"
            _record(
                steps, "Outcome: UW Referral", "passed",
                time.perf_counter() - t,
                f"{len(uw_conditions)} condition cell(s) captured",
            )
        except Exception:
            CreatePolicyPage(page).policy_creation_steps()
            outcome = "policy_bound"
            _record(steps, "Outcome: Policy Bound", "passed", time.perf_counter() - t)

    except Exception as exc:
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

    return {"outcome": outcome, "uw_conditions": uw_conditions, "error": None, "screenshot_path": None}
