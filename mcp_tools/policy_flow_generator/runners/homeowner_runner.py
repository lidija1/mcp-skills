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


def _emit_progress(progress_callback, phase: str, detail: str = "Homeowner"):
    if not progress_callback:
        return
    try:
        progress_callback(phase, detail)
    except Exception:
        pass


def _is_uw_referral_visible(page: Page, timeout: int = 2_000) -> bool:
    from ui.pages.auto.uw_referral_page import UWReferralPage

    return UWReferralPage(page).is_visible(timeout=timeout)


def _capture_uw_conditions(page: Page) -> list[str]:
    from ui.pages.auto.uw_referral_page import UWReferralPage

    return UWReferralPage(page).capture_conditions(timeout=5_000)


def _record_uw_outcome(steps, name: str, elapsed: float, page: Page, detail: str, progress_callback=None) -> dict:
    _emit_progress(progress_callback, "UW Referral", detail)
    uw_conditions = _capture_uw_conditions(page)
    _record(
        steps,
        name,
        "passed",
        elapsed,
        f"{detail} {len(uw_conditions)} condition cell(s) captured",
    )
    return {
        "outcome": "uw_referral",
        "uw_conditions": uw_conditions,
        "error": None,
        "screenshot_path": None,
        "premium": None,
        "policy_summary": None,
    }


def _create_policy_or_uw(page: Page, steps: list, started_at: float, progress_callback=None) -> dict | None:
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
        _emit_progress(progress_callback, action_name)
        if _is_uw_referral_visible(page, timeout=1_000):
            return _record_uw_outcome(
                steps,
                f"Outcome: UW Referral ({action_name})",
                time.perf_counter() - started_at,
                page,
                f"UW referral detected before {action_name.lower()}.",
                progress_callback,
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
                    progress_callback,
                )
            raise
        if _is_uw_referral_visible(page, timeout=1_000):
            return _record_uw_outcome(
                steps,
                f"Outcome: UW Referral ({action_name})",
                time.perf_counter() - started_at,
                page,
                f"UW referral detected after {action_name.lower()}.",
                progress_callback,
            )

    return None


def run_homeowner_flow(page: Page, persona: dict, steps: list, progress_callback=None) -> dict:
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
    from ui.pages.common.quote_registration_page import QuoteRegistrationPage
    from ui.pages.homeowner.homeowner_quote_summary_page import HomeOwnerQuoteSummaryPage
    from ui.pages.homeowner.homeowner_coverage_page import HomeownerCoveragePage
    from ui.pages.common.policy_summary_page import PolicySummary

    outcome = "error"
    uw_conditions = []
    error = None
    shot_path = None
    policy_summary = None

    try:
        # 1. Login
        _emit_progress(progress_callback, "Login")
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
        _emit_progress(progress_callback, "New Quote")
        t = time.perf_counter()
        NewQuotePage(page).new_quote_steps()
        _record(steps, "New Quote", "passed", time.perf_counter() - t)

        # 3. Customer
        _emit_progress(progress_callback, "Customer")
        t = time.perf_counter()
        CustomerPage(page).customer_steps(persona)
        _record(steps, "Customer", "passed", time.perf_counter() - t)

        # 4. Quote Registration
        _emit_progress(progress_callback, "Quote Registration")
        t = time.perf_counter()
        QuoteRegistrationPage(page).quote_registration_steps(persona)
        _record(steps, "Quote Registration", "passed", time.perf_counter() - t)

        # 5. Homeowner Quote Summary
        # summary_steps navigates: fills billing/program/radios → saves → clicks city link
        #                          → saves → clicks homeowners link (lands on coverage tab)
        _emit_progress(progress_callback, "Quote Summary")
        t = time.perf_counter()
        HomeOwnerQuoteSummaryPage(page).summary_steps(persona)
        _record(steps, "Quote Summary (HO)", "passed", time.perf_counter() - t)

        # 6. Location Coverage + Rate Quote
        # coverage_steps fills all property/construction/risk fields and ends with click_rate_quote()
        _emit_progress(progress_callback, "Location Coverage & Rate")
        t = time.perf_counter()
        HomeownerCoveragePage(page).coverage_steps(persona)
        # Wait for post-rate-quote navigation to settle
        page.wait_for_load_state("networkidle", timeout=30_000)
        _record(steps, "Location Coverage & Rate", "passed", time.perf_counter() - t)

        # 7. Outcome detection
        t = time.perf_counter()
        try:
            if not _is_uw_referral_visible(page, timeout=6_000):
                raise RuntimeError("UW referral was not visible after rating.")
            _emit_progress(progress_callback, "UW Referral")
            uw_conditions = _capture_uw_conditions(page)
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
            uw_result = _create_policy_or_uw(page, steps, t, progress_callback)
            if uw_result:
                return uw_result
            outcome = "policy_bound"
            try:
                _emit_progress(progress_callback, "Policy Summary")
                policy_page = PolicySummary(page)
                policy_summary = policy_page.extract_details(persona)
                policy_page.save_lob_report(policy_summary)
            except Exception:
                policy_summary = None
            _record(steps, "Outcome: Policy Bound", "passed", time.perf_counter() - t)

    except Exception as exc:
        error_msg = traceback.format_exc()
        # UW referral may have been triggered mid-flow (e.g. on save when
        # Refused=Yes / Loses=Yes fires a hard-stop before Rate Quote renders).
        # The navigation away from the coverage page takes a moment — wait for it.
        try:
            if not _is_uw_referral_visible(page, timeout=8_000):
                raise RuntimeError("UW referral was not visible after exception.")
            _emit_progress(progress_callback, "UW Referral", "UW referral detected while handling a normal-flow exception.")
            uw_conditions = _capture_uw_conditions(page)
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
        "premium": (policy_summary or {}).get("Total Policy Premium"),
        "policy_summary": policy_summary,
    }
