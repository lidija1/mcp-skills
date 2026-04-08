"""
Singleton browser session for the LOB recorder.

Keeps a headed Playwright browser open across MCP tool calls so the user
can interact with the page between calls.
"""

import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_pw = None
_browser = None
_page = None
_lob_name: str = ""
_captured_pages: list[dict] = []      # [{page_name, fields, interactions}]
_current_interactions: list = []       # raw JS interaction log for current page


# JS snippet injected after every navigation to capture user interactions
_INJECT_JS = """
(function () {
  if (window.__lob_recorder_v1) return;
  window.__lob_recorder_v1 = true;
  window.__lob_interactions = [];

  function _label(el) {
    if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
    if (el.id) {
      const lbl = document.querySelector('label[for="' + el.id + '"]');
      if (lbl) return lbl.textContent.trim();
    }
    // walk up to find ExtJS label
    let p = el.parentElement;
    for (let i = 0; i < 6; i++) {
      if (!p) break;
      const lbl = p.querySelector('.x-form-item-label-text');
      if (lbl) return lbl.textContent.trim();
      p = p.parentElement;
    }
    return el.name || el.id || '';
  }

  function _push(el, value, ev_type) {
    window.__lob_interactions.push({
      event: ev_type,
      tag: el.tagName,
      role: el.getAttribute('role') || el.type || el.tagName.toLowerCase(),
      aria_label: el.getAttribute('aria-label') || '',
      id: el.id || null,
      name_attr: el.name || null,
      label: _label(el),
      value: value,
      ts: Date.now(),
    });
  }

  // native inputs
  document.addEventListener('change', function (e) {
    var el = e.target;
    if (/^(INPUT|SELECT|TEXTAREA)$/i.test(el.tagName)) {
      var val = el.type === 'checkbox' ? (el.checked ? 'Yes' : 'No') : el.value;
      _push(el, val, 'change');
    }
  }, true);

  // radio / checkbox clicks
  document.addEventListener('click', function (e) {
    var el = e.target;
    if (el.type === 'radio' || el.type === 'checkbox') {
      _push(el, el.type === 'checkbox' ? (el.checked ? 'Yes' : 'No') : el.value, 'click');
    }
    // ExtJS boundlist selection — record selected text + nearest combobox label
    var item = el.closest ? el.closest('.x-boundlist-item') : null;
    if (item) {
      var val = item.textContent.trim();
      // find the most recently focused combobox
      var combos = Array.from(document.querySelectorAll('[role="combobox"]'));
      var focused = combos.find(function(c) { return c === document.activeElement; })
                  || combos[combos.length - 1];
      var label = focused ? (focused.getAttribute('aria-label') || _label(focused)) : '';
      window.__lob_interactions.push({
        event: 'boundlist_click',
        tag: 'COMBOBOX',
        role: 'combobox',
        aria_label: label,
        id: focused ? focused.id : null,
        name_attr: null,
        label: label,
        value: val,
        ts: Date.now(),
      });
    }
  }, true);
})();
"""

# ---------------------------------------------------------------------------
# DOM scanner — returns all visible ARIA form fields on the page
# ---------------------------------------------------------------------------

_SCAN_JS = """
() => {
  var fields = [];
  var seen = new Set();

  // ARIA role elements
  var roleMap = {
    'combobox': 'combobox',
    'textbox': 'textbox',
    'spinbutton': 'spinbutton',
    'checkbox': 'checkbox',
    'radio': 'radio',
  };

  Object.keys(roleMap).forEach(function(role) {
    document.querySelectorAll('[role="' + role + '"]').forEach(function(el) {
      if (seen.has(el)) return;
      var rect = el.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) return; // hidden
      seen.add(el);
      var ariaLabel = el.getAttribute('aria-label') || '';
      if (!ariaLabel) return;
      fields.push({
        playwright_role: roleMap[role],
        label: ariaLabel,
        value: el.value || '',
        required: ariaLabel.endsWith('*'),
        field_name: ariaLabel.replace(/\\*$/, '').trim(),
        id: el.id || null,
      });
    });
  });

  // native inputs with aria-label that don't have an explicit role
  ['input', 'textarea', 'select'].forEach(function(tag) {
    document.querySelectorAll(tag + ':not([role])').forEach(function(el) {
      if (seen.has(el)) return;
      var rect = el.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) return;
      seen.add(el);
      var ariaLabel = el.getAttribute('aria-label') || el.name || '';
      if (!ariaLabel) return;
      var pw_role = (el.type === 'checkbox') ? 'checkbox'
                  : (el.tagName === 'SELECT') ? 'combobox'
                  : 'textbox';
      fields.push({
        playwright_role: pw_role,
        label: ariaLabel,
        value: el.value || '',
        required: ariaLabel.endsWith('*'),
        field_name: ariaLabel.replace(/\\*$/, '').trim(),
        id: el.id || null,
      });
    });
  });

  // Radio groups
  var radioGroups = {};
  document.querySelectorAll('[role="radio"], input[type="radio"]').forEach(function(el) {
    if (seen.has(el)) return;
    seen.add(el);
    var gName = el.getAttribute('name') || el.closest('[role="radiogroup"]')?.id || 'unknown';
    if (!radioGroups[gName]) radioGroups[gName] = { options: [], checked: null, group_label: '' };
    var lbl = el.getAttribute('aria-label') || el.value || '';
    radioGroups[gName].options.push(lbl);
    if (el.checked || el.getAttribute('aria-checked') === 'true') {
      radioGroups[gName].checked = lbl;
    }
    // try to find group label
    var grp = el.closest('[role="radiogroup"]') || el.closest('fieldset');
    if (grp && !radioGroups[gName].group_label) {
      var leg = grp.querySelector('legend, .x-form-item-label-text');
      radioGroups[gName].group_label = leg ? leg.textContent.trim() : '';
    }
  });
  Object.keys(radioGroups).forEach(function(gName) {
    var g = radioGroups[gName];
    fields.push({
      playwright_role: 'radiogroup',
      label: g.group_label || gName,
      value: g.checked || '',
      options: g.options,
      required: false,
      field_name: (g.group_label || gName).replace(/\\*$/, '').trim(),
    });
  });

  // Visible action buttons
  var buttons = [];
  document.querySelectorAll('[role="button"], button').forEach(function(el) {
    if (seen.has(el)) return;
    var rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) return;
    seen.add(el);
    var label = el.getAttribute('aria-label') || el.textContent.trim();
    if (label) buttons.push(label);
  });

  return { fields: fields, buttons: buttons };
}
"""


def get_page():
    return _page


def get_lob_name():
    return _lob_name


def get_captured_pages():
    return _captured_pages


def inject_listeners():
    """Inject the JS event listener into the current page (idempotent)."""
    global _page
    if _page:
        _page.evaluate(_INJECT_JS)


def scan_dom():
    """Scan the current page DOM and return structured field info."""
    global _page
    if not _page:
        return {"fields": [], "buttons": []}
    return _page.evaluate(_SCAN_JS)


def read_interactions():
    """Read and clear the JS interaction log."""
    global _page
    if not _page:
        return []
    interactions = _page.evaluate("() => window.__lob_interactions || []")
    _page.evaluate("() => { window.__lob_interactions = []; }")
    return interactions


def start_session(lob_name: str, program: str) -> str:
    """
    Open a headed browser, login, and navigate through common steps
    until the LOB-specific quote page is reached.
    Returns status message.
    """
    global _pw, _browser, _page, _lob_name, _captured_pages

    # Clean up any previous session
    if _browser:
        try:
            _browser.close()
        except Exception:
            pass
    if _pw:
        try:
            _pw.stop()
        except Exception:
            pass

    _lob_name = lob_name.lower().strip()
    _captured_pages = []

    from playwright.sync_api import sync_playwright  # noqa
    headless = os.environ.get("LOB_HEADLESS", "true").lower() != "false"
    _pw = sync_playwright().start()
    _browser = _pw.chromium.launch(headless=headless, slow_mo=50)
    context = _browser.new_context(viewport={"width": 1440, "height": 900})
    _page = context.new_page()
    _page.set_default_timeout(60_000)

    # Run common steps
    from ui.pages.common.login_page import LoginPage
    from ui.pages.common.new_quote_page import NewQuotePage
    from ui.pages.common.customer_page import CustomerPage

    # Minimal persona for common steps
    eff_date = (date.today() + timedelta(days=1)).strftime("%m/%d/%Y")
    _persona = {
        "CustomerType": "Individual",
        "FirstName": "Recorder",
        "LastName": "Session",
        "DOB": "01/15/1985",
        "PhoneNum": "555-123-4567",
        "Email": f"recorder_{int(time.time())}@lob.com",
        "Address": "230 Old Taunton Ave",
        "ZIP": "01101",
        "State": "Massachusetts",
        "City": "Springfield",
        "Producer": "Janis Irey",
        "EffDateOffset": "1",
        "Program": program,
        "PaymentPlan": "Pay In Full",
    }

    login = LoginPage(_page)
    login.navigate()
    login.click_splash_button()
    login.wait_for_login_page()
    login.fill_credentials_from_env()
    login.click_login()
    _page.get_by_role("button", name="quotes").wait_for(state="visible", timeout=30_000)

    NewQuotePage(_page).new_quote_steps()
    CustomerPage(_page).customer_steps(_persona)

    # Quote registration — select program
    from ui.pages.auto.quote_registration_page import QuoteRegistrationPage
    QuoteRegistrationPage(_page).quote_registration_steps(_persona)

    inject_listeners()

    mode = "headless" if headless else "headed"
    return (
        f"Browser open and ready ({mode} mode).\n"
        f"LOB: {lob_name!r} | Program: {program!r}\n\n"
        f"You are now on the first LOB-specific page.\n\n"
        f"Headless workflow:\n"
        f"  1. Call take_screenshot('page_name') to see the current state.\n"
        f"  2. Call scan_page('page_name') to discover all fields.\n"
        f"  3. Fill fields: fill_field(label, value) / select_option(label, value) / answer_radio(group, answer)\n"
        f"  4. Call click_button('Next') to advance.\n"
        f"  5. Repeat until all pages are captured.\n"
        f"  6. Call generate_scaffold_files() to produce the pytest-bdd scaffold.\n\n"
        f"Tip: Set LOB_HEADLESS=false in your .env to open a visible browser locally."
    )


_BOUNDLIST_VISIBLE_JS = (
    "() => [...document.querySelectorAll('.x-boundlist-item')]"
    ".some(el => { const r = el.getBoundingClientRect();"
    " return r.width > 0 && r.height > 0; })"
)

_SELECT_ITEM_JS = """(text) => {
    const items = [...document.querySelectorAll('.x-boundlist-item')];
    const visible = items.filter(el => {
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
    });
    const match = visible.find(el => el.textContent.trim() === text);
    if (match) match.click();
    else throw new Error('Option not found: ' + text);
}"""


def fill_field(label: str, value: str) -> str:
    """Fill a textbox by its aria-label."""
    global _page
    loc = _page.get_by_role("textbox", name=label)
    loc.scroll_into_view_if_needed()
    loc.clear()
    loc.fill(value)
    actual = loc.input_value()
    if actual != value:
        loc.type(value)
    return f"Filled '{label}' → '{value}'"


def select_option(label: str, value: str) -> str:
    """Select a value from an ExtJS combobox by its aria-label."""
    global _page
    loc = _page.get_by_role("combobox", name=label)
    loc.scroll_into_view_if_needed()
    loc.click()
    try:
        _page.wait_for_function(_BOUNDLIST_VISIBLE_JS, timeout=3000)
    except Exception:
        _page.keyboard.press("ArrowDown")
        _page.wait_for_function(_BOUNDLIST_VISIBLE_JS, timeout=5000)
    _page.evaluate(_SELECT_ITEM_JS, value)
    time.sleep(0.3)
    return f"Selected '{value}' in '{label}'"


def answer_radio(group_label: str, answer: str) -> str:
    """Click a radio button option within a named radio group."""
    global _page
    # Try aria-label match first, then fall back to value/text
    radio = _page.locator(
        f'[role="radio"][aria-label="{answer}"], input[type="radio"][value="{answer}"]'
    ).first
    if not radio.is_visible():
        # walk up to find the group by label and pick by option text
        _page.evaluate(
            """([group, answer]) => {
                const labels = [...document.querySelectorAll('.x-form-item-label-text')];
                const grpLabel = labels.find(l => l.textContent.trim().replace('*','') === group);
                if (!grpLabel) throw new Error('Group not found: ' + group);
                const container = grpLabel.closest('.x-form-item') || grpLabel.parentElement;
                const radios = [...container.querySelectorAll('[role="radio"], input[type="radio"]')];
                const target = radios.find(r =>
                    r.getAttribute('aria-label') === answer || r.value === answer
                );
                if (!target) throw new Error('Option not found: ' + answer);
                target.dispatchEvent(new MouseEvent('click', {bubbles: true}));
            }""",
            [group_label, answer],
        )
    else:
        radio.dispatch_event("click")
    time.sleep(0.2)
    return f"Selected radio '{answer}' in group '{group_label}'"


def take_screenshot(name: str = "page") -> str:
    """Take a screenshot and save to reports/lob_recorder/. Returns file path."""
    global _page
    if not _page:
        return "No active session."
    out_dir = _PROJECT_ROOT / "reports" / "lob_recorder"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = name.replace(" ", "_").lower()
    path = out_dir / f"{safe_name}.png"
    _page.screenshot(path=str(path), full_page=False)
    return str(path)


def capture_page(page_name: str) -> dict:
    """
    Capture the current page: DOM scan + interaction log.
    Returns a summary dict.
    """
    global _captured_pages

    interactions = read_interactions()
    dom_data = scan_dom()

    page_data = {
        "page_name": page_name,
        "fields": dom_data.get("fields", []),
        "buttons": dom_data.get("buttons", []),
        "interactions": interactions,
    }
    _captured_pages.append(page_data)

    field_count = len(page_data["fields"])
    interaction_count = len(interactions)
    return {
        "page_name": page_name,
        "fields_found": field_count,
        "interactions_captured": interaction_count,
        "fields": page_data["fields"],
        "buttons": page_data["buttons"],
    }


def click_button(label: str) -> str:
    """Click a button by label, then re-inject event listeners."""
    global _page
    if not _page:
        return "No active browser session."
    _page.get_by_role("button", name=label).click()
    time.sleep(1.5)  # wait for page transition / spinner
    inject_listeners()
    return f"Clicked '{label}'. Listeners re-injected on new page."


def stop_session() -> str:
    """Close the browser and clean up."""
    global _pw, _browser, _page
    try:
        if _browser:
            _browser.close()
        if _pw:
            _pw.stop()
    except Exception:
        pass
    _browser = None
    _page = None
    _pw = None
    return "Browser session closed."
