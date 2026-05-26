"""
MCP Server — OneShield QA.

API-layer UW test runner and app state validator. Uses OneShieldApiReplay
(requests-based, no browser) to drive Auto policy flows and assert
conditions / field values at any stage.

Exposes four tools:

  run_uw_api_test      Run a single UW API test case, assert expected conditions
  run_uw_api_batch     Run all / specified UW cases in one call
  validate_stage_data  Run to a stage and assert specific field values
  inspect_app_state    Run to a stage and return a readable page state dump

──────────────────────────────────────────────────────────────────────────────
REGISTER IN .mcp.json
──────────────────────────────────────────────────────────────────────────────

  "oneshield-qa": {
    "command": "C:/Programming/SandboxPlaywrightMCP/.venv/Scripts/python.exe",
    "args": ["-m", "mcp_tools.oneshield_qa.server"],
    "cwd": "C:/Programming/SandboxPlaywrightMCP",
    "env": { "PYTHONUTF8": "1" }
  }

──────────────────────────────────────────────────────────────────────────────
USAGE EXAMPLES
──────────────────────────────────────────────────────────────────────────────

  run_uw_api_test("UW_TC_007")
  run_uw_api_batch(["UW_TC_001", "UW_TC_007"])
  run_uw_api_batch()   # all 14 cases

  validate_stage_data("TC_ID_0001", "rate", {
      "page_name_contains": "premium",
      "Premium": "$ 1,",
      "has_action": "request issue"
  })

  inspect_app_state("UW_TC_003", "rate")
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_PROJECT_ROOT / ".env")

from mcp.server.fastmcp import FastMCP  # noqa: E402

from mcp_tools.oneshield_qa.report_formatter import (  # noqa: E402
    format_uw_api_report,
    format_uw_batch_report,
    format_assertion_report,
    format_state_dump,
)

# ---------------------------------------------------------------------------
# Known expected UW conditions per TC_ID  (mirrors test_oneshield_api_uw_rules.py)
# ---------------------------------------------------------------------------

_SR22 = "SR-22 / Certificate of Insurance Indicator is checked"
_LIC  = "driver license status that is revoked or suspended"
_U25  = "All drivers under 25 years of age"

AUTO_UW_EXPECTED: dict[str, list[str]] = {
    "UW_TC_001": [_SR22],
    "UW_TC_002": [_LIC],
    "UW_TC_003": [_U25],
    "UW_TC_004": [_LIC],
    "UW_TC_005": [_SR22, _U25],
    "UW_TC_006": [_SR22, _LIC],
    "UW_TC_007": [_SR22, _LIC, _U25],
    "UW_TC_008": [_U25],
    "UW_TC_009": [_LIC, _U25],
    "UW_TC_010": [_SR22],
    "UW_TC_011": [_U25],
    "UW_TC_012": [_SR22, _LIC],
    "UW_TC_013": [_SR22],
    "UW_TC_014": [_U25],
}

_UW_DATA   = _PROJECT_ROOT / "testdata" / "static" / "auto" / "AutoUWRulesData.json"
_AUTO_DATA = _PROJECT_ROOT / "testdata" / "static" / "auto" / "AutoData.json"
_VALID_STAGES = ("rate", "rating-detail", "request-issue", "billing-plan", "verify-billing")

# ---------------------------------------------------------------------------
# Server definition
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "oneshield-qa",
    instructions=(
        "OneShield QA tools — API-layer UW test runner and app state validator. "
        "No browser required: uses captured UI traffic replayed via HTTP requests. "
        "Use run_uw_api_test for a single UW_TC_XXX case (checks expected UW conditions). "
        "Use run_uw_api_batch to sweep all 14 Auto UW cases in one call. "
        "Use validate_stage_data to assert field values / page state at any flow stage. "
        "Use inspect_app_state to dump all visible fields, grids, and actions at a stage."
    ),
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_credentials() -> str | None:
    missing = [v for v in ("PARTNER_NUM", "USERNAMEE", "PASSWORD") if not os.getenv(v)]
    if missing:
        return (
            f"**ERROR** — Missing env var(s): {', '.join(missing)}. "
            "Add them to the project .env file and restart the MCP server."
        )
    return None


def _load_test_data(tc_id: str, data_file: str = "") -> tuple[dict, str] | None:
    from api_tests.oneshield_api_replay import load_auto_test_data

    paths: list[Path] = []
    if data_file:
        paths.append(Path(data_file))
    paths += [_UW_DATA, _AUTO_DATA]

    for path in paths:
        try:
            data = load_auto_test_data(path, tc_id)
            return data, str(path)
        except (LookupError, FileNotFoundError):
            continue
    return None


def _run_api_flow(test_data: dict, stop_after: str = "rate") -> dict:
    from api_tests.oneshield_api_replay import OneShieldApiReplay

    client = OneShieldApiReplay()
    try:
        return client.run_captured_auto_flow(test_data, stop_after=stop_after)
    finally:
        client.close()


def _stage_ui(result: dict, stage: str) -> dict:
    return result.get("stage_ui_data", {}).get(stage, result.get("ui_data", {}))


def _uw_conditions_pass(result: dict, expected: list[str]) -> bool:
    rate_ui = _stage_ui(result, "rate")
    row_texts = [
        " | ".join(str(v) for v in row.values())
        for grid in rate_ui.get("grids", [])
        for row in grid.get("rows", [])
    ]
    return (
        result.get("completed", False)
        and not result.get("blocked_reason")
        and all(
            any("Underwriting" in row and cond in row for row in row_texts)
            for cond in expected
        )
    )


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def run_uw_api_test(tc_id: str, data_file: str = "") -> str:
    """
    Run a single Auto UW API test case and assert expected conditions appear.

    Uses the API replay layer (HTTP requests, no browser) to drive the Auto
    quote flow to the rating stage, then checks the UW referral grid for the
    expected conditions registered for that TC_ID.

    Args:
        tc_id: Test case ID — "UW_TC_001" through "UW_TC_014"
        data_file: Optional path to a custom AutoUWRulesData.json
                   (defaults to testdata/static/auto/AutoUWRulesData.json)

    Returns:
        Markdown report: page reached, conditions found/missing, full UW grid.

    Registered expected conditions:
      UW_TC_001/010/013 — SR-22 checked
      UW_TC_002/004     — revoked/suspended licence
      UW_TC_003/008/011/014 — under 25
      UW_TC_005         — SR-22 + under 25
      UW_TC_006/012     — SR-22 + revoked licence
      UW_TC_007         — SR-22 + revoked + under 25
      UW_TC_009         — revoked + under 25
    """
    err = _check_credentials()
    if err:
        return err

    tc_id = tc_id.upper().strip()
    if tc_id not in AUTO_UW_EXPECTED:
        return (
            f"**ERROR** — Unknown TC_ID `{tc_id}`.\n\n"
            f"Valid IDs: {', '.join(f'`{k}`' for k in sorted(AUTO_UW_EXPECTED))}"
        )

    loaded = _load_test_data(tc_id, data_file)
    if not loaded:
        return f"**ERROR** — TC_ID `{tc_id}` not found in any data file."

    test_data, _ = loaded
    result = _run_api_flow(test_data, stop_after="rate")
    return format_uw_api_report(tc_id, test_data, result, AUTO_UW_EXPECTED[tc_id])


@mcp.tool()
def run_uw_api_batch(tc_ids: list = None) -> str:
    """
    Run multiple Auto UW API test cases and return a combined pass/fail report.

    Cases run in parallel (up to 6 concurrent) through the API replay layer (no browser).
    All 14 registered cases run when tc_ids is omitted.

    Args:
        tc_ids: Optional list of TC IDs, e.g. ["UW_TC_001", "UW_TC_007"].
                Omit or pass empty list to run all 14 cases.

    Returns:
        Markdown summary table (PASS/FAIL per case) + failure detail section.
        Each row shows: TC_ID, status, expected conditions, page reached.

    Note: Each case is a separate HTTP session (~15–30 s each).
          All 14 cases take approximately 1–2 minutes with parallel execution (max 6 workers).
    """
    err = _check_credentials()
    if err:
        return err

    target_ids = [tc.upper().strip() for tc in (tc_ids or [])] or sorted(AUTO_UW_EXPECTED)

    def _run_one(tc_id: str) -> dict:
        if tc_id not in AUTO_UW_EXPECTED:
            return {"tc_id": tc_id, "error": "Unknown TC_ID — not in registry", "passed": False}
        loaded = _load_test_data(tc_id)
        if not loaded:
            return {"tc_id": tc_id, "error": "TC_ID not found in data files", "passed": False}
        test_data, _ = loaded
        try:
            flow_result = _run_api_flow(test_data, stop_after="rate")
        except Exception as exc:
            return {"tc_id": tc_id, "error": str(exc)[:120], "passed": False}
        return {
            "tc_id": tc_id,
            "result": flow_result,
            "expected": AUTO_UW_EXPECTED[tc_id],
            "passed": _uw_conditions_pass(flow_result, AUTO_UW_EXPECTED[tc_id]),
        }

    results_map: dict = {}
    with ThreadPoolExecutor(max_workers=min(len(target_ids), 6)) as pool:
        futures = {pool.submit(_run_one, tc_id): tc_id for tc_id in target_ids}
        for future in as_completed(futures):
            r = future.result()
            results_map[r["tc_id"]] = r

    results = [results_map[tc_id] for tc_id in target_ids]
    return format_uw_batch_report(results)


@mcp.tool()
def validate_stage_data(
    tc_id: str,
    stage: str,
    assertions: dict,
    data_file: str = "",
) -> str:
    """
    Run to a stage and assert specific field values from the UI data model.

    Drives the Auto API flow to the target stage, then evaluates each
    assertion against the captured page state.

    Args:
        tc_id: Test case ID from AutoData.json or AutoUWRulesData.json,
               e.g. "TC_ID_0001", "UW_TC_007"
        stage: Flow stage — one of:
               "rate", "rating-detail", "request-issue",
               "billing-plan", "verify-billing"
        assertions: Dict of assertions. Supported keys:
            "page_name_contains" — page name includes this string (case-insensitive)
            "has_action"         — action bar has a button with this label
            "no_messages"        — message list is empty
            <field label>        — field has a value containing the expected string
            Example:
            {
              "page_name_contains": "premium",
              "Premium": "$ 1,",
              "Billing Method": "Direct Billed",
              "has_action": "request issue"
            }
        data_file: Optional path to a custom test data JSON file

    Returns:
        Markdown report — each assertion with PASS/FAIL and actual value.
    """
    err = _check_credentials()
    if err:
        return err

    stage = stage.lower().strip()
    if stage not in _VALID_STAGES:
        return f"**ERROR** — invalid stage `{stage}`. Valid: {', '.join(_VALID_STAGES)}"

    tc_id = tc_id.upper().strip()
    loaded = _load_test_data(tc_id, data_file)
    if not loaded:
        return f"**ERROR** — TC_ID `{tc_id}` not found in any data file."

    test_data, _ = loaded
    result = _run_api_flow(test_data, stop_after=stage)
    ui_data = _stage_ui(result, stage)
    return format_assertion_report(tc_id, stage, ui_data, assertions, result)


@mcp.tool()
def inspect_app_state(tc_id: str, stage: str = "rate", data_file: str = "") -> str:
    """
    Run to a stage and return a readable dump of the OneShield page state.

    Use for discovery and debugging: see every visible field, grid, action
    button, tab, and message the API layer exposes at any flow stage.

    Args:
        tc_id: Test case ID from AutoData.json or AutoUWRulesData.json,
               e.g. "TC_ID_0001", "UW_TC_003"
        stage: "rate" (default), "rating-detail", "request-issue",
               "billing-plan", or "verify-billing"
        data_file: Optional path to a custom test data JSON file

    Returns:
        Markdown page state dump: page name, all visible fields with
        display values, grids with rows, action/tab buttons, messages.

    Typical uses:
        - Discover what fields are available at the premium summary page
        - See exact UW condition text before writing an assertion
        - Debug a failing validate_stage_data assertion
    """
    err = _check_credentials()
    if err:
        return err

    stage = stage.lower().strip()
    if stage not in _VALID_STAGES:
        return f"**ERROR** — invalid stage `{stage}`. Valid: {', '.join(_VALID_STAGES)}"

    tc_id = tc_id.upper().strip()
    loaded = _load_test_data(tc_id, data_file)
    if not loaded:
        return f"**ERROR** — TC_ID `{tc_id}` not found in any data file."

    test_data, _ = loaded
    result = _run_api_flow(test_data, stop_after=stage)
    ui_data = _stage_ui(result, stage)
    return format_state_dump(tc_id, stage, ui_data, result)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
