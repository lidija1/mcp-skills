"""
Homeowner E2E runner.

Workflow:
  1. Login
  2. New Quote
  3. Customer
  4. Quote Registration
  5. Quote Summary HO (billing method, program type, eligibility radios, navigation)
  6. Location Coverage (property details, construction, risk radios, rate quote)
  7. Outcome: UW Referral  OR  Policy Bind (request issue → next → next → bind)
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


def run_homeowner_flow(page: Page, persona: dict, steps: list) -> dict:
    """
    Execute the Homeowner quote workflow on an already-open browser page.

    Args:
        page: Playwright page (already launched, blank new tab)
        persona: Dict matching the HomeData.json schema
        steps: List to append step result dicts to (mutated in place)

    Returns:
        Partial result dict with keys: outcome, uw_conditions, error, screenshot_path
    """
    from ui.pages.common.login_page import LoginPage
    from ui.pages.common.new_quote_page import NewQuotePage
    from ui.pages.common.customer_page import CustomerPage
    from ui.pages.auto.quote_registration_page import QuoteRegistrationPage
    from ui.pages.homeowner.homeowner_quote_summary_page import HomeOwnerQuoteSummaryPage
    from ui.pages.homeowner.homeowner_coverage_page import HomeownerCoveragePage
    from ui.pages.auto.create_policy_page import CreatePolicyPage

    outcome = "error"
    uw_conditions = []
    error = None
    shot_path = None

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

        # 5. Homeowner Quote Summary
        # summary_steps navigates: fills billing/program/radios → saves → clicks city link
        #                          → saves → clicks homeowners link (lands on coverage tab)
        t = time.perf_counter()
        HomeOwnerQuoteSummaryPage(page).summary_steps(persona)
        _record(steps, "Quote Summary (HO)", "passed", time.perf_counter() - t)

        # 6. Location Coverage + Rate Quote
        # coverage_steps fills all property/construction/risk fields and ends with click_rate_quote()
        t = time.perf_counter()
        HomeownerCoveragePage(page).coverage_steps(persona)
        # Wait for post-rate-quote navigation to settle
        page.wait_for_load_state("networkidle", timeout=30_000)
        _record(steps, "Location Coverage & Rate", "passed", time.perf_counter() - t)

        # 7. Outcome detection
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
            # No UW — proceed to bind via CreatePolicyPage
            # policy_creation_steps: request issue → wait → next (delivery prefs)
            #                        → wait → next (billing plan) → wait → bind
            CreatePolicyPage(page).policy_creation_steps()
            outcome = "policy_bound"
            _record(steps, "Outcome: Policy Bound", "passed", time.perf_counter() - t)

    except Exception as exc:
        error_msg = traceback.format_exc()
        # UW referral may have been triggered mid-flow (e.g. on save when
        # Refused=Yes / Loses=Yes fires a hard-stop before Rate Quote renders).
        # The navigation away from the coverage page takes a moment — wait for it.
        try:
            uw_breadcrumb = page.locator("text=underwriting referral")
            uw_breadcrumb.first.wait_for(state="visible", timeout=8_000)
            cells = page.get_by_role("gridcell").all()
            uw_conditions = [c.inner_text().strip() for c in cells if c.inner_text().strip()]
            outcome = "uw_referral"
            error = None
        except Exception:
            pass

        if outcome == "error":
            error = error_msg
            try:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                tc = persona.get("TC_ID", "unknown").replace(" ", "_")
                shot_dir = _PROJECT_ROOT / "reports" / "screenshots"
                shot_dir.mkdir(parents=True, exist_ok=True)
                shot_path = str(shot_dir / f"homeowner_{tc}_{ts}.png")
                page.screenshot(path=shot_path, full_page=True)
            except Exception:
                pass

    return {
        "outcome": outcome,
        "uw_conditions": uw_conditions,
        "error": error,
        "screenshot_path": shot_path,
        "premium": None,
    }
