"""
MCP Server — Accessibility Audit.

Exposes five tools that drive a headless Playwright browser and inspect a live
page through its accessibility tree plus direct DOM queries:

  audit_accessibility   Full audit (all six check categories) — returns a
                        Markdown report with a severity-bucketed issue list,
                        heading outline, and accessibility-tree dump.

  check_images          Targeted check: missing or empty alt text on <img>
                        elements.

  check_forms           Targeted check: <input> / <select> / <textarea>
                        controls that lack an accessible label.

  check_headings        Targeted check: heading hierarchy — skipped levels,
                        missing h1, multiple h1s.

  check_keyboard        Targeted check: keyboard-navigation pitfalls —
                        non-interactive elements with onclick, disruptive
                        positive tabindex values, empty links and buttons,
                        and focusable elements inside aria-hidden containers.

─────────────────────────────────────────────────────────────────────────────
REGISTRATION  (VS Code / Claude Code  — .vscode/mcp.json or settings.json)
─────────────────────────────────────────────────────────────────────────────

  "mcpServers": {
    "accessibility": {
      "command": "python",
      "args": ["-m", "mcp_tools.accessibility.server"],
      "cwd": "C:/Projects/SandboxPlaywright"
    }
  }

─────────────────────────────────────────────────────────────────────────────
USAGE EXAMPLES
─────────────────────────────────────────────────────────────────────────────

  # Full audit of a page
  audit_accessibility("https://example.com")

  # Run only the image alt-text check
  check_images("https://example.com/gallery")

  # Check form labels on a registration page
  check_forms("https://example.com/register")

  # Inspect heading structure
  check_headings("https://example.com/docs")

  # Keyboard-navigation audit
  check_keyboard("https://example.com/dashboard")

─────────────────────────────────────────────────────────────────────────────
"""

import asyncio
import sys
from pathlib import Path

# Ensure project root on sys.path when started via python -m
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from mcp_tools.url_guard import validate_url  # noqa: E402
from mcp_tools.accessibility.engine import AccessibilityEngine  # noqa: E402
from mcp_tools.accessibility.reporter import (  # noqa: E402
    format_category_report,
    format_full_report,
    format_heading_tree,
)

mcp = FastMCP(
    "accessibility",
    instructions=(
        "Run WCAG-aligned accessibility checks against a live webpage. "
        "Available checks: alt text, form labels, heading order, keyboard navigation, "
        "ARIA hygiene, and page metadata (title / lang). "
        "Results are returned as structured Markdown reports with severity badges "
        "(critical / warning / info), affected element snippets, and remediation hints."
    ),
)


# ---------------------------------------------------------------------------
# Tool: full audit
# ---------------------------------------------------------------------------

@mcp.tool()
async def audit_accessibility(url: str, headed: bool = False) -> str:
    """
    Run a full accessibility audit on *url* covering all six check categories:
    page metadata, image alt text, form labels, heading order, keyboard
    navigation, and ARIA hygiene.

    Returns a Markdown report that includes:
    - A severity summary table (critical / warning / info counts)
    - Issues grouped by category with remediation suggestions and element snippets
    - The complete heading outline
    - A collapsed accessibility-tree dump (Playwright snapshot)

    Args:
        url:    The fully-qualified URL to audit (must be reachable by the server).
        headed: Set to True to run with a visible browser window (useful for debugging).
    """
    try:
        validate_url(url)
    except ValueError as exc:
        return f"**BLOCKED** — {exc}"
    engine = AccessibilityEngine(headed=headed)
    report = await asyncio.to_thread(engine.audit, url)
    return format_full_report(report)


# ---------------------------------------------------------------------------
# Tool: image alt text
# ---------------------------------------------------------------------------

@mcp.tool()
def check_images(url: str, headed: bool = False) -> str:
    """
    Check every <img> element on the page for a missing or empty alt attribute.

    Images without alt text are flagged as **critical** (completely inaccessible
    to screen-reader users).  Images with alt="" but without role="presentation"
    or aria-hidden="true" are flagged as **warning** because they may be
    informative.

    Args:
        url:    The fully-qualified URL to inspect.
        headed: Set to True to open a visible browser window.
    """
    try:
        validate_url(url)
    except ValueError as exc:
        return f"**BLOCKED** — {exc}"
    report = AccessibilityEngine(headed=headed).audit(url, checks=["alt_text"])
    return format_category_report("alt_text", report.issues, url)


# ---------------------------------------------------------------------------
# Tool: form labels
# ---------------------------------------------------------------------------

@mcp.tool()
def check_forms(url: str, headed: bool = False) -> str:
    """
    Inspect every visible form control (<input>, <select>, <textarea>) for an
    accessible label.

    A control is considered labelled if it has any of:
      - A <label for="id"> association
      - A wrapping <label> element
      - aria-label attribute
      - aria-labelledby pointing to an existing element
      - title attribute (fallback; discouraged but acceptable)

    Controls relying solely on placeholder text are flagged as **warning** since
    placeholders disappear during input and are not reliably announced.
    Unlabelled controls with no placeholder at all are **critical**.

    Args:
        url:    The fully-qualified URL to inspect.
        headed: Set to True to open a visible browser window.
    """
    try:
        validate_url(url)
    except ValueError as exc:
        return f"**BLOCKED** — {exc}"
    report = AccessibilityEngine(headed=headed).audit(url, checks=["form_labels"])
    return format_category_report("form_labels", report.issues, url)


# ---------------------------------------------------------------------------
# Tool: heading order
# ---------------------------------------------------------------------------

@mcp.tool()
def check_headings(url: str, headed: bool = False) -> str:
    """
    Analyse the heading hierarchy (<h1>–<h6>) on the page.

    Checks performed:
      - Missing <h1> (critical — every page needs one main heading)
      - Multiple <h1> elements (warning — typically only one is correct)
      - Skipped heading levels, e.g. <h2> → <h4> (warning — breaks screen-reader
        navigation and document outline)
      - No headings at all (warning — page lacks navigable structure)

    Returns a report that includes the full heading tree so the visual outline
    can be reviewed at a glance.

    Args:
        url:    The fully-qualified URL to inspect.
        headed: Set to True to open a visible browser window.
    """
    try:
        validate_url(url)
    except ValueError as exc:
        return f"**BLOCKED** — {exc}"
    report = AccessibilityEngine(headed=headed).audit(url, checks=["heading_order"])
    issues_md = format_category_report("heading_order", report.issues, url)
    tree_md   = format_heading_tree(report.headings, url)
    return issues_md + "\n---\n\n" + tree_md


# ---------------------------------------------------------------------------
# Tool: keyboard navigation
# ---------------------------------------------------------------------------

@mcp.tool()
def check_keyboard(url: str, headed: bool = False) -> str:
    """
    Audit the page for keyboard-navigation accessibility problems.

    Checks performed:
      - Non-interactive elements (<div>, <span>, etc.) with onclick handlers but
        no tabindex or keyboard event handler — keyboard-only users cannot reach
        these (critical)
      - Elements with tabindex > 0 — disrupts the natural document tab order
        (warning)
      - Focusable elements (<a>, <button>, <input>) inside an aria-hidden="true"
        container — keyboard focus can land on elements invisible to AT (critical)
      - <a> links with no accessible name — screen readers announce "link" with
        no context (critical)
      - <button> elements with no accessible name (critical)

    Args:
        url:    The fully-qualified URL to inspect.
        headed: Set to True to open a visible browser window.
    """
    try:
        validate_url(url)
    except ValueError as exc:
        return f"**BLOCKED** — {exc}"
    report = AccessibilityEngine(headed=headed).audit(url, checks=["keyboard"])
    return format_category_report("keyboard", report.issues, url)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
