"""
MCP Server — AI Scenario Generator for Personal Auto policy testing.

Exposes three tools:

  generate_scenario      NL description → structured test-data JSON
  execute_scenario       Test-data JSON → live browser execution + result report
  generate_and_execute   Combined convenience tool (NL → run → report)

─────────────────────────────────────────────────────────────────────────────
HOW TO REGISTER IN CLAUDE CODE  (~/.claude/settings.json or project settings)
─────────────────────────────────────────────────────────────────────────────

  "mcpServers": {
    "auto-scenario-generator": {
      "command": "python",
      "args": ["-m", "mcp_tools.scenario_generator.server"],
      "cwd": "C:/Projects/SandboxPlaywright"
    }
  }

NOTE: Do NOT add API keys to settings.json or settings.local.json.
      The server reads ANTHROPIC_API_KEY (and optionally OPENAI_API_KEY)
      from the project .env file at startup.  Keep all secrets there.

─────────────────────────────────────────────────────────────────────────────
USAGE EXAMPLES
─────────────────────────────────────────────────────────────────────────────

  # Quick end-to-end: plain English → execute → report
  generate_and_execute("High-risk driver with SR-22 and suspended licence on a leased vehicle")

  # Two-step: generate first, review JSON, then run
  json_data = generate_scenario("Young driver aged 20 with revoked licence, business use")
  execute_scenario(json_data)

  # Standard clean scenario (should bind successfully)
  generate_and_execute("Standard adult driver, clean record, owned vehicle, commute use")

─────────────────────────────────────────────────────────────────────────────
"""

import json
import sys
from pathlib import Path

# Ensure the project root is on sys.path so ui.* / utils.* resolve when the
# server is started via `python -m mcp_tools.scenario_generator.server`
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from mcp_tools.scenario_generator.ai_translator import translate_scenario  # noqa: E402
from mcp_tools.scenario_generator.result_formatter import format_result  # noqa: E402
from mcp_tools.scenario_generator.scenario_runner import run_scenario  # noqa: E402

# ---------------------------------------------------------------------------
# Server definition
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "auto-scenario-generator",
    instructions=(
        "Generate and execute Personal Auto insurance policy test scenarios "
        "from plain-English descriptions using the OneShield Playwright framework. "
        "Call generate_and_execute for a one-shot flow, or generate_scenario + "
        "execute_scenario separately to inspect and optionally edit the test data "
        "before running."
    ),
)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def generate_scenario(description: str) -> str:
    """
    Translate a plain-English test scenario into structured JSON test data.

    The returned JSON matches the AutoData.json schema used by the Personal
    Auto Playwright framework and includes all fields required for a full
    end-to-end quote workflow (customer, quote registration, driver, vehicle,
    coverage).

    Args:
        description: Natural-language scenario, e.g.
            "High-risk driver with SR-22 and suspended licence on a leased BMW."
            "Young driver aged 19 with a revoked licence, business-use vehicle."
            "Standard middle-aged driver, clean record, owned vehicle."

    Returns:
        JSON string with all test-data fields, or a JSON error object if
        the AI translation fails.
    """
    return translate_scenario(description)


@mcp.tool()
def execute_scenario(test_data_json: str) -> str:
    """
    Execute a Personal Auto quote scenario against the live application.

    Launches a headless Chromium browser and drives the full workflow:
    login → new quote → customer → quote registration → quote summary →
    driver info → vehicle info → coverage & rate → outcome detection.

    Detects automatically whether a UW soft-referral fires (SR-22, suspended/
    revoked licence, driver under 25) or the quote proceeds to policy bind.

    Args:
        test_data_json: JSON string matching the AutoData.json schema.
            Typically the output of generate_scenario(), but hand-crafted
            JSON is also accepted.

    Returns:
        Markdown result report with per-step status, timing, UW conditions
        (if triggered), and a failure screenshot path on error.
    """
    try:
        test_data = json.loads(test_data_json)
    except json.JSONDecodeError as exc:
        return f"**ERROR** — invalid JSON supplied to execute_scenario: {exc}"

    if test_data.get("error"):
        return f"**ERROR** — test data contains an error key: {test_data['error']}"

    result = run_scenario(test_data)
    return format_result(result)


@mcp.tool()
def generate_and_execute(description: str) -> str:
    """
    Translate a plain-English scenario description, execute it immediately,
    and return a combined report.

    This is the primary tool for interactive use: one call goes from natural
    language all the way to execution results without an intermediate step.

    Args:
        description: Natural-language scenario, e.g.
            "Auto policy with a high-risk driver and multiple prior accidents."
            "Triple-risk: SR-22, revoked licence, and driver under 25."
            "Clean record, standard adult, leased vehicle, Gold coverage."

    Returns:
        Markdown document containing:
          1. The generated test data JSON (for transparency / reuse)
          2. The full execution result report
    """
    # Step 1 — translate
    test_data_json = translate_scenario(description)

    try:
        test_data = json.loads(test_data_json)
    except json.JSONDecodeError:
        return (
            f"**ERROR** — AI translator returned non-JSON output:\n\n"
            f"```\n{test_data_json}\n```"
        )

    if test_data.get("error"):
        return f"**ERROR** generating scenario: {test_data['error']}"

    # Step 2 — execute
    result = run_scenario(test_data)
    report = format_result(result)

    return (
        "## Generated Test Data\n\n"
        f"```json\n{json.dumps(test_data, indent=2)}\n```\n\n"
        "---\n\n"
        f"{report}"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
