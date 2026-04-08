"""
AI Enricher — converts raw captured page data into a full LOB scaffold.

Sends the captured field data to Claude and receives back a complete set of
Python / Gherkin / JSON files ready to drop into the framework.
"""

import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_CLIENT = anthropic.Anthropic()

# ---------------------------------------------------------------------------
# System prompt — teach Claude the framework conventions
# ---------------------------------------------------------------------------

_SYSTEM = """
You are a test automation engineer generating a full pytest-bdd scaffold for a
OneShield insurance platform using the Playwright + Python framework below.

FRAMEWORK CONVENTIONS
─────────────────────
1. Page objects inherit BasePage from `ui/pages/common/base_page.py`.
2. Locators use Playwright's ARIA-based getters:
     page.get_by_role("combobox", name="Field Label*")
     page.get_by_role("textbox",  name="Field Label*")
     page.get_by_role("button",   name="button text")
     page.get_by_role("checkbox", name="Field Label")
3. Dropdown (combobox) setter — always use _open_and_select:
     def set_field(self, data): self._open_and_select(self.field, data["FieldKey"])
4. Text input setter — use smart_fill:
     def set_field(self, data): self.smart_fill(self.field, data["FieldKey"])
5. Radio groups — use answer_question(group_label, answer):
     def set_field(self, data): self.answer_question("Group Label", data["FieldKey"])
6. Every page class has:
   - __init__(self, page) with all locators
   - fill_{lob}_details(self, data) that calls all setters in order
   - Individual setter methods
7. Feature file uses Gherkin. Steps are:
     Given I have test data for "<TC_ID>"
     Given I login to the application
     When i create a new quote
     When i create a new customer
     When I provide quote registration details
     When I fill {lob} quote details      ← LOB-specific
     ... (one step per page)
     Then the policy should be bound successfully
8. Step definitions use @given/@when/@then from pytest_bdd; parameterized steps
   need parsers.parse(). Import fixtures via function arguments.
9. Test entry point uses @scenario decorator.
10. Test data JSON must include ALL common fields (FirstName, LastName, DOB, etc.)
    plus LOB-specific fields. Use captured values as defaults.
11. EffDateOffset is always "1" (string).
12. Email format: "name_{timestamp}@{lob}.com"

COMMON FIELDS (always include in JSON, these exact keys):
  TC_ID, CustomerType, FirstName, LastName, DOB, PhoneNum, Email,
  Address, ZIP, State, City, Producer, EffDateOffset, Program, PaymentPlan

OUTPUT FORMAT
─────────────
Return a single JSON object with these keys, each value being the complete
file content as a string:

{
  "page_object":      "# full content of ui/pages/{lob}/{lob}_quote_page.py",
  "feature_file":     "# full content of ui/features/{lob}/{lob}_creation.feature",
  "step_definitions": "# full content of ui/steps/{lob}_steps.py",
  "test_entry":       "# full content of ui/tests/test_{lob}.py",
  "test_data":        "# full content of testdata/static/{Lob}Data.json"
}

Use real Python/Gherkin syntax. No placeholders, no "...". Generate complete,
working files that follow the conventions above exactly.
"""


def generate_scaffold(lob_name: str, program: str, captured_pages: list[dict]) -> dict[str, str]:
    """
    Send captured page data to Claude and get back a complete scaffold.

    Args:
        lob_name:       e.g. "workers_comp"
        program:        e.g. "Workers Compensation"
        captured_pages: list of page dicts from browser_session.capture_page()

    Returns:
        Dict with keys: page_object, feature_file, step_definitions, test_entry, test_data
    """
    lob_title = lob_name.replace("_", " ").title()
    lob_class = "".join(w.capitalize() for w in lob_name.split("_"))

    # Build a human-readable summary of captured pages
    pages_summary = []
    for pg in captured_pages:
        lines = [f"## Page: {pg['page_name']}"]
        lines.append("### Fields")
        for f in pg["fields"]:
            req = " (required)" if f.get("required") else ""
            role = f.get("playwright_role", "?")
            label = f.get("label", "?")
            value = f.get("value", "")
            opts = f.get("options")
            opt_str = f" | options: {opts}" if opts else ""
            val_str = f" | captured value: {value!r}" if value else ""
            lines.append(f"  - [{role}] {label}{req}{val_str}{opt_str}")
        if pg.get("buttons"):
            lines.append("### Buttons")
            for b in pg["buttons"]:
                lines.append(f"  - [button] {b}")
        if pg.get("interactions"):
            lines.append("### User Interactions (order filled)")
            for ix in pg["interactions"]:
                lines.append(f"  - {ix.get('label', '?')} → {ix.get('value', '?')!r}  [{ix.get('event')}]")
        pages_summary.append("\n".join(lines))

    user_prompt = f"""
Generate a complete pytest-bdd scaffold for the following new LOB:

LOB name:    {lob_name}
LOB title:   {lob_title}
Class prefix:{lob_class}
Program:     {program}

CAPTURED PAGES
==============
{chr(10).join(pages_summary)}

Generate all 5 files as described. Use the captured values as defaults in the
test data JSON. Include the full common fields section.
Return ONLY the JSON object — no markdown fences, no preamble.
"""

    response = _CLIENT.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0].strip()

    return json.loads(raw)
