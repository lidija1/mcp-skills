"""
MCP Server — Policy Flow Generator (multi-LOB).

Exposes five tools:

  list_persona_archetypes   List available persona archetypes per LOB
  create_persona            NL description → structured persona JSON (Auto/Cyber/Homeowner)
  run_policy_flow           Persona JSON → live E2E browser execution + report
  run_full_policy_flow      Combined: NL → persona → execute → report (one shot)
  run_batch_flows           Run multiple NL descriptions across LOBs in one call

──────────────────────────────────────────────────────────────────────────────
REGISTER IN CLAUDE CODE  (~/.claude/settings.json or project .claude/settings.json)
──────────────────────────────────────────────────────────────────────────────

  "mcpServers": {
    "policy-flow-generator": {
      "command": "python",
      "args": ["-m", "mcp_tools.policy_flow_generator.server"],
      "cwd": "C:/Projects/SandboxPlaywright"
    }
  }

NOTE: Do NOT add API keys to settings.json or settings.local.json.
      The server reads ANTHROPIC_API_KEY (and optionally OPENAI_API_KEY)
      from the project .env file at startup.  Keep all secrets there.

──────────────────────────────────────────────────────────────────────────────
USAGE EXAMPLES
──────────────────────────────────────────────────────────────────────────────

  # List all available persona archetypes
  list_persona_archetypes()
  list_persona_archetypes("cyber")

  # One-shot: NL → execute → report
  run_full_policy_flow("auto", "Young driver aged 21 with SR-22 on a leased BMW")
  run_full_policy_flow("cyber", "E-commerce startup, no cyber training, past ransomware attack")
  run_full_policy_flow("homeowner", "High-value home with prior losses and refused coverage")

  # Two-step: inspect persona JSON before running
  persona_json = create_persona("auto", "Triple-risk: SR-22, revoked licence, under 25")
  run_policy_flow("auto", persona_json)

  # Batch: multiple scenarios at once
  run_batch_flows([
    {"lob": "auto", "description": "Clean standard driver, Gold coverage"},
    {"lob": "cyber", "description": "Small office with good cyber hygiene"},
    {"lob": "homeowner", "description": "New construction, low risk"},
  ])
──────────────────────────────────────────────────────────────────────────────
"""

import concurrent.futures
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from mcp_tools.policy_flow_generator.persona_generator import (  # noqa: E402
    generate_persona,
    list_archetypes,
)
from mcp_tools.policy_flow_generator.flow_runner import run_flow  # noqa: E402
from mcp_tools.policy_flow_generator.result_formatter import (  # noqa: E402
    format_result,
    format_batch_summary,
)

# ---------------------------------------------------------------------------
# Server definition
# ---------------------------------------------------------------------------

MAX_BATCH_SIZE = 25  # hard cap — each scenario launches a browser session (~60-120 s)


def _run_flow_threaded(lob: str, persona: dict) -> dict:
    """Wrap run_flow in a dedicated thread so Playwright's sync API does not
    conflict with FastMCP's running asyncio event loop."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(run_flow, lob, persona).result()

mcp = FastMCP(
    "policy-flow-generator",
    instructions=(
        "Generate realistic insurance personas and execute full end-to-end policy "
        "flows (quote → UW check → bind) for Personal Auto, Cyber, and Homeowner "
        "lines of business. "
        "Use list_persona_archetypes to see available personas. "
        "Use run_full_policy_flow for one-shot NL → execute → report. "
        "Use create_persona + run_policy_flow for a two-step inspect-then-run flow. "
        "Use run_batch_flows to test multiple scenarios at once."
    ),
)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def list_persona_archetypes(lob: str = "") -> str:
    """
    List available persona archetypes for one or all lines of business.

    Each archetype maps to a curated set of risk characteristics and field
    values that produce realistic, immediately runnable test data.

    Args:
        lob: Optional LOB filter — "auto", "cyber", or "homeowner".
             Omit (or pass empty string) to see all LOBs.

    Returns:
        Formatted list of persona archetypes with brief descriptions.
    """
    return list_archetypes(lob if lob else None)


@mcp.tool()
def create_persona(lob: str, description: str) -> str:
    """
    Generate a realistic insurance persona JSON for the given line of business.

    Uses Claude AI to translate a natural-language description into structured
    test data matching the exact field schema required by the policy workflow.

    Args:
        lob: Line of business — "auto", "cyber", or "homeowner"
        description: Natural-language persona, e.g.
            "Young driver aged 21 with SR-22 on a leased BMW" (auto)
            "Healthcare business, 20 employees, strong compliance posture" (cyber)
            "Luxury coastal home, tile roof, Platinum coverage" (homeowner)

    Returns:
        JSON string with all LOB-specific fields, or a JSON error object.
    """
    return generate_persona(lob, description)


@mcp.tool()
def run_policy_flow(lob: str, persona_json: str) -> str:
    """
    Execute a full end-to-end insurance policy flow for the given persona.

    Launches a headless browser and drives the complete workflow:
    - Auto:       login → quote → customer → registration → driver/vehicle → coverage/rate → UW check → bind
    - Cyber:      login → quote → customer → registration → cyber details → rate → UW check → issue → delivery → billing → bind
    - Homeowner:  login → quote → customer → registration → HO summary → coverage/rate → UW check → bind

    Automatically detects UW soft-referrals (captures all condition rows)
    or proceeds to policy bind.

    Args:
        lob: Line of business — "auto", "cyber", or "homeowner"
        persona_json: JSON string from create_persona() or hand-crafted data

    Returns:
        Markdown report: step-by-step results, timing, UW conditions (if any),
        premium (Cyber), and failure screenshot path on error.
    """
    try:
        persona = json.loads(persona_json)
    except json.JSONDecodeError as exc:
        return f"**ERROR** — invalid JSON: {exc}"

    if persona.get("error"):
        return f"**ERROR** — persona contains error: {persona['error']}"

    result = _run_flow_threaded(lob, persona)
    return format_result(result)


@mcp.tool()
def run_full_policy_flow(lob: str, description: str) -> str:
    """
    Translate a plain-English persona and immediately execute the full policy flow.

    One-shot convenience: NL description → AI-generated persona JSON →
    live browser execution → result report.

    Args:
        lob: Line of business — "auto", "cyber", or "homeowner"
        description: Natural-language persona, e.g.
            "Triple-risk: SR-22, revoked licence, under 25" (auto)
            "E-commerce startup with no cyber training and past data breach" (cyber)
            "Luxury home worth $1.5M, prior losses, refused by previous insurer" (homeowner)

    Returns:
        Markdown document containing:
          1. Generated persona JSON (for transparency and reuse)
          2. Full execution result report
    """
    # Step 1 — generate persona
    persona_json = generate_persona(lob, description)
    try:
        persona = json.loads(persona_json)
    except json.JSONDecodeError:
        return (
            f"**ERROR** — AI returned non-JSON output:\n\n"
            f"```\n{persona_json}\n```"
        )

    if persona.get("error"):
        return f"**ERROR** generating persona: {persona['error']}"

    # Attach description as persona_type for display
    persona["_persona_type"] = description[:60] + ("…" if len(description) > 60 else "")

    # Step 2 — execute
    result = _run_flow_threaded(lob, persona)
    report = format_result(result)

    return (
        f"## Generated Persona — {lob.upper()}\n\n"
        f"```json\n{json.dumps(persona, indent=2)}\n```\n\n"
        "---\n\n"
        f"{report}"
    )


@mcp.tool()
def run_batch_flows(scenarios: list) -> str:
    """
    Run multiple persona flows across LOBs and return a combined report.

    Each scenario is executed sequentially (a separate browser session per run).

    Args:
        scenarios: List of dicts, each with:
            {
              "lob": "auto" | "cyber" | "homeowner",
              "description": str   // natural-language persona
            }
            Example:
            [
              {"lob": "auto", "description": "Clean standard driver, Gold coverage"},
              {"lob": "cyber", "description": "Small office with good cyber hygiene"},
              {"lob": "homeowner", "description": "New construction 2022, low risk"}
            ]

    Returns:
        Markdown document with a summary table + individual result per scenario.
    """
    if not scenarios:
        return "**ERROR** — no scenarios provided."

    if len(scenarios) > MAX_BATCH_SIZE:
        return (
            f"**ERROR** — batch size {len(scenarios)} exceeds the limit of "
            f"{MAX_BATCH_SIZE} scenarios per call. Split into smaller batches."
        )

    all_results = []
    individual_reports = []

    for i, scenario in enumerate(scenarios, 1):
        lob = scenario.get("lob", "").lower().strip()
        description = scenario.get("description", "")

        if not lob or not description:
            individual_reports.append(
                f"### Scenario {i} — SKIPPED\n\nMissing `lob` or `description` field.\n"
            )
            continue

        persona_json = generate_persona(lob, description)
        try:
            persona = json.loads(persona_json)
        except json.JSONDecodeError:
            individual_reports.append(
                f"### Scenario {i} ({lob.upper()}) — ERROR\n\n"
                f"AI returned non-JSON: ```{persona_json}```\n"
            )
            continue

        if persona.get("error"):
            individual_reports.append(
                f"### Scenario {i} ({lob.upper()}) — ERROR\n\n{persona['error']}\n"
            )
            continue

        persona["_persona_type"] = description[:50] + ("…" if len(description) > 50 else "")
        result = _run_flow_threaded(lob, persona)
        all_results.append(result)
        individual_reports.append(format_result(result))

    summary = format_batch_summary(all_results)
    detail = "\n\n---\n\n".join(individual_reports)

    return f"{summary}\n\n---\n\n## Individual Results\n\n{detail}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
