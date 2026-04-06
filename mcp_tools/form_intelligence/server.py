"""
MCP Server — Form Intelligence & Validation Engine.

Exposes three tools:

  analyze_form       Navigate to a URL and return a structural description
                     of every form field found (no testing, no side-effects).

  probe_form         Full three-phase investigation:
                       1. Structural analysis
                       2. Empty-submission test
                       3. Per-field payload probing (malformed, boundary,
                          injection, boundary values, etc.)
                     Returns a Markdown report with findings and flagged issues.

  test_field         Targeted single-field deep-dive.  Useful when you already
                     know which field you want to stress-test.

─────────────────────────────────────────────────────────────────────────────
HOW TO REGISTER IN CLAUDE CODE  (~/.claude/settings.json or project settings)
─────────────────────────────────────────────────────────────────────────────

  "mcpServers": {
    "form-intelligence": {
      "command": "python",
      "args": ["-m", "mcp_tools.form_intelligence.server"],
      "cwd": "C:/Projects/SandboxPlaywright"
    }
  }

─────────────────────────────────────────────────────────────────────────────
USAGE EXAMPLES
─────────────────────────────────────────────────────────────────────────────

  # Discover what fields a form has (no testing)
  analyze_form("https://example.com/contact")

  # Full probe with default settings (headless, no submit button known)
  probe_form("https://example.com/register")

  # Probe a login form — pre-fill username so we can isolate the password field
  probe_form(
      url="https://example.com/login",
      valid_defaults={"#username": "valid@example.com"},
      submit_selector="#login-btn",
  )

  # Deep-dive on a single email field
  test_field(
      url="https://example.com/register",
      field_selector="#email",
      field_type="email",
  )

─────────────────────────────────────────────────────────────────────────────
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

# Ensure project root on sys.path when started via python -m
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from mcp_tools.url_guard import assert_probe_allowed, validate_url  # noqa: E402
from mcp_tools.form_intelligence.engine import FormIntelligenceEngine  # noqa: E402
from mcp_tools.form_intelligence.reporter import (  # noqa: E402
    format_analysis,
    format_field_probe,
    format_probe,
)

mcp = FastMCP(
    "form-intelligence",
    instructions=(
        "Analyse and probe HTML forms for validation gaps, missing required-field "
        "checks, boundary failures, and injection opportunities.  "
        "Call analyze_form to see what fields exist, probe_form for a full "
        "investigation, or test_field for a targeted single-field deep-dive."
    ),
)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def analyze_form(url: str) -> str:
    """
    Navigate to the given URL and return a structural description of every
    visible form field (input, select, textarea) found on the page.

    No data is submitted — this tool is purely observational.

    Args:
        url: Full URL of the page containing the form, e.g.
             "https://example.com/register"

    Returns:
        Markdown table listing each field with its type, selector, required
        flag, and any HTML constraints (min, max, maxlength, pattern).
    """
    try:
        validate_url(url)
        fields = FormIntelligenceEngine(headless=True).analyze(url)
        return format_analysis(fields)
    except ValueError as exc:
        return f"**BLOCKED** — {exc}"
    except Exception as exc:
        return f"**ERROR** — analyze_form failed: {exc}"


@mcp.tool()
async def probe_form(
    url: str,
    valid_defaults: Optional[str] = None,
    submit_selector: Optional[str] = None,
    field_selectors: Optional[str] = None,
    headless: bool = True,
) -> str:
    """
    Run a full three-phase validation investigation against a web form.

    Phase 1 — Structural analysis: discover all form fields and their HTML
               constraints (type, required, min, max, pattern, maxlength).

    Phase 2 — Empty submission: clear every field and attempt to submit (or
               trigger blur) to reveal which fields are required and what
               their error messages look like.

    Phase 3 — Per-field probing: for every field, reload the page, inject a
               battery of test values (empty, malformed inputs, boundary
               values, injection strings) and capture any validation messages
               that appear.

    Findings are categorised as:
      MISSING VALIDATION  — an invalid value was accepted without an error
      OVER-VALIDATION     — a legitimately valid value was rejected

    Args:
        url:              Full URL of the page, e.g. "https://example.com/register"

        valid_defaults:   JSON object of {selector: value} pairs used to
                          pre-fill all fields EXCEPT the one being tested.
                          This keeps the rest of the form valid so validation
                          messages are unambiguous.
                          Example: '{"#firstName": "Alice", "#lastName": "Smith"}'

        submit_selector:  CSS selector for the form's submit button.
                          When provided, the engine also clicks it after each
                          payload to trigger JS/server-side validation.
                          Example: 'button[type="submit"]'

        field_selectors:  JSON array of CSS selectors — probe only these fields
                          instead of every field on the page.
                          Example: '["#email", "#phone"]'

        headless:         Run the browser in headless mode (default: true).
                          Set to false to watch the browser while it probes.

    Returns:
        Markdown report with:
          - Issue summary (missing/over-validation findings)
          - Empty-submission results
          - Per-field results table (every payload, pass/fail, error messages)
    """
    try:
        assert_probe_allowed(url)
        defaults = json.loads(valid_defaults) if valid_defaults else None
        selectors = json.loads(field_selectors) if field_selectors else None

        def _run():
            engine = FormIntelligenceEngine(headless=headless)
            return engine.probe(
                url=url,
                valid_defaults=defaults,
                submit_selector=submit_selector,
                field_selectors=selectors,
            )

        report = await asyncio.to_thread(_run)
        return format_probe(report)

    except ValueError as exc:
        return f"**BLOCKED** — {exc}"
    except Exception as exc:
        return f"**ERROR** — probe_form failed: {exc}"


@mcp.tool()
def test_field(
    url: str,
    field_selector: str,
    field_type: str,
    valid_defaults: Optional[str] = None,
    headless: bool = True,
) -> str:
    """
    Run the full payload battery against a single, specific form field.

    This is the fastest way to deep-dive on one field without waiting for
    the entire form to be probed.

    Args:
        url:             Full URL of the page containing the field.

        field_selector:  CSS selector uniquely identifying the target field,
                         e.g. "#email", "input[name='phone']".

        field_type:      HTML input type to select the appropriate payload set.
                         Supported values: text, email, tel, date, number,
                         password, url, select, checkbox, radio, textarea.

        valid_defaults:  JSON object of {selector: value} pairs to pre-fill
                         other fields so the form can be partially submitted.
                         Example: '{"#firstName": "Alice"}'

        headless:        Run the browser in headless mode (default: true).

    Returns:
        Markdown report showing every payload tested, whether it passed
        client-side validation, and any error messages captured.
    """
    try:
        assert_probe_allowed(url)
        defaults = json.loads(valid_defaults) if valid_defaults else None

        def _run():
            engine = FormIntelligenceEngine(headless=headless)
            return engine.probe_single_field(
                url=url,
                field_selector=field_selector,
                field_type=field_type,
                valid_defaults=defaults,
            )

        result = _run()
        return format_field_probe(result)

    except ValueError as exc:
        return f"**BLOCKED** — {exc}"
    except Exception as exc:
        return f"**ERROR** — test_field failed: {exc}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
