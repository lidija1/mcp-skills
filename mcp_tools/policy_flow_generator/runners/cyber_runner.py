"""
Cyber E2E runner.

Workflow:
  1. Login
  2. New Quote
  3. Customer
  4. Quote Registration
  5. Cyber Quote Details (billing, business info, coverages, eligibility)
  6. Rate Quote
  7. Outcome: UW Referral  OR  Request Issue → Delivery Prefs → Billing Plan → Bind
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


def run_cyber_flow(page: Page, persona: dict, steps: list) -> dict:
    """
    Execute the Cyber quote workflow on an already-open browser page.

    Args:
        page: Playwright page (already launched, blank new tab)
        persona: Dict matching the CyberData.json schema
        steps: List to append step result dicts to (mutated in place)

    Returns:
        Partial result dict with keys: outcome, uw_conditions, error, screenshot_path,
        premium (optional)
    """
    from ui.pages.common.login_page import LoginPage
    from ui.pages.common.new_quote_page import NewQuotePage
    from ui.pages.common.customer_page import CustomerPage
    from ui.pages.common.quote_registration_page import QuoteRegistrationPage
    from ui.pages.cyber.cyber_quote_page import CyberQuotePage
    from ui.pages.cyber.cyber_premium_summary_page import CyberPremiumSummaryPage
    from ui.pages.common.delivery_preferences_page import DeliveryPreferencesPage
    from ui.pages.common.billing_plan_page import BillingPlanPage
    from ui.pages.common.verify_billing_page import VerifyBillingPage
    from ui.pages.common.policy_summary_page import PolicySummary

    outcome = "error"
    uw_conditions = []
    error = None
    shot_path = None
    premium = None
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

        # 5. Cyber Quote Details
        t = time.perf_counter()
        cyber_quote = CyberQuotePage(page)
        cyber_quote.fill_cyber_quote_details(persona)
        _record(steps, "Cyber Quote Details", "passed", time.perf_counter() - t)

        # 6. Rate Quote
        t = time.perf_counter()
        cyber_quote.click_rate_quote()
        # Wait for page to settle after navigation triggered by rate quote
        page.wait_for_load_state("networkidle", timeout=30_000)
        _record(steps, "Rate Quote", "passed", time.perf_counter() - t)

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
            # No UW — proceed to bind via: request issue → delivery prefs → billing → bind
            summary = CyberPremiumSummaryPage(page)
            try:
                premium = summary.get_premium()
            except Exception:
                pass

            summary.click_request_issue()
            _record(steps, "Request Issue", "passed", time.perf_counter() - t)

            t = time.perf_counter()
            DeliveryPreferencesPage(page).click_next()
            _record(steps, "Delivery Preferences", "passed", time.perf_counter() - t)

            t = time.perf_counter()
            BillingPlanPage(page).complete_billing_plan(persona)
            _record(steps, "Billing Plan", "passed", time.perf_counter() - t)

            t = time.perf_counter()
            VerifyBillingPage(page).click_bind()
            outcome = "policy_bound"
            try:
                policy_page = PolicySummary(page)
                policy_summary = policy_page.extract_details(persona)
                policy_page.save_lob_report(policy_summary)
                premium = policy_summary.get("Total Policy Premium") or premium
            except Exception:
                pass
            _record(steps, "Outcome: Policy Bound (Bind)", "passed", time.perf_counter() - t)

    except Exception as exc:
        error = traceback.format_exc()
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            tc = persona.get("TC_ID", "unknown").replace(" ", "_")
            shot_dir = _PROJECT_ROOT / "reports" / "screenshots"
            shot_dir.mkdir(parents=True, exist_ok=True)
            shot_path = str(shot_dir / f"cyber_{tc}_{ts}.png")
            page.screenshot(path=shot_path, full_page=True)
        except Exception:
            pass

    return {
        "outcome": outcome,
        "uw_conditions": uw_conditions,
        "error": error,
        "screenshot_path": shot_path,
        "premium": premium,
        "policy_summary": policy_summary,
    }
