#!/usr/bin/env python3
"""
tools/lob_scaffold.py
=====================
LOB Scaffold Generator.

Navigates the OneShield app via Playwright to discover each workflow step and
its form fields, then calls Claude API to generate all six framework files:

  testdata/static/<Lob>Data.json
  ui/pages/<lob>/__init__.py
  ui/pages/<lob>/<lob>_quote_page.py   (one file, one class per step)
  ui/features/<lob>/<lob>_creation.feature
  ui/steps/<lob>_steps.py
  ui/tests/test_<lob>.py

Usage:
    python tools/lob_scaffold.py --lob "Term Life"   --program "Term Life"
    python tools/lob_scaffold.py --lob "Dental"      --program "Dental Insurance" --headed
    python tools/lob_scaffold.py --lob "Term Life"   --program "Term Life" --dry-run
    python tools/lob_scaffold.py --lob "Term Life"   --program "Term Life" --skip-nav
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import anthropic
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout

# -- load .env from project root ----------------------------------------------
_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")

# -- app constants -------------------------------------------------------------
_SPLASH_URL = "https://inforcedev.oneshield.com/splash.html"
_AGENCY    = "Sherrie Insurance Co"

# Fields that MUST stay consistent across ALL LOBs (used in shared CustomerPage)
FIXED_FIELDS = {
    "ZIP":       "01101",
    "City":      "Springfield",
    "State":     "Massachusetts",
    "Producer":  "Janis Irey",
    "EffDateOffset": "1",
    "PaymentPlan": "Pay In Full",
}

# Steps already implemented in ui/pages/common/ — skip code generation for these
COMMON_STEP_KEYWORDS = {
    "Delivery Preferences",
    "Billing Plan",
    "Verify Billing",
    "Billing Verification",
}


# -----------------------------------------------------------------------------
# Data structures
# -----------------------------------------------------------------------------

@dataclass
class FieldDef:
    label:      str
    field_type: str          # combobox | text | radio | checkbox | date | textarea
    required:   bool  = False
    options:    list[str] = field(default_factory=list)
    hint:       str   = ""   # placeholder / tooltip


@dataclass
class StepDef:
    name:      str
    fields:    list[FieldDef] = field(default_factory=list)
    is_common: bool = False   # True = already in ui/pages/common/


# -----------------------------------------------------------------------------
# JS used to extract ExtJS form fields from any page
# -----------------------------------------------------------------------------

_EXTRACT_FIELDS_JS = r"""
() => {
    const results = [];
    const seen = new Set();

    function labelOf(el) {
        // 1. aria-label on the input itself
        const al = el.getAttribute('aria-label');
        if (al) return al.replace(/\*$/, '').trim();

        // 2. ExtJS wrapping .x-field > .x-form-item-label-text
        const wrap = el.closest('.x-field, .x-form-item');
        if (wrap) {
            const lbl = wrap.querySelector('.x-form-item-label-text');
            if (lbl) return lbl.textContent.trim().replace(/\*$/, '').trim();
        }

        // 3. aria-labelledby
        const lblId = el.getAttribute('aria-labelledby');
        if (lblId) {
            const node = document.getElementById(lblId);
            if (node) return node.textContent.trim().replace(/\*$/, '').trim();
        }

        return el.placeholder || el.name || '';
    }

    function isHidden(el) {
        if (el.offsetParent === null) return true;
        const r = el.getBoundingClientRect();
        return r.width === 0 && r.height === 0;
    }

    function requiredCheck(el) {
        return el.getAttribute('aria-required') === 'true'
            || !!el.closest('.x-field-required')
            || el.required;
    }

    // -- ExtJS comboboxes (input[aria-owns]) ------------------------------
    document.querySelectorAll('input[aria-owns]').forEach(el => {
        if (isHidden(el)) return;
        const label = labelOf(el);
        if (!label || seen.has(label)) return;
        seen.add(label);

        // Collect options from the bound list (may be empty if not yet opened)
        const pickerId = (el.getAttribute('aria-owns') || '')
            .split(' ').find(id => id.includes('picker'));
        const options = [];
        if (pickerId) {
            (document.getElementById(pickerId) || { querySelectorAll: () => [] })
                .querySelectorAll('.x-boundlist-item')
                .forEach(opt => options.push(opt.textContent.trim()));
        }

        results.push({ label, field_type: 'combobox', required: requiredCheck(el), options, hint: el.placeholder || '' });
    });

    // -- Plain text inputs -------------------------------------------------
    document.querySelectorAll('input.x-form-text:not([aria-owns])').forEach(el => {
        if (isHidden(el)) return;
        const label = labelOf(el);
        if (!label || seen.has(label)) return;
        seen.add(label);
        results.push({ label, field_type: 'text', required: requiredCheck(el), options: [], hint: el.placeholder || '' });
    });

    // -- Textarea ----------------------------------------------------------
    document.querySelectorAll('textarea').forEach(el => {
        if (isHidden(el)) return;
        const label = labelOf(el);
        if (!label || seen.has(label)) return;
        seen.add(label);
        results.push({ label, field_type: 'textarea', required: requiredCheck(el), options: [], hint: el.placeholder || '' });
    });

    // -- Radio groups ------------------------------------------------------
    document.querySelectorAll('[role="radiogroup"]').forEach(group => {
        if (isHidden(group)) return;

        let label = group.getAttribute('aria-label') || '';
        if (!label) {
            const wrap = group.closest('.x-field, .x-form-item');
            if (wrap) {
                const lbl = wrap.querySelector('.x-form-item-label-text');
                if (lbl) label = lbl.textContent.trim().replace(/\*$/, '').trim();
            }
        }
        if (!label || seen.has(label)) return;
        seen.add(label);

        const options = [...group.querySelectorAll('input[type="radio"]')].map(r => {
            const lbl = r.id ? document.querySelector(`label[for="${r.id}"]`) : null;
            return lbl ? lbl.textContent.trim() : r.value;
        }).filter(Boolean);

        results.push({ label, field_type: 'radio', required: requiredCheck(group), options, hint: '' });
    });

    return results;
}
"""


# -----------------------------------------------------------------------------
# App Navigator — OneShield-specific Playwright logic
# -----------------------------------------------------------------------------

class AppNavigator:
    """Drives the OneShield app through the new-quote workflow for a given LOB."""

    def __init__(self, page: Page):
        self.page = page

    # -- public API ------------------------------------------------------------

    def login(self) -> None:
        partner  = os.getenv("PARTNER_NUM", "0")
        username = os.getenv("USERNAMEE", "")
        password = os.getenv("PASSWORD", "")

        # Mirror the exact flow from the MCP session:
        # splash page -> click LOGIN link -> fill credentials -> submit
        self.page.goto(_SPLASH_URL)
        self.page.wait_for_selector("a[href*='EmployeePortal']", timeout=15_000)
        self.page.locator("a[href*='EmployeePortal']").first.click()

        # Wait for login form
        self.page.wait_for_selector("text=PARTNER NUMBER", timeout=20_000)
        self.page.get_by_role("textbox", name="PARTNER NUMBER*").fill(partner)
        self.page.get_by_role("textbox", name="USERNAME*").fill(username)
        self.page.get_by_role("textbox", name="PASSWORD*").fill(password)
        self.page.wait_for_timeout(500)
        self.page.get_by_role("button", name="login").click()
        # Wait for redirect; save debug screenshot if it times out
        # "new quote" button text lives in a nested <generic> — use role locator
        try:
            self.page.get_by_role("button", name="new quote").wait_for(
                state="visible", timeout=30_000
            )
        except Exception:
            self.page.screenshot(path=str(_ROOT / "tools" / "debug_login.png"), full_page=True)
            raise
        print("  [OK] Logged in")

    def start_new_quote(self) -> None:
        self.page.get_by_role("button", name="new quote").click()
        self.page.wait_for_selector(f"text={_AGENCY}", timeout=15_000)
        # Click the row-selector cell (first empty td/gridcell) to select the row.
        # Do NOT click the agency name — it is a hyperlink that navigates away.
        agency_row = self.page.get_by_role("row", name=re.compile(_AGENCY))
        agency_row.get_by_role("gridcell").first.click()
        # Wait for any loading mask that appears after row selection
        try:
            self.page.wait_for_selector(
                ".loadmask-body-container", state="hidden", timeout=8_000
            )
        except Exception:
            pass
        self.page.get_by_role("button", name=">>> next").click()
        print(f"  [OK] Agency selected: {_AGENCY}")

    def select_customer(self) -> None:
        """Search by ZIP, pick the first result."""
        # After the agency step there is a full-page navigation — wait for it
        self.page.wait_for_load_state("domcontentloaded", timeout=20_000)
        self.page.wait_for_timeout(2_000)
        self.page.screenshot(path=str(_ROOT / "tools" / "debug_post_agency.png"), full_page=True)
        self.page.wait_for_selector("text=ZIP Code", timeout=20_000)
        self.page.get_by_role("textbox", name="ZIP Code").fill(FIXED_FIELDS["ZIP"])
        # Search button label varies (">>> Search" or "Search") — match both
        search_btn = self.page.get_by_role("button").filter(
            has_text=re.compile(r"Search", re.I)
        ).first
        search_btn.click()
        # Wait for results grid
        self.page.wait_for_selector("text=Select", timeout=15_000)
        self.page.get_by_role("button", name="Select").first.click()
        print(f"  [OK] Customer selected (ZIP {FIXED_FIELDS['ZIP']})")

    def fill_quote_registration(self, program: str) -> None:
        """Fill Producer, Program, Effective Date on the Quote Registration page."""
        self.page.wait_for_selector("text=Select Program", timeout=15_000)

        # Producer
        prod = self.page.get_by_role("combobox", name="Producer*")
        prod.click()
        self.page.get_by_role("option", name=FIXED_FIELDS["Producer"], exact=True).click()

        # Program
        prog = self.page.get_by_role("combobox", name="Program*")
        prog.scroll_into_view_if_needed()
        prog.click()
        with self.page.expect_response("**/FieldProcessorServlet*"):
            self.page.get_by_role("option", name=program, exact=True).click()
        # ExtJS may leave the dropdown list open after the response fires.
        # Dismiss it so its overlay cannot intercept subsequent clicks.
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(300)
        # Wait for all masks triggered by program selection to clear
        try:
            self.page.wait_for_function(self._NO_VISIBLE_MASK_JS, timeout=15_000)
        except Exception:
            pass

        # Effective Date — fill without clicking to avoid opening the date-picker
        # overlay (.x-mask.x-border-box) that would intercept subsequent clicks.
        eff_date = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y")
        eff = self.page.get_by_role("combobox", name="Effective Date*")
        eff.fill(eff_date)
        eff.press("Tab")  # trigger blur/change event
        # Dismiss any calendar picker that may have appeared
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(300)
        # Wait for all masks to clear (effective date may trigger server call)
        try:
            self.page.wait_for_function(self._NO_VISIBLE_MASK_JS, timeout=15_000)
        except Exception:
            pass

        print(f"  [OK] Quote registration: Program='{program}', EffDate={eff_date}")

    def discover_steps(self, max_steps: int = 10) -> list[StepDef]:
        """
        Click Next from quote registration through the LOB workflow.
        Records fields at each step.  Stops at bind or a common tail step.
        """
        # Leave quote registration
        self.page.screenshot(path=str(_ROOT / "tools" / "debug_before_first_next.png"), full_page=True)
        self._click_next()

        steps: list[StepDef] = []
        seen_names: set[str] = set()

        for i in range(max_steps):
            self._wait_for_page_settle()
            name = self._current_step_name(i + 1)

            if name in seen_names:
                print(f"  -> Loop detected at '{name}', stopping")
                break
            seen_names.add(name)

            is_common = any(kw in name for kw in COMMON_STEP_KEYWORDS)
            fields = self._extract_fields()

            steps.append(StepDef(name=name, fields=fields, is_common=is_common))
            print(f"  [OK] Step {i+1}: '{name}' — {len(fields)} field(s) | common={is_common}")
            self.page.screenshot(
                path=str(_ROOT / "tools" / f"debug_step_{i+1}_{name[:20].replace(' ','_')}.png"),
                full_page=True
            )

            # Stop when bind button is visible
            bind = self.page.locator("button").filter(has_text=re.compile(r"^bind$", re.I))
            if bind.count() and bind.first.is_visible():
                print("  -> Bind button found, workflow complete")
                break

            # Stop after last common step
            if is_common and any(kw in name for kw in ("Verify", "Billing Verification")):
                break

            # Proceed to next step
            if not self._advance():
                self.page.screenshot(
                    path=str(_ROOT / "tools" / f"debug_step_{i+1}.png"), full_page=True
                )
                print(f"  -> Cannot advance from '{name}', stopping")
                break

        return steps

    # -- private helpers -------------------------------------------------------

    # JS that returns True only when EVERY ExtJS loading mask is invisible.
    # Plain wait_for_selector(state="hidden") is unreliable here because ExtJS
    # leaves stale hidden mask divs in the DOM from earlier interactions; Playwright
    # matches the first hidden one and returns immediately even when a second mask
    # is actively intercepting pointer events.
    _NO_VISIBLE_MASK_JS = """() => {
        const SELS = [
            '#ajax-sub-pre-loading',
            '.x-mask.x-border-box',
            '.loadmask-body-container',
        ];
        for (const sel of SELS) {
            for (const el of document.querySelectorAll(sel)) {
                const r = el.getBoundingClientRect();
                if (r.width > 0 && r.height > 0) return false;
            }
        }
        return true;
    }"""

    def _wait_for_page_settle(self) -> None:
        self.page.wait_for_timeout(1_000)
        try:
            self.page.wait_for_function(self._NO_VISIBLE_MASK_JS, timeout=30_000)
        except Exception:
            pass

    def _current_step_name(self, fallback_idx: int) -> str:
        """Read step name from page breadcrumb or heading."""
        # Try the OneShield breadcrumb toolbar (last plain-text segment after ">")
        try:
            # The breadcrumb area contains text like "HOME > NEW QUOTE > Step Name"
            breadcrumb = self.page.evaluate(
                """() => {
                    // Look for toolbar items that form the breadcrumb
                    const toolbarTexts = [
                        ...document.querySelectorAll('.x-toolbar .x-box-inner .x-component')
                    ].map(el => el.innerText?.trim()).filter(t => t && t !== '>' && t !== '|');
                    return toolbarTexts.length ? toolbarTexts[toolbarTexts.length - 1] : null;
                }"""
            )
            if breadcrumb and breadcrumb.lower() not in ("home", "new quote", ""):
                return breadcrumb
        except Exception:
            pass

        # Fallback: page heading (h1/h2)
        try:
            for sel in ("h1", "h2", ".x-panel-header-title-text"):
                heading = self.page.locator(sel).first
                if heading.count() and heading.is_visible():
                    text = heading.inner_text(timeout=1_000).strip()
                    if text:
                        return text
        except Exception:
            pass

        return f"Step_{fallback_idx}"

    def _extract_fields(self) -> list[FieldDef]:
        try:
            raw: list[dict] = self.page.evaluate(_EXTRACT_FIELDS_JS)
            fields = []
            for item in raw:
                label = (item.get("label") or "").strip()
                if not label:
                    continue
                fields.append(FieldDef(
                    label=label,
                    field_type=item.get("field_type", "text"),
                    required=bool(item.get("required", False)),
                    options=item.get("options", []),
                    hint=item.get("hint", ""),
                ))
            return fields
        except Exception as exc:
            print(f"    [WARN] Field extraction error: {exc}")
            return []

    def _click_next(self) -> None:
        self._wait_for_page_settle()
        # Use JS dispatch_event so the click reaches ExtJS even when a loading
        # mask (.x-mask.x-border-box) is still intercepting Playwright pointer events.
        # This is acceptable in this discovery tool (not a page-object under test).
        clicked = self.page.evaluate("""() => {
            const btns = [...document.querySelectorAll('[role="button"]')];
            const next = btns.find(b => {
                const t = (b.innerText || b.textContent || '').trim().toLowerCase();
                return t === 'next';
            });
            if (next) {
                next.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                return true;
            }
            return false;
        }""")
        if not clicked:
            raise PWTimeout("Next button not found on page")
        self.page.wait_for_timeout(500)

    def _advance(self) -> bool:
        """Click Save (if present) then Next.  Returns False if no way forward."""
        try:
            self._wait_for_page_settle()

            # Save button (some LOB-specific pages need save first)
            save = self.page.get_by_role("button").filter(
                has_text=re.compile(r"save changes", re.I)
            )
            if save.count() and save.first.is_visible():
                save.first.click()
                self._wait_for_page_settle()

            # Next button
            nxt = self.page.get_by_role("button", name="Next")
            if nxt.count() and nxt.first.is_visible():
                self._click_next()
                return True

            # Rate Quote button (some LOBs need rating before Next appears)
            rate = self.page.get_by_role("button").filter(
                has_text=re.compile(r"rate quote", re.I)
            )
            if rate.count() and rate.first.is_visible():
                rate.first.click()
                self._wait_for_page_settle()
                nxt2 = self.page.get_by_role("button", name="Next")
                if nxt2.count() and nxt2.first.is_visible():
                    self._click_next()
                    return True

            # Request Issue button (Cyber pattern)
            issue = self.page.get_by_role("button").filter(
                has_text=re.compile(r"request issue", re.I)
            )
            if issue.count() and issue.first.is_visible():
                issue.first.click()
                self._wait_for_page_settle()
                return True

            return False
        except Exception as exc:
            print(f"    [WARN] Advance error: {exc}")
            return False


# -----------------------------------------------------------------------------
# Code Generator — Claude API
# -----------------------------------------------------------------------------

class LOBCodeGenerator:
    """Calls Claude API to generate all framework files from discovered step data."""

    def __init__(
        self,
        lob_name: str,
        lob_slug: str,
        program: str,
        steps: list[StepDef],
    ):
        self.lob_name = lob_name     # e.g. "Term Life"
        self.lob_slug = lob_slug     # e.g. "termlife"
        self.program  = program      # e.g. "Term Life"
        self.steps    = steps
        self.client   = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

    def generate(self) -> dict[str, str]:
        """Return {relative_path: file_content} for all generated files."""
        prompt = self._build_prompt()
        print("  Calling Claude API ...")
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8_000,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse(response.content[0].text)

    # -- private ---------------------------------------------------------------

    def _flow_summary(self) -> str:
        lines = []
        for step in self.steps:
            tag = "(COMMON — use existing page object)" if step.is_common else "(LOB-SPECIFIC — needs new page object)"
            lines.append(f"\n### {step.name} {tag}")
            if step.fields:
                for f in step.fields:
                    req = "*" if f.required else " "
                    opts = f"  options={f.options}" if f.options else ""
                    lines.append(f"  [{f.field_type}{req}] {f.label}{opts}")
            else:
                lines.append("  (no fields discovered)")
        return "\n".join(lines)

    def _reference_files(self) -> tuple[str, str]:
        """Load short snippets from existing LOBs as reference."""
        cyber_steps = ""
        homeowner_page = ""
        try:
            cyber_steps = (_ROOT / "ui/steps/cyber_steps.py").read_text()[:900]
        except Exception:
            pass
        try:
            homeowner_page = (
                _ROOT / "ui/pages/homeowner/homeowner_quote_summary_page.py"
            ).read_text()[:1_200]
        except Exception:
            pass
        return cyber_steps, homeowner_page

    def _build_prompt(self) -> str:
        cyber_steps, homeowner_page = self._reference_files()
        flow = self._flow_summary()
        lob_class = "".join(w.title() for w in self.lob_slug.split())

        return f"""You are generating test automation framework files for a new insurance LOB.

## LOB DETAILS
- LOB name  : {self.lob_name}
- LOB slug  : {self.lob_slug}   (used in filenames and Python identifiers)
- Class stem: {lob_class}        (e.g. TermLife -> TermLifeQuotePage)
- Program   : {self.program}     (exact dropdown value in app)

## DISCOVERED WORKFLOW STEPS AND FIELDS
{flow}

## FRAMEWORK RULES (follow exactly — no exceptions)

### Page objects
- Inherit from BasePage: `from ui.pages.common.base_page import BasePage`
- Locators defined in `__init__` using `page.get_by_role(...)`, `page.get_by_label(...)`, `page.locator(...)`
- Action methods decorated with `@allure.step(...)`
- Buttons -> `smart_click(locator)`
- Text inputs -> `smart_fill(locator, value)`
- ExtJS combobox -> `locator.click(); self.page.get_by_role("option", name=value, exact=True).click()`
- Radio groups -> `answer_question("label text", value)` from BasePage
- Spinner wait -> `self.spinner_wait("#ajax-sub-pre-loading")`

### Step definitions
- Import: `from pytest_bdd import when, given, then, parsers`
- Parameterised steps MUST use `parsers.parse()`
- Fixture names match snake_case of the LOB slug: `{self.lob_slug}_quote_page`

### Test data JSON
- Must include ALL common fields:
  FirstName, LastName, DOB (MM/DD/YYYY), Email (`name_{{{{timestamp}}}}@domain.com`),
  PhoneNum (555-xxx-xxxx), CustomerType="Individual"
  Address, ZIP="{FIXED_FIELDS["ZIP"]}", City="{FIXED_FIELDS["City"]}", State="{FIXED_FIELDS["State"]}"
  Producer="{FIXED_FIELDS["Producer"]}", Program="{self.program}", EffDateOffset="{FIXED_FIELDS["EffDateOffset"]}"
  PaymentPlan="{FIXED_FIELDS["PaymentPlan"]}"
- ZIP / City / State must ALWAYS match (ZIP 01101 = Springfield MA)
- Email MUST use literal {{{{timestamp}}}} placeholder — NEVER a real address
- LOB-specific fields: use realistic values matching discovered options

### Feature file
- Located at `ui/features/{self.lob_slug}/{self.lob_slug}_creation.feature`
- Tag: `@{self.lob_slug}`
- Scenario Outline parameterised by TC_ID
- Shared steps reused verbatim: "i create a new quote", "i create a new customer",
  "I provide quote registration details", "I complete delivery preferences",
  "I complete billing plan", "I bind the {self.lob_name} policy"

### Test entry point
- Uses `@scenario` decorator from pytest_bdd
- Marker: `@pytest.mark.{self.lob_slug}`

## REFERENCE: existing step file (cyber_steps.py)
```python
{cyber_steps}
```

## REFERENCE: existing page object (homeowner_quote_summary_page.py)
```python
{homeowner_page}
```

## OUTPUT FORMAT

Produce each file inside XML tags exactly as shown.
Use realistic placeholder locators where real IDs are unknown — add a comment
`# TODO: verify locator in app` so the developer knows to check.

<file path="testdata/static/{lob_class}Data.json">
... JSON content (wrapped in {{"testCases": [...]}}) ...
</file>

<file path="ui/pages/{self.lob_slug}/__init__.py">
</file>

<file path="ui/pages/{self.lob_slug}/{self.lob_slug}_quote_page.py">
... one class per LOB-specific step ...
</file>

<file path="ui/features/{self.lob_slug}/{self.lob_slug}_creation.feature">
... Gherkin ...
</file>

<file path="ui/steps/{self.lob_slug}_steps.py">
... pytest-bdd step definitions ...
</file>

<file path="ui/tests/test_{self.lob_slug}.py">
... @scenario test entry point ...
</file>
"""

    @staticmethod
    def _parse(raw: str) -> dict[str, str]:
        files: dict[str, str] = {}
        for match in re.finditer(r'<file path="([^"]+)">(.*?)</file>', raw, re.DOTALL):
            path    = match.group(1).strip()
            content = match.group(2).strip()
            files[path] = content
        return files


# -----------------------------------------------------------------------------
# File writer & manual-steps printer
# -----------------------------------------------------------------------------

def write_files(files: dict[str, str], dry_run: bool) -> None:
    for rel, content in files.items():
        full = _ROOT / rel
        if dry_run:
            print(f"\n{'-'*60}")
            print(f"[DRY RUN] {rel}")
            print(f"{'-'*60}")
            preview = content[:600] + ("..." if len(content) > 600 else "")
            print(textwrap.indent(preview, "  "))
        else:
            full.parent.mkdir(parents=True, exist_ok=True)
            if full.exists():
                print(f"  [WARN]  skipped (exists): {rel}")
            else:
                full.write_text(content, encoding="utf-8")
                print(f"  [OK]  {rel}")


def print_manual_steps(lob_slug: str, lob_name: str) -> None:
    lob_class = "".join(w.title() for w in lob_slug.split())
    print(f"""
{'='*60}
MANUAL WIRING REQUIRED
{'='*60}

1. conftest.py — add to pytest_plugins list:
       "ui.steps.{lob_slug}_steps",

2. ui/fixtures.py — add import + fixture:
       from ui.pages.{lob_slug}.{lob_slug}_quote_page import {lob_class}QuotePage

       @pytest.fixture
       def {lob_slug}_quote_page(page):
           return {lob_class}QuotePage(page)

3. pytest.ini — add marker:
       {lob_slug}: {lob_name} LOB tests

4. Review generated page objects:
   - Run app, open each step, inspect real field IDs/labels
   - Replace any "# TODO: verify locator" placeholders
   - Confirm combobox option strings match the app exactly

5. Add test data file path to data_steps if a custom loader is needed.
{'='*60}
""")


# -----------------------------------------------------------------------------
# CLI entry point
# -----------------------------------------------------------------------------

def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate LOB scaffold from live app discovery + Claude API"
    )
    parser.add_argument("--lob",      required=True, help="LOB display name, e.g. 'Term Life'")
    parser.add_argument("--program",  required=True, help="Exact program dropdown value, e.g. 'Term Life'")
    parser.add_argument("--headed",   action="store_true", help="Show browser window")
    parser.add_argument("--dry-run",  action="store_true", help="Print files without writing them")
    parser.add_argument("--skip-nav", action="store_true", help="Skip Playwright navigation (generate from LOB name only)")
    parser.add_argument("--max-steps", type=int, default=10, help="Max workflow steps to traverse (default 10)")
    args = parser.parse_args()

    lob_slug = slugify(args.lob)

    print(f"\n{'='*60}")
    print(f" LOB Scaffold Generator")
    print(f"{'='*60}")
    print(f" LOB     : {args.lob}  ({lob_slug})")
    print(f" Program : {args.program}")
    print(f" Dry run : {args.dry_run}")
    print(f"{'='*60}\n")

    steps: list[StepDef] = []

    # -- Phase 1: navigate app -------------------------------------------------
    if not args.skip_nav:
        print("Phase 1 — Navigating app to discover workflow steps ...\n")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not args.headed)
            ctx  = browser.new_context(viewport=None)
            page = ctx.new_page()

            try:
                nav = AppNavigator(page)
                nav.login()
                nav.start_new_quote()
                nav.select_customer()
                nav.fill_quote_registration(args.program)
                steps = nav.discover_steps(max_steps=args.max_steps)
            except Exception as exc:
                print(f"\n[ERROR] Navigation failed: {exc}")
                import traceback
                traceback.print_exc()
                sys.exit(1)
            finally:
                browser.close()

        if not steps:
            print("[ERROR] No steps discovered — try --headed to debug the browser flow")
            sys.exit(1)

        print(f"\n  Total steps discovered: {len(steps)}")
    else:
        print("Phase 1 — Skipped (--skip-nav)\n")
        # Minimal placeholder so generator still works
        steps = [StepDef(name="Quote Details", fields=[], is_common=False)]

    # -- Phase 2: generate via Claude ------------------------------------------
    print("\nPhase 2 — Generating framework files via Claude API ...\n")

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("[ERROR] ANTHROPIC_API_KEY not set in .env")
        sys.exit(1)

    gen = LOBCodeGenerator(
        lob_name=args.lob,
        lob_slug=lob_slug,
        program=args.program,
        steps=steps,
    )
    try:
        files = gen.generate()
    except Exception as exc:
        print(f"[ERROR] Claude API error: {exc}")
        sys.exit(1)

    print(f"  Generated {len(files)} file(s)")

    # -- Phase 3: write files --------------------------------------------------
    print("\nPhase 3 — Writing files ...\n")
    write_files(files, dry_run=args.dry_run)

    print_manual_steps(lob_slug, args.lob)
    print("Done [OK]\n")


if __name__ == "__main__":
    main()
