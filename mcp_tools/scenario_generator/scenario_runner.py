"""
Scenario runner: executes a Personal Auto quote workflow against the live
application using the existing page-object model — no pytest required.

Workflow steps
--------------
  1. Login
  2. New Quote
  3. Customer
  4. Quote Registration
  5. Quote Summary  (+ driver navigation)
  6. Driver Info
  7. Vehicle Info
  8. Coverage & Rate
  9. Outcome detection — UW referral  OR  policy bind

Returns a structured result dict consumed by result_formatter.py.
"""

import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup — must happen before any ui.* / utils.* imports
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_PROJECT_ROOT / ".env")

from playwright.sync_api import sync_playwright  # noqa: E402

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _record(steps: list, name: str, status: str, elapsed: float, detail: str = "") -> None:
    steps.append(
        {
            "step": name,
            "status": status,
            "duration_s": round(elapsed, 2),
            "detail": detail,
        }
    )


def _fail(steps: list, name: str, elapsed: float, exc: Exception) -> None:
    _record(steps, name, "failed", elapsed, str(exc))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_scenario(test_data: dict) -> dict[str, Any]:
    """
    Execute a Personal Auto quote workflow and return a structured result.

    Args:
        test_data: Dict matching the AutoData.json schema.  Must contain at
                   minimum all fields required by each page-object step.

    Returns:
        {
            "tc_id":            str,
            "description":      str,
            "overall_status":   "passed" | "failed" | "uw_referral",
            "outcome":          "policy_bound" | "uw_referral" | "error",
            "uw_conditions":    list[str],
            "steps":            list[step_dict],
            "total_duration_s": float,
            "error":            str | None,
            "screenshot_path":  str | None,
        }
    """
    # Lazy page-object imports (sys.path already extended above)
    from ui.pages.common.login_page import LoginPage
    from ui.pages.common.new_quote_page import NewQuotePage
    from ui.pages.common.customer_page import CustomerPage
    from ui.pages.auto.quote_registration_page import QuoteRegistrationPage
    from ui.pages.auto.quote_summary_page import QuoteSummaryPage
    from ui.pages.auto.driver_info_page import DriverInfoPage
    from ui.pages.auto.vehicle_info_page import VehicleInfoPage
    from ui.pages.auto.policy_term_page import PolicyTermPage
    from ui.pages.auto.create_policy_page import CreatePolicyPage

    result: dict[str, Any] = {
        "tc_id": test_data.get("TC_ID", "AI_UNKNOWN"),
        "description": test_data.get("UW_Description", test_data.get("UW_Rule", "")),
        "overall_status": "failed",
        "outcome": "error",
        "uw_conditions": [],
        "steps": [],
        "total_duration_s": 0.0,
        "error": None,
        "screenshot_path": None,
    }
    steps = result["steps"]
    wall_start = time.perf_counter()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, slow_mo=80)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        try:
            # ── 1. Login ─────────────────────────────────────────────────────
            t = time.perf_counter()
            login = LoginPage(page)
            login.navigate()
            login.click_splash_button()
            login.wait_for_login_page()
            login.fill_credentials_from_env()
            login.click_login()
            # Wait until the quotes button confirms a successful home page load
            page.get_by_role("button", name="quotes").wait_for(
                state="visible", timeout=30_000
            )
            _record(steps, "Login", "passed", time.perf_counter() - t)

            # ── 2. New Quote ──────────────────────────────────────────────────
            t = time.perf_counter()
            NewQuotePage(page).new_quote_steps()
            _record(steps, "New Quote", "passed", time.perf_counter() - t)

            # ── 3. Customer ───────────────────────────────────────────────────
            t = time.perf_counter()
            CustomerPage(page).customer_steps(test_data)
            _record(steps, "Customer", "passed", time.perf_counter() - t)

            # ── 4. Quote Registration ─────────────────────────────────────────
            t = time.perf_counter()
            QuoteRegistrationPage(page).quote_registration_steps(test_data)
            _record(steps, "Quote Registration", "passed", time.perf_counter() - t)

            # ── 5. Quote Summary ──────────────────────────────────────────────
            t = time.perf_counter()
            QuoteSummaryPage(page).summary_steps(test_data)
            _record(steps, "Quote Summary", "passed", time.perf_counter() - t)

            # ── 6. Driver Info ────────────────────────────────────────────────
            t = time.perf_counter()
            DriverInfoPage(page).fill_driver_info(test_data)
            _record(steps, "Driver Info", "passed", time.perf_counter() - t)

            # ── 7. Vehicle Info ───────────────────────────────────────────────
            t = time.perf_counter()
            VehicleInfoPage(page).fill_vehicle_info(test_data)
            _record(steps, "Vehicle Info", "passed", time.perf_counter() - t)

            # ── 8. Coverage & Rate ────────────────────────────────────────────
            t = time.perf_counter()
            PolicyTermPage(page).policy_term_steps(test_data)
            _record(steps, "Coverage & Rate", "passed", time.perf_counter() - t)

            # ── 9. Outcome detection ──────────────────────────────────────────
            t = time.perf_counter()
            uw_breadcrumb = page.locator("text=underwriting referral")

            try:
                uw_breadcrumb.first.wait_for(state="visible", timeout=6_000)
                # UW referral page — harvest all visible gridcell text
                cells = page.get_by_role("gridcell").all()
                conditions = [
                    c.inner_text().strip()
                    for c in cells
                    if c.inner_text().strip()
                ]
                result["uw_conditions"] = conditions
                result["outcome"] = "uw_referral"
                result["overall_status"] = "uw_referral"
                _record(
                    steps,
                    "Outcome: UW Referral",
                    "passed",
                    time.perf_counter() - t,
                    f"{len(conditions)} gridcell(s) captured",
                )

            except Exception:
                # No UW referral — proceed to bind
                try:
                    CreatePolicyPage(page).policy_creation_steps()
                    result["outcome"] = "policy_bound"
                    result["overall_status"] = "passed"
                    _record(
                        steps, "Outcome: Policy Bound", "passed", time.perf_counter() - t
                    )
                except Exception as bind_exc:
                    _fail(steps, "Outcome: Bind Attempt", time.perf_counter() - t, bind_exc)
                    raise bind_exc

        except Exception as exc:
            result["error"] = traceback.format_exc()
            result["overall_status"] = "failed"

            # Best-effort failure screenshot
            try:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                tc = test_data.get("TC_ID", "unknown").replace(" ", "_")
                shot_dir = _PROJECT_ROOT / "reports" / "screenshots"
                shot_dir.mkdir(parents=True, exist_ok=True)
                shot_path = str(shot_dir / f"ai_scenario_{tc}_{ts}.png")
                page.screenshot(path=shot_path, full_page=True)
                result["screenshot_path"] = shot_path
            except Exception:
                pass

        finally:
            result["total_duration_s"] = round(time.perf_counter() - wall_start, 2)
            context.close()
            browser.close()

    return result
