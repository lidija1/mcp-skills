"""Personal Auto field and dropdown discovery probe.

Creates one quote, inventories Auto controls and combobox options, probes a
small set of conditional values, and stops on Coverages without rating or
binding.

Usage:
    python tools/probe_auto_elements.py
    python tools/probe_auto_elements.py --headed --slow-mo 100
"""

import argparse
import json
import os
import re
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.pages.auto.driver_info_page import DriverInfoPage
from ui.pages.auto.quote_summary_page import QuoteSummaryPage
from ui.pages.auto.vehicle_info_page import VehicleInfoPage
from ui.pages.common.customer_page import CustomerPage
from ui.pages.common.login_page import LoginPage
from ui.pages.common.new_quote_page import NewQuotePage
from ui.pages.common.quote_registration_page import QuoteRegistrationPage


OUTPUT_DIR = ROOT / "reports" / "lob-discovery" / "auto"
KNOWN_LABELS = {
    "Billing Method*",
    "Gender*",
    "Prefix",
    "MI/Middle Name",
    "Suffix",
    "Relationship to Insured",
    "SSN",
    "Marital Status*",
    "Driver Status*",
    "Employment Category",
    "Occupation",
    "License Status*",
    "Country of Issue",
    "License State/Province",
    "License Year",
    "License Number",
    "SR-22 Filing State",
    "Vehicle Type*",
    "Vehicle Detail Entry Mode",
    "Year*",
    "Make*",
    "Model*",
    "Specification*",
    "Vehicle Use*",
    "Ownership",
    "Physical Damage Symbol (Override)",
    "Address Line 1",
    "City",
    "State/Province",
    "ZIP",
    "Interest Type",
    "Loss Payee/Additional Interest Name",
    "Policy Coverage Option*",
}


def load_case():
    path = ROOT / "testdata" / "static" / "auto" / "AutoData.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    data = deepcopy(payload["testCases"][0])
    suffix = datetime.now().strftime("%H%M%S")
    data.update(
        {
            "TC_ID": "TC_ID_AUTO_DISCOVERY_0001",
            "TestName": "Inventory Personal Auto optional fields and dropdowns",
            "Description": "Stops on Coverages without rating or binding",
            "FirstName": "Daria",
            "LastName": f"Discovery{suffix}",
            "Email": f"auto_discovery_{suffix}_{{timestamp}}@example.com",
        }
    )
    return data


def normalize_label(value):
    return re.sub(r"\s+", " ", value or "").strip()


def visible_controls(page):
    return page.evaluate(
        """() => {
            const visible = el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0
                    && style.display !== 'none'
                    && style.visibility !== 'hidden';
            };
            const norm = value => (value || '').replace(/\\s+/g, ' ').trim();
            const labelFor = el => {
                const id = el.id || '';
                const explicit = id
                    ? document.querySelector('label[for="' + CSS.escape(id) + '"]')
                    : null;
                const field = el.closest(
                    '.x-field, .x-form-item, fieldset, td, div[class*="field"]'
                );
                const nearby = field
                    ? field.querySelector(
                        'label, legend, .x-form-item-label, .x-form-cb-label'
                    )
                    : null;
                return norm(
                    el.getAttribute('aria-label')
                    || (explicit && explicit.textContent)
                    || (nearby && nearby.textContent)
                    || el.getAttribute('placeholder')
                );
            };
            return [...document.querySelectorAll(
                'input, textarea, select, button, a, [role="combobox"], '
                + '[role="checkbox"], [role="radio"], [role="radiogroup"], '
                + '[role="button"]'
            )]
                .filter(visible)
                .map(el => ({
                    tag: el.tagName.toLowerCase(),
                    type: el.getAttribute('type'),
                    role: el.getAttribute('role'),
                    label: labelFor(el),
                    text: norm(el.textContent),
                    value: 'value' in el ? norm(el.value) : '',
                    required: el.required
                        || el.getAttribute('aria-required') === 'true'
                        || labelFor(el).endsWith('*'),
                    disabled: el.disabled
                        || el.getAttribute('aria-disabled') === 'true',
                    readOnly: el.readOnly,
                    osviewid: el.getAttribute('osviewid'),
                    name: el.getAttribute('name'),
                }))
                .filter(item => item.label || item.text || item.value);
        }"""
    )


def visible_comboboxes(page):
    controls = visible_controls(page)
    seen = set()
    result = []
    for control in controls:
        if control.get("role") != "combobox":
            continue
        key = control.get("osviewid") or control.get("name") or (
            control.get("label"),
            control.get("value"),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(control)
    return result


def locator_for_control(page, control):
    if control.get("osviewid"):
        return page.locator(f'[osviewid="{control["osviewid"]}"]').first
    label = control.get("label")
    if label:
        return page.get_by_role("combobox", name=label, exact=True).first
    return None


def collect_options(page, control):
    locator = locator_for_control(page, control)
    if locator is None:
        return {"error": "No stable locator metadata"}
    try:
        locator.scroll_into_view_if_needed()
        locator.click()
        page.wait_for_function(
            """() => [...document.querySelectorAll('.x-boundlist')]
                .some(list => {
                    const rect = list.getBoundingClientRect();
                    const style = window.getComputedStyle(list);
                    return rect.width > 0 && rect.height > 0
                        && style.display !== 'none'
                        && style.visibility !== 'hidden';
                })""",
            timeout=7_000,
        )
        options = page.evaluate(
            """() => {
                const visible = el => {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    return rect.width > 0 && rect.height > 0
                        && style.display !== 'none'
                        && style.visibility !== 'hidden';
                };
                const lists = [...document.querySelectorAll('.x-boundlist')]
                    .filter(visible);
                const active = lists[lists.length - 1];
                return [...active.querySelectorAll('.x-boundlist-item')]
                    .filter(visible)
                    .filter(item => !item.classList.contains('x-item-disabled'))
                    .map(item => (item.textContent || '')
                        .replace(/\\s+/g, ' ').trim())
                    .filter(Boolean);
            }"""
        )
        return list(dict.fromkeys(options))
    except Exception as exc:
        return {"error": str(exc)}
    finally:
        page.keyboard.press("Escape")
        page.wait_for_timeout(100)


def snapshot_screen(page, name):
    controls = visible_controls(page)
    dropdowns = {}
    for index, control in enumerate(visible_comboboxes(page), start=1):
        label = control.get("label") or f"unlabeled_combobox_{index}"
        key = label
        if key in dropdowns:
            key = f"{label} [{index}]"
        dropdowns[key] = {
            "control": control,
            "selectableOptions": collect_options(page, control),
        }
    unmapped = []
    for control in controls:
        label = normalize_label(control.get("label"))
        if label and label not in KNOWN_LABELS:
            unmapped.append(control)
    return {
        "name": name,
        "url": page.url,
        "controls": controls,
        "dropdowns": dropdowns,
        "unmappedCandidates": unmapped,
    }


def select_and_snapshot(page_object, locator, value, screen_name):
    page_object.select_extjs_option(
        locator,
        value,
        wait_for_response=True,
        url_parts=["FieldProcessorServlet"],
    )
    page_object.wait_for_app_ready()
    return snapshot_screen(page_object.page, screen_name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--slow-mo", type=int, default=50)
    args = parser.parse_args()

    load_dotenv(ROOT / ".env", override=True)
    data = load_case()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    technical_failures = []
    combinations = []
    screens = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=not args.headed,
            slow_mo=args.slow_mo,
        )
        context = browser.new_context(viewport=None)
        page = context.new_page()

        login = LoginPage(page)
        login.navigate(os.getenv("BASE_URL"))
        if page.locator(login.employee_portal).is_visible(timeout=3_000):
            login.click_splash_button()
        login.wait_for_login_page()
        login.fill_credentials_from_env()
        login.click_login()

        NewQuotePage(page).new_quote_steps()
        CustomerPage(page).customer_steps(data)
        QuoteRegistrationPage(page).quote_registration_steps(data)

        quote = QuoteSummaryPage(page)
        screens.append(snapshot_screen(page, "Quote Summary"))
        quote.summary_steps(data)

        driver = DriverInfoPage(page)
        driver.set_gender(data)
        driver.set_marital_status(data)
        driver.set_driver_status(data)
        driver.set_employment_category(data)
        driver.set_occupation(data)
        driver.set_license_status(data)
        driver.set_defensive_driver(data)
        screens.append(snapshot_screen(page, "Driver Information - baseline"))

        for value in ("Yes", "No", "Yes"):
            try:
                driver.set_sr22_required({**data, "SR22": value})
                snap = snapshot_screen(
                    page, f"Driver Information - SR-22 {value}"
                )
                combinations.append(
                    {
                        "id": f"AUTO-SR22-{len(combinations) + 1:03d}",
                        "testName": f"SR-22 required {value}",
                        "values": {"SR22": value},
                        "result": "captured",
                        "screen": snap,
                    }
                )
            except Exception as exc:
                technical_failures.append(
                    {"combination": f"SR22={value}", "error": str(exc)}
                )
                break
        driver.set_sr22_required({**data, "SR22": "No"})
        driver.click_save()
        driver.click_vehicle_info_link()

        vehicle = VehicleInfoPage(page)
        vehicle.set_year(data)
        vehicle.set_make(data)
        vehicle.set_model(data)
        vehicle.set_specification(data)
        vehicle.set_vehicle_use(data)
        vehicle.set_ownership(data)
        screens.append(snapshot_screen(page, "Vehicle Information - baseline"))

        for value in ("Leased", "Owned", "Financed", "Owned"):
            try:
                snap = select_and_snapshot(
                    vehicle,
                    vehicle.ownership,
                    value,
                    f"Vehicle Information - ownership {value}",
                )
                combinations.append(
                    {
                        "id": f"AUTO-OWNERSHIP-{len(combinations) + 1:03d}",
                        "testName": f"Vehicle ownership {value}",
                        "values": {"Ownership": value},
                        "result": "captured",
                        "screen": snap,
                    }
                )
            except Exception as exc:
                technical_failures.append(
                    {"combination": f"Ownership={value}", "error": str(exc)}
                )
                break

        vehicle.set_ownership(data)
        vehicle.click_save()
        vehicle.click_coverages_link()
        screens.append(snapshot_screen(page, "Coverages"))

        generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
        result = {
            "schemaVersion": 1,
            "lob": "auto",
            "generatedAt": generated_at,
            "sourceScenario": "tools/probe_auto_elements.py",
            "limits": {
                "runtimeMinutes": 45,
                "maxCombinations": 30,
                "maxConsecutiveTechnicalFailures": 5,
                "maxBoundPolicies": 0,
            },
            "quotesCreated": 1,
            "rated": False,
            "requestedIssue": False,
            "boundPolicies": 0,
            "screens": screens,
            "combinations": combinations,
            "diff": {
                "newElements": [],
                "removedElements": [],
                "changedSelectors": [],
                "changedOptions": [],
                "changedTriggers": [],
            },
            "technicalFailures": technical_failures,
            "blockedBranches": [],
        }

        history_dir = OUTPUT_DIR / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        latest_path = OUTPUT_DIR / "latest.json"
        latest_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        (history_dir / f"{timestamp}.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        baseline_path = OUTPUT_DIR / "baseline.json"
        if not baseline_path.exists():
            baseline_path.write_text(
                json.dumps(result, indent=2), encoding="utf-8"
            )

        print(f"Auto discovery inventory written to {latest_path}")
        print(f"Technical failures: {len(technical_failures)}")
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
