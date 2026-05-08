"""
MCP Server — Policy Flow Generator (multi-LOB).

Exposes seven tools:

  list_persona_archetypes   List available persona archetypes per LOB
  create_persona            NL description → structured persona JSON (Auto/Cyber/Homeowner)
  create_persona_variations Generate N distinct variations from a single base description
  create_batch_personas     Generate multiple persona JSONs in one call (no browser execution)
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
    generate_batch_personas,
    generate_persona_variations,
    list_archetypes,
)
from mcp_tools.policy_flow_generator.flow_runner import run_flow  # noqa: E402
from mcp_tools.policy_flow_generator.result_formatter import (  # noqa: E402
    format_result,
    format_batch_summary,
)
from mcp_tools.policy_flow_generator.business_reports import (  # noqa: E402
    format_scenario_comparison,
    summarize_policy_from_reports,
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
        "Use create_batch_personas to generate multiple persona JSONs without running flows. "
        "Use run_batch_flows to test multiple scenarios at once. "
        "Use compare_scenarios for BA/customer-friendly scenario comparison, "
        "and summarize_policy to summarize a saved bound policy."
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
def create_batch_personas(scenarios: list) -> str:
    """
    Generate multiple insurance persona JSONs in a single call — no browser execution.

    Use this when you need to inspect or store many personas before deciding which
    flows to run, or when you want to pre-generate a corpus of test data without
    waiting for browser sessions to complete.

    Args:
        scenarios: List of dicts, each with:
            {
              "lob": "auto" | "cyber" | "homeowner",
              "description": str   // natural-language persona
            }
            Example:
            [
              {"lob": "auto", "description": "Young driver aged 19 with one at-fault accident"},
              {"lob": "cyber", "description": "Healthcare SaaS, 50 employees, HIPAA compliant"},
              {"lob": "homeowner", "description": "Coastal property, tile roof, $800k value"}
            ]
            Up to 25 scenarios per call.

    Returns:
        JSON array where each element is the generated persona object for that
        scenario (or an error object if generation failed), plus an added
        "_scenario_index" field for correlation.
    """
    if not scenarios:
        return json.dumps({"error": "No scenarios provided."})

    if len(scenarios) > MAX_BATCH_SIZE:
        return json.dumps({
            "error": (
                f"Batch size {len(scenarios)} exceeds the limit of "
                f"{MAX_BATCH_SIZE}. Split into smaller batches."
            )
        })

    return generate_batch_personas(scenarios)


@mcp.tool()
def create_persona_variations(lob: str, base_description: str, count: int = 5) -> str:
    """
    Generate N distinct persona variations from a single base description — no browser execution.

    Use this when you want multiple different test personas that all share a common
    risk theme (e.g., "20 variations of a high-risk auto driver" or "10 coastal
    homeowner profiles"). Each variation differs in name, age, coverage level,
    specific risk factors, and other details, while staying true to the base theme.

    Args:
        lob: Line of business — "auto", "cyber", or "homeowner"
        base_description: Natural-language base persona, e.g.
            "22-year-old driver with SR-22, revoked license, leased BMW, Platinum coverage"
        count: Number of distinct variations to generate (1–25, default 5)

    Returns:
        JSON array of `count` persona objects, each with a `_variation_index` field.
    """
    if not lob or not base_description:
        return json.dumps({"error": "lob and base_description are required."})

    if not 1 <= count <= MAX_BATCH_SIZE:
        return json.dumps({
            "error": f"count must be between 1 and {MAX_BATCH_SIZE} (got {count})."
        })

    return generate_persona_variations(lob, base_description, count)


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

    # Accept an array (e.g. pasted from create_persona_variations output) — use first element
    if isinstance(persona, list):
        if not persona:
            return "**ERROR** — empty persona array."
        persona = persona[0]

    if not isinstance(persona, dict):
        return "**ERROR** — persona_json must be a JSON object (or array of objects)."

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


@mcp.tool()
def compare_scenarios(scenarios: list, default_lob: str = "auto") -> str:
    """
    Compare multiple plain-English insurance scenarios in a business-friendly table.

    This is intended for BAs, product owners, and customer demos. Codex can
    translate a request such as "compare clean driver vs SR-22 driver" into
    scenario descriptions and call this tool.

    Each scenario launches a live browser flow, so keep the list small for
    interactive use.

    Args:
        scenarios: List of strings or dicts. Accepted forms:
            [
              "Clean standard driver with Gold coverage",
              "Same driver with SR-22 and leased BMW"
            ]
            or
            [
              {"lob": "auto", "description": "Clean standard driver"},
              {"lob": "homeowner", "description": "High-value home with prior losses"}
            ]
        default_lob: LOB used when a scenario item is just a string.
            Valid values: "auto", "cyber", "homeowner".

    Returns:
        Markdown comparison table with outcome, policy number, premium, UW/error
        notes, duration, and bound policy detail sections when available.
    """
    if not scenarios:
        return "**ERROR** - no scenarios provided."
    if len(scenarios) > MAX_BATCH_SIZE:
        return (
            f"**ERROR** - scenario count {len(scenarios)} exceeds the limit of "
            f"{MAX_BATCH_SIZE}. Split into smaller comparison batches."
        )

    results = []
    detail_reports = []

    for item in scenarios:
        if isinstance(item, str):
            lob = default_lob.lower().strip()
            description = item
        else:
            lob = str(item.get("lob") or default_lob).lower().strip()
            description = str(item.get("description") or "").strip()

        if not description:
            results.append({
                "lob": lob,
                "persona_type": "(missing description)",
                "outcome": "error",
                "error": "Missing scenario description.",
                "total_duration_s": 0,
            })
            continue

        persona_json = generate_persona(lob, description)
        try:
            persona = json.loads(persona_json)
        except json.JSONDecodeError:
            results.append({
                "lob": lob,
                "persona_type": description,
                "outcome": "error",
                "error": f"AI returned non-JSON persona: {persona_json}",
                "total_duration_s": 0,
            })
            continue

        if persona.get("error"):
            results.append({
                "lob": lob,
                "persona_type": description,
                "outcome": "error",
                "error": persona["error"],
                "total_duration_s": 0,
            })
            continue

        persona["_persona_type"] = description[:70] + ("..." if len(description) > 70 else "")
        result = _run_flow_threaded(lob, persona)
        result["description"] = description
        results.append(result)
        detail_reports.append(format_result(result))

    comparison = format_scenario_comparison(results)
    if detail_reports:
        comparison += "\n\n---\n\n## Execution Detail\n\n"
        comparison += "\n\n---\n\n".join(detail_reports)
    return comparison


@mcp.tool()
def summarize_policy(
    policy_number: str = "",
    lob: str = "",
    customer_name: str = "",
    query: str = "",
    latest: bool = True,
) -> str:
    """
    Summarize a policy that has already been created by the automation.

    Reads the local policy summary CSV files written by live policy runs.
    Codex can call this from plain English, for example:
      - "summarize the latest auto policy"
      - "summarize PA10068256657-00"
      - "show policy for James Smith"

    Args:
        policy_number: Exact policy number when known.
        lob: Optional LOB filter: "auto", "cyber", "homeowner", or
            "general liability".
        customer_name: Optional customer/insured name filter.
        query: Optional plain-English query; policy number and simple customer
            names are extracted when possible.
        latest: When multiple rows match, return the latest saved row.

    Returns:
        Markdown policy summary table.
    """
    return summarize_policy_from_reports(
        lob=lob,
        policy_number=policy_number,
        customer_name=customer_name,
        query=query,
        latest=latest,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
