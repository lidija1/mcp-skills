"""
MCP Server — Local Inference.

Exposes local Ollama model inference as MCP tools so any other tool, the
dashboard, or Claude Code can call the local model without coupling to a
cloud provider.

Exposes three tools:

  ask_model              General-purpose Q&A with optional context
  analyze_test_failure   Explain a pytest/Playwright failure and suggest a fix
  suggest_scenarios      Brainstorm test scenarios or UW edge cases for a topic

Configuration (.env or MCP server env block):
  OLLAMA_MODEL      Model to use (default: qwen3:8b)
  OLLAMA_BASE_URL   Ollama API base URL (default: http://localhost:11434/v1)
"""

import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env")

from mcp.server.fastmcp import FastMCP  # noqa: E402

# ---------------------------------------------------------------------------
# Ollama client config
# ---------------------------------------------------------------------------

_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

_FRAMEWORK_CONTEXT = """\
You are an expert assistant for an insurance policy automation test framework.
The framework uses Python, pytest-bdd, Playwright, and ExtJS against the
OneShield insurance platform. Lines of business: Personal Auto, Homeowner,
Tests are BDD scenarios in Gherkin. Page objects inherit BasePage.
UW rules trigger referrals for SR-22, suspended/revoked licence, driver
under 25, prior losses, and prior refusal/non-renewal.
"""


def _call_ollama(system: str, user: str, max_tokens: int = 2048) -> str:
    """Send a chat request to the local Ollama model and return the response text."""
    import openai as _openai
    client = _openai.OpenAI(base_url=_BASE_URL, api_key="ollama")
    response = client.chat.completions.create(
        model=_MODEL,
        max_tokens=max_tokens,
        extra_body={"think": False},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "local-inference",
    instructions=(
        "Local Ollama model inference. No browser or cloud API required. "
        "Use ask_model for general Q&A with optional context. "
        "Use analyze_test_failure to explain a pytest/Playwright error and get a fix suggestion. "
        "Use suggest_scenarios to brainstorm new test scenarios or UW edge cases."
    ),
)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def ask_model(question: str, context: str = "") -> str:
    """
    Ask the local model any question, optionally with supporting context.

    The model is pre-primed with OneShield framework knowledge so you can
    ask framework-specific questions without re-explaining the stack each time.

    Args:
        question: The question or instruction for the model.
        context:  Optional supporting text — paste code, a log excerpt, a
                  JSON blob, a feature file, etc. The model will read it
                  before answering. Leave blank for open-ended questions.

    Returns:
        Model response as plain text.

    Examples:
        ask_model("What BasePage method should I use to select a combobox value?")
        ask_model("What does this step definition do?", context="<paste code>")
        ask_model("Summarise this API payload", context="<paste JSON>")
    """
    system = _FRAMEWORK_CONTEXT + "\nAnswer clearly and concisely."
    user = f"{question}\n\n---\n{context}" if context.strip() else question
    return _call_ollama(system, user)


@mcp.tool()
def analyze_test_failure(error_output: str, test_file: str = "") -> str:
    """
    Explain a pytest or Playwright test failure and suggest how to fix it.

    Paste the raw pytest output, a stack trace, or a Playwright error message.
    The model identifies the root cause, explains it in plain English, and
    proposes a concrete fix within this framework's conventions.

    Args:
        error_output: Raw error text — pytest output, stack trace, or
                      Playwright TimeoutError / assertion message.
        test_file:    Optional — paste the relevant test/step/page-object
                      source so the model can reference specific lines.

    Returns:
        Markdown report with: Root Cause, Explanation, Suggested Fix,
        and Framework Notes (relevant BasePage methods / ExtJS patterns).

    Examples:
        analyze_test_failure("<paste pytest -s output>")
        analyze_test_failure("<stack trace>", test_file="<paste page object>")
    """
    system = (
        _FRAMEWORK_CONTEXT
        + "\n\nYou are a senior QA engineer debugging a failing automated test. "
        "Given the error output and optional source code, produce a Markdown report "
        "with these four sections:\n"
        "## Root Cause\n"
        "## Explanation\n"
        "## Suggested Fix  (show exact code changes where possible)\n"
        "## Framework Notes  (relevant BasePage methods, ExtJS patterns, or pytest-bdd gotchas)\n"
        "Be specific and actionable. Do not pad with generic advice."
    )
    user = f"## Error Output\n\n```\n{error_output}\n```"
    if test_file.strip():
        user += f"\n\n## Source File\n\n```python\n{test_file}\n```"
    return _call_ollama(system, user, max_tokens=3072)


@mcp.tool()
def suggest_scenarios(description: str, lob: str = "", existing: str = "") -> str:
    """
    Brainstorm new test scenarios or UW edge cases for a given topic.

    Use this to expand coverage: describe what you want to test, optionally
    name the line of business, and optionally paste your existing scenarios
    so the model avoids duplicating them.

    Args:
        description: What you want to cover — a rule, a page, a risk factor,
                     a workflow step, or an open-ended area like
                     "leased vehicle with loss payee" or
                     "homeowner with prior losses and renovation".
        lob:         Optional LOB filter — "auto" or "homeowner".
                     Omit for framework-wide suggestions.
        existing:    Optional — paste your current Gherkin scenarios or test
                     case IDs so the model skips them.

    Returns:
        Bulleted list of scenario ideas, each with: title, risk profile
        summary, expected outcome (policy_bound / uw_referral), and which
        UW rule(s) it exercises.

    Examples:
        suggest_scenarios("SR-22 edge cases", lob="auto")
        suggest_scenarios("homeowner high-risk profiles", lob="homeowner", existing="<paste feature file>")
        suggest_scenarios("homeowner boundary conditions for prior refusal rule")
    """
    lob_hint = f" for the {lob.upper()} line of business" if lob.strip() else ""
    system = (
        _FRAMEWORK_CONTEXT
        + f"\n\nYou are a QA architect designing test scenarios{lob_hint}. "
        "Given the topic and any existing coverage, suggest NEW scenarios that "
        "meaningfully extend coverage. For each scenario provide:\n"
        "- **Title**: short scenario name\n"
        "- **Profile**: key persona attributes that make this interesting\n"
        "- **Expected outcome**: `policy_bound` or `uw_referral`\n"
        "- **Rule(s) exercised**: which UW rule(s) or page behaviour this targets\n\n"
        "Prefer boundary conditions, multi-trigger combinations, and cases that "
        "are easy to miss. Do not repeat any scenario in the existing list."
    )
    user = f"Topic: {description}"
    if existing.strip():
        user += f"\n\nExisting coverage to avoid duplicating:\n{existing}"
    return _call_ollama(system, user, max_tokens=3072)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
