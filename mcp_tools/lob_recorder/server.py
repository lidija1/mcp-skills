"""
MCP Server — LOB Recorder (AI-powered interactive inspector).

Workflow
────────
1. start_recording(lob_name, program)
     Opens a headed browser, logs in, runs common steps (NewQuote →
     Customer → QuoteRegistration) and lands on the LOB-specific form.
     JS event listeners are injected so every field interaction is captured.

2. [User interacts with the page normally — fill fields, pick dropdowns]

3. scan_page(page_name)
     Scans the current DOM for all ARIA-accessible form fields + reads
     the JS interaction log. Saves the snapshot and prints a summary.

4. click_button(label)  [optional]
     Clicks a navigation button (Next, Save, Rate Quote …) and re-injects
     listeners on the new page. Alternatively the user can click in the
     browser directly and just call scan_page again.

5. [Repeat 2-4 for every LOB-specific page]

6. generate_scaffold()
     Sends all captured pages to Claude, which produces a complete
     pytest-bdd scaffold:
       ui/pages/{lob}/{lob}_quote_page.py
       ui/features/{lob}/{lob}_creation.feature
       ui/steps/{lob}_steps.py
       ui/tests/test_{lob}.py
       testdata/static/{Lob}Data.json

7. stop_recording()
     Closes the browser.
"""

import asyncio
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP  # noqa: E402
import mcp_tools.lob_recorder.browser_session as _bs  # noqa: E402
from mcp_tools.lob_recorder.ai_enricher import generate_scaffold  # noqa: E402
from mcp_tools.lob_recorder.scaffold_writer import write_scaffold  # noqa: E402

mcp = FastMCP("lob-recorder")

# Single-threaded executor: all Playwright sync API calls must run in the
# same thread (not the asyncio event loop thread).
_EXECUTOR = ThreadPoolExecutor(max_workers=1)


async def _run(fn, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_EXECUTOR, fn, *args)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def start_recording(lob_name: str, program: str) -> str:
    """
    Open a headed browser, log in, run common steps, and land on the
    first LOB-specific form page ready for you to interact with.

    Args:
        lob_name: Snake-case LOB identifier, e.g. "workers_comp", "pet_insurance"
        program:  Exact program name as it appears in the dropdown,
                  e.g. "Workers Compensation", "Personal Auto"

    Returns:
        Status message with instructions.
    """
    try:
        return await _run(_bs.start_session, lob_name, program)
    except Exception:
        import traceback
        return f"ERROR starting session:\n{traceback.format_exc()}"


@mcp.tool()
async def scan_page(page_name: str) -> str:
    """
    Snapshot the current browser page: scans all visible ARIA form fields
    and reads the JS interaction log (values you entered/selected).

    Call this when you have finished interacting with a page and before
    clicking the next navigation button.

    Args:
        page_name: Human-readable page name, e.g. "Quote Details", "Driver Info"

    Returns:
        Summary of captured fields and interactions.
    """
    try:
        result = await _run(_bs.capture_page, page_name)
        lines = [
            f"Captured page: {result['page_name']}",
            f"  Fields found:          {result['fields_found']}",
            f"  Interactions recorded: {result['interactions_captured']}",
            "",
            "Fields:",
        ]
        for f in result["fields"]:
            role = f.get("playwright_role", "?")
            label = f.get("label", "?")
            value = f.get("value", "")
            req = "*" if f.get("required") else " "
            opts = f.get("options")
            val_str = f" → {value!r}" if value else ""
            opt_str = f"  [options: {', '.join(opts[:5])}{'…' if len(opts or []) > 5 else ''}]" if opts else ""
            lines.append(f"  [{req}] [{role:<10}] {label}{val_str}{opt_str}")

        if result.get("buttons"):
            lines.append("\nVisible buttons:")
            for b in result["buttons"]:
                lines.append(f"  [button] {b}")

        lines.append(
            f"\nPage '{page_name}' saved. "
            f"Total pages captured so far: {len(_bs.get_captured_pages())}"
        )
        return "\n".join(lines)
    except Exception:
        import traceback
        return f"ERROR scanning page:\n{traceback.format_exc()}"


@mcp.tool()
async def click_button(label: str) -> str:
    """
    Click a navigation button in the browser (e.g. 'Next', 'Save', 'Rate Quote')
    and re-inject event listeners on the new page so interactions keep being
    captured.

    You can also click buttons directly in the browser window — just call
    scan_page() again after navigating.

    Args:
        label: Button label text exactly as shown (case-insensitive match attempted).

    Returns:
        Confirmation message.
    """
    try:
        return await _run(_bs.click_button, label)
    except Exception:
        import traceback
        return f"ERROR clicking button:\n{traceback.format_exc()}"


@mcp.tool()
async def reinject_listeners() -> str:
    """
    Re-inject JS event listeners on the current page.

    Use this if you navigated in the browser yourself (without calling
    click_button) and want to resume capturing interactions.
    """
    try:
        await _run(_bs.inject_listeners)
        return "JS listeners re-injected on current page."
    except Exception:
        import traceback
        return f"ERROR:\n{traceback.format_exc()}"


@mcp.tool()
def get_session_summary() -> str:
    """
    Show a summary of all pages captured so far in this recording session.
    """
    pages = _bs.get_captured_pages()
    if not pages:
        return "No pages captured yet."
    lines = [f"LOB: {_bs.get_lob_name()} | Pages captured: {len(pages)}", ""]
    for i, pg in enumerate(pages, 1):
        lines.append(f"{i}. {pg['page_name']}  ({len(pg['fields'])} fields, {len(pg['interactions'])} interactions)")
    return "\n".join(lines)


@mcp.tool()
async def fill_field(label: str, value: str) -> str:
    """
    Fill a text input field on the current page by its aria-label.

    Use this in headless mode instead of typing manually in the browser.

    Args:
        label: The field's aria-label (visible label text, may end with *).
        value: The value to enter.
    """
    try:
        return await _run(_bs.fill_field, label, value)
    except Exception:
        import traceback
        return f"ERROR filling field:\n{traceback.format_exc()}"


@mcp.tool()
async def select_option(label: str, value: str) -> str:
    """
    Select a value from an ExtJS combobox / dropdown by its aria-label.

    Args:
        label: The combobox aria-label.
        value: The exact option text to select.
    """
    try:
        return await _run(_bs.select_option, label, value)
    except Exception:
        import traceback
        return f"ERROR selecting option:\n{traceback.format_exc()}"


@mcp.tool()
async def answer_radio(group_label: str, answer: str) -> str:
    """
    Click a radio button option within a named radio group.

    Args:
        group_label: The question / group label text (without trailing *).
        answer:      The option to select (aria-label or value text).
    """
    try:
        return await _run(_bs.answer_radio, group_label, answer)
    except Exception:
        import traceback
        return f"ERROR answering radio:\n{traceback.format_exc()}"


@mcp.tool()
async def take_screenshot(name: str = "page") -> str:
    """
    Take a screenshot of the current browser page and save it to
    reports/lob_recorder/<name>.png.

    Essential in headless mode — call this after filling out a page section
    to verify the state before scanning.

    Args:
        name: File name prefix (spaces replaced with underscores).

    Returns:
        Absolute path to the saved PNG.
    """
    try:
        return await _run(_bs.take_screenshot, name)
    except Exception:
        import traceback
        return f"ERROR taking screenshot:\n{traceback.format_exc()}"


@mcp.tool()
async def generate_scaffold_files(program: str = "") -> str:
    """
    Send all captured page data to Claude and generate a complete
    pytest-bdd scaffold for the new LOB.

    Writes these files to the project:
      ui/pages/{lob}/{lob}_quote_page.py
      ui/features/{lob}/{lob}_creation.feature
      ui/steps/{lob}_steps.py
      ui/tests/test_{lob}.py
      testdata/static/{Lob}Data.json

    Args:
        program: Program name override (defaults to the one used in start_recording).

    Returns:
        List of written files + next-steps instructions.
    """
    lob_name = _bs.get_lob_name()
    captured_pages = _bs.get_captured_pages()

    if not lob_name:
        return "No active recording session. Call start_recording() first."
    if not captured_pages:
        return "No pages captured yet. Use scan_page() on each form page first."

    try:
        files = await _run(generate_scaffold, lob_name, program or lob_name.replace("_", " ").title(), captured_pages)
        written = write_scaffold(lob_name, files)

        lob_class = "".join(w.capitalize() for w in lob_name.split("_"))
        lines = [
            f"Scaffold generated for LOB: {lob_name!r}",
            f"Files written ({len(written)}):",
        ]
        for path in written:
            lines.append(f"  {path}")

        lines += [
            "",
            "Next steps:",
            f"  1. Register step module in conftest.py:pytest_plugins:",
            f'       "ui.steps.{lob_name}_steps"',
            f"  2. Register page fixtures in ui/fixtures.py",
            f"  3. Run:  pytest ui/tests/test_{lob_name}.py -v --headed",
        ]
        return "\n".join(lines)

    except Exception:
        import traceback
        return f"ERROR generating scaffold:\n{traceback.format_exc()}"


@mcp.tool()
async def stop_recording() -> str:
    """
    Close the browser and end the recording session.
    """
    return await _run(_bs.stop_session)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
