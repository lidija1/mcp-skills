"""
Flow orchestrator: sets up the browser, routes to the LOB-specific runner,
and returns a standardised result dict consumed by result_formatter.py.
"""

import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
_DASHBOARD_BACKEND = _PROJECT_ROOT / "dashboard" / "backend"
if str(_DASHBOARD_BACKEND) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD_BACKEND))

import job_store

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_PROJECT_ROOT / ".env")

from playwright.sync_api import sync_playwright  # noqa: E402

from mcp_tools.policy_flow_generator.runners.auto_runner import run_auto_flow  # noqa: E402
from mcp_tools.policy_flow_generator.runners.homeowner_runner import run_homeowner_flow  # noqa: E402

_LOB_RUNNERS = {
    "auto": run_auto_flow,
    "homeowner": run_homeowner_flow,
}
_VALID_LOBS = ", ".join(_LOB_RUNNERS)
ProgressCallback = Callable[[str, str | None], None]


class JobCanceled(Exception):
    """Raised when a running flow is canceled by the user."""


def _check_cancel(job_id: str | None):
    if job_id and job_store.is_canceled(job_id):
        raise JobCanceled("Job canceled by user")

def _emit_progress(progress_callback: ProgressCallback | None, phase: str, detail: str | None = None) -> None:
    if not progress_callback:
        return
    try:
        progress_callback(phase, detail)
    except Exception:
        pass


def run_flow(lob: str, persona: dict, progress_callback: ProgressCallback | None = None, job_id: str | None = None) -> dict[str, Any]:
    """
    Launch a browser, execute the LOB-specific policy flow, and return a result dict.

    Args:
        lob: "auto" or "homeowner"
        persona: Persona dict from persona_generator.generate_persona()

    Returns:
        {
            "tc_id":            str,
            "lob":              str,
            "persona_type":     str,
            "overall_status":   "passed" | "failed" | "uw_referral",
            "outcome":          "policy_bound" | "uw_referral" | "error",
            "uw_conditions":    list[str],
            "steps":            list[step_dict],
            "total_duration_s": float,
            "premium":          str | None,
            "error":            str | None,
            "screenshot_path":  str | None,
        }
    """
    lob = lob.lower().strip()

    result: dict[str, Any] = {
        "tc_id": persona.get("TC_ID", "AI_UNKNOWN"),
        "lob": lob,
        "persona_type": persona.get("_persona_type", "custom"),
        "overall_status": "failed",
        "outcome": "error",
        "uw_conditions": [],
        "steps": [],
        "total_duration_s": 0.0,
        "premium": None,
        "error": None,
        "screenshot_path": None,
    }

    if lob not in _LOB_RUNNERS:
        result["error"] = f"Unknown LOB '{lob}'. Valid: {_VALID_LOBS}"
        return result

    runner = _LOB_RUNNERS[lob]
    steps = result["steps"]
    wall_start = time.perf_counter()
    _emit_progress(progress_callback, "Starting browser", lob.upper())
    _check_cancel(job_id)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, slow_mo=80)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.set_default_navigation_timeout(60_000)   # 60 s per page load
        page.set_default_timeout(90_000)              # 90 s per action (click/fill/wait)

        try:
            _check_cancel(job_id)
            runner_result = runner(page, persona, steps, progress_callback=progress_callback)

            result["outcome"] = runner_result.get("outcome", "error")
            result["uw_conditions"] = runner_result.get("uw_conditions", [])
            result["error"] = runner_result.get("error")
            result["screenshot_path"] = runner_result.get("screenshot_path")
            result["premium"] = runner_result.get("premium")
            result["policy_summary"] = runner_result.get("policy_summary")

            if result["outcome"] == "policy_bound":
                result["overall_status"] = "passed"
            elif result["outcome"] == "uw_referral":
                result["overall_status"] = "uw_referral"
            else:
                result["overall_status"] = "failed"

        except JobCanceled:
            raise
        except Exception as exc:
            _emit_progress(progress_callback, "Error", "Flow failed")
            result["error"] = traceback.format_exc()
            result["overall_status"] = "failed"
            try:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                tc = persona.get("TC_ID", "unknown")
                shot_dir = _PROJECT_ROOT / "reports" / "screenshots"
                shot_dir.mkdir(parents=True, exist_ok=True)
                shot_path = str(shot_dir / f"{lob}_{tc}_{ts}.png")
                page.screenshot(path=shot_path, full_page=True)
                result["screenshot_path"] = shot_path
            except Exception:
                pass

        finally:
            result["total_duration_s"] = round(time.perf_counter() - wall_start, 2)
            context.close()
            browser.close()

    return result
