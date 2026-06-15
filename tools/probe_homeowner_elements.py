"""Homeowner field and conditional-control discovery probe.

Creates one quote, inventories visible controls and dropdown options, probes
high-value Yes/No conditions, and stops on Bind Information without rating,
requesting issue, or binding.

Usage:
    python tools/probe_homeowner_elements.py
    python tools/probe_homeowner_elements.py --headed --slow-mo 100
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

from ui.pages.common.customer_page import CustomerPage
from ui.pages.common.login_page import LoginPage
from ui.pages.common.new_quote_page import NewQuotePage
from ui.pages.common.quote_registration_page import QuoteRegistrationPage
from ui.pages.homeowner.homeowner_city_information_page import HomeownerCityInformationPage
from ui.pages.homeowner.homeowner_coverage_page import HomeownerCoveragePage
from ui.pages.homeowner.homeowner_quote_summary_page import HomeOwnerQuoteSummaryPage


OUTPUT_DIR = ROOT / "reports" / "lob-discovery" / "homeowner"

KNOWN_LABELS = {
    "Billing Method",
    "Program Type",
    "Quote Name",
    "Term",
    "Effective Date",
    "Expiration Date",
    "Prefix",
    "First Name",
    "MI/Middle Name",
    "Last Name",
    "Suffix",
    "DOB",
    "Address Line 1",
    "City",
    "State",
    "ZIP",
    "Country",
    "Policy Coverage Option",
    "Residence Type",
    "Replacement cost contents?",
    "Replacement Cost",
    "Contents",
    "Loss of Use",
    "Other Structures",
    "All Perils Deductible",
    "Windstorm or Hail",
    "Liability",
    "Medical Payments",
    "Year Built",
    "Construction Type",
    "Protection Class",
    "BCEG",
    "Roof Type",
    "Roof Shape",
    "Secondary Water Resistance",
    "Opening Protection",
    "Roof Wall Connection",
    "Roof Deck",
    "Roof Deck Attachment",
    "Distance to Shore",
    "Central Reporting Fire Alarm",
    "Guard Gated Community",
    "Central Reporting Burglar Alarm",
    "Residential Sprinkler System",
    "Permanently Installed Generator",
    "Lightning Protection System",
    "Gas Leak Detector",
    "External Perimeter Gate",
    "Full Time Live In Caretaker",
    "24 Hour Door Man",
    "Locked or Manned Elevator",
    "Surveillance Camera",
    "24 Hour Signal Continuity",
    "Sprinkler System with Waterflow",
    "Perimeter Security Protection",
    "Existing Agency Client?",
    "Has any company cancelled or refused to insure in the past 3 years?",
    "Has coverage been non-renewed or Declined?",
    "Is Child or Day Care run out",
    "Any underground oil or",
    "Is the residence rented more",
    "Is the residence vacant?",
    "Are there any animals or",
    "Is the residence under construction or major renovation?",
    "Has the customer lived at this location for less than 3 years?",
    "Any losses in the last three years?",
    "Swimming Pool",
    "Pool",
}

IGNORED_TEXT = {
    "save changes",
    "DELETE",
    "Add",
    "Bind Information",
    "Homeowner",
}


def load_case():
    path = ROOT / "testdata" / "static" / "homeowner" / "HomeData.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    data = deepcopy(payload["testCases"][0])
    suffix = datetime.now().strftime("%H%M%S")
    data.update(
        {
            "TC_ID": "TC_ID_HOMEOWNER_DISCOVERY_0001",
            "TestName": "Inventory Homeowner fields and conditional controls",
            "Description": "Stops on Bind Information without rating or binding",
            "FirstName": "Holly",
            "LastName": f"Discovery{suffix}",
            "Email": f"homeowner_discovery_{suffix}_{{timestamp}}@example.com",
            "Address": f"{700 + int(suffix[-2:])} Old Taunton Ave",
        }
    )
    data.pop("Pool", None)
    return data


def normalize(value):
    value = re.sub(r"\s+", " ", value or "").strip()
    return value.rstrip("*").strip()


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
                const labelledBy = el.getAttribute('aria-labelledby');
                const ariaLabel = labelledBy
                    ? labelledBy.split(/\\s+/)
                        .map(part => document.getElementById(part))
                        .filter(Boolean)
                        .map(node => node.textContent)
                        .join(' ')
                    : '';
                const field = el.closest(
                    '.x-field, .x-form-item, .x-form-fieldcontainer, '
                    + 'fieldset, td, div[class*="field"]'
                );
                const nearby = field
                    ? field.querySelector(
                        'label, legend, .x-form-item-label, .x-form-cb-label'
                    )
                    : null;
                return norm(
                    el.getAttribute('aria-label')
                    || ariaLabel
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
                    readOnly: Boolean(el.readOnly)
                        || el.getAttribute('aria-readonly') === 'true',
                    osviewid: el.getAttribute('osviewid'),
                    name: el.getAttribute('name'),
                }))
                .filter(item => item.label || item.text || item.value);
        }"""
    )


def dedupe_controls(controls):
    seen = set()
    result = []
    for control in controls:
        key = (
            control.get("osviewid")
            or control.get("name")
            or (
                control.get("tag"),
                control.get("role"),
                control.get("label"),
                control.get("text"),
                control.get("value"),
            )
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(control)
    return result


def locator_for_combobox(page, control):
    if control.get("osviewid"):
        return page.locator(f'[osviewid="{control["osviewid"]}"]').first
    label = control.get("label")
    if label:
        return page.get_by_role("combobox", name=label, exact=True).first
    return None


def collect_options(page, control):
    locator = locator_for_combobox(page, control)
    if locator is None or control.get("readOnly") or control.get("disabled"):
        return []
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
            timeout=5_000,
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


def is_known(control):
    label = normalize(control.get("label"))
    text = normalize(control.get("text"))
    if label and any(label.startswith(known) for known in KNOWN_LABELS):
        return True
    if text in IGNORED_TEXT:
        return True
    return False


def snapshot_screen(page, name):
    controls = dedupe_controls(visible_controls(page))
    dropdowns = {}
    for index, control in enumerate(
        item for item in controls if item.get("role") == "combobox"
    ):
        label = normalize(control.get("label")) or f"unlabeled_combobox_{index + 1}"
        key = label if label not in dropdowns else f"{label} [{index + 1}]"
        dropdowns[key] = {
            "control": control,
            "selectableOptions": collect_options(page, control),
        }
    return {
        "name": name,
        "url": page.url,
        "controls": controls,
        "dropdowns": dropdowns,
        "unmappedCandidates": [
            control for control in controls if not is_known(control)
        ],
    }


def control_keys(snapshot):
    return {
        normalize(control.get("label"))
        or normalize(control.get("text"))
        or control.get("osviewid")
        for control in snapshot["controls"]
    }


def diff_snapshots(baseline, changed):
    baseline_keys = control_keys(baseline)
    changed_keys = control_keys(changed)
    return {
        "newControls": sorted(changed_keys - baseline_keys),
        "removedControls": sorted(baseline_keys - changed_keys),
    }


def answer_and_snapshot(page_object, group_name, value, screen_name):
    page_object.answer_question(group_name, value)
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

        try:
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

            quote = HomeOwnerQuoteSummaryPage(page)
            quote_baseline = snapshot_screen(page, "Quote Summary - baseline")
            screens.append(quote_baseline)
            quote_conditions = (
                ("DayCare", "Is Child or Day Care run out"),
                ("UndergroundOil", "Any underground oil or"),
                ("ResidenceRented", "Is the residence rented more"),
                ("ResidenceVacant", "Is the residence vacant?"),
                ("Animals", "Are there any animals or"),
            )
            for key, group in quote_conditions:
                try:
                    changed = answer_and_snapshot(
                        quote, group, "Yes", f"Quote Summary - {key} Yes"
                    )
                    combinations.append(
                        {
                            "id": f"HO-QUOTE-{len(combinations) + 1:03d}",
                            "testName": f"{key} Yes",
                            "values": {key: "Yes"},
                            "result": diff_snapshots(quote_baseline, changed),
                            "screen": changed,
                        }
                    )
                    answer_and_snapshot(quote, group, "No", f"{key} reset")
                except Exception as exc:
                    technical_failures.append(
                        {"combination": f"{key}=Yes", "error": str(exc)}
                    )

            quote.summary_steps(data)
            city = HomeownerCityInformationPage(page)
            screens.append(snapshot_screen(page, "City Information"))
            city.click_save()
            city.click_homeowners_link(data)

            coverage = HomeownerCoveragePage(page)
            coverage.set_residency(data)
            coverage.set_coverage(data)
            coverage.wait_for_loader_to_disappear()
            product_baseline = snapshot_screen(
                page, "Location Coverage - Homeowner Gold prefill"
            )
            for value in ("Condo/Co-op", "Tenants", "Homeowner"):
                try:
                    coverage.select_extjs_option(
                        coverage.residence_type,
                        value,
                        wait_for_response=True,
                        url_parts=["FieldProcessorServlet"],
                    )
                    coverage.wait_for_app_ready()
                    changed = snapshot_screen(
                        page, f"Location Coverage - Residence Type {value}"
                    )
                    combinations.append(
                        {
                            "id": f"HO-PRODUCT-{len(combinations) + 1:03d}",
                            "testName": f"Residence Type {value}",
                            "values": {"ResidenceType": value},
                            "result": diff_snapshots(product_baseline, changed),
                            "screen": changed,
                        }
                    )
                except Exception as exc:
                    technical_failures.append(
                        {
                            "combination": f"ResidenceType={value}",
                            "error": str(exc),
                        }
                    )

            coverage.set_residency(data)
            for value in ("Bronze", "Silver", "Platinum", "Gold"):
                try:
                    coverage.select_extjs_option(
                        coverage.policy_coverage,
                        value,
                        wait_for_response=True,
                        url_parts=["FieldProcessorServlet"],
                    )
                    coverage.wait_for_app_ready()
                    changed = snapshot_screen(
                        page, f"Location Coverage - Package {value}"
                    )
                    combinations.append(
                        {
                            "id": f"HO-PRODUCT-{len(combinations) + 1:03d}",
                            "testName": f"Coverage Package {value}",
                            "values": {"PolicyCoverageOption": value},
                            "result": diff_snapshots(product_baseline, changed),
                            "screen": changed,
                        }
                    )
                except Exception as exc:
                    technical_failures.append(
                        {
                            "combination": f"PolicyCoverageOption={value}",
                            "error": str(exc),
                        }
                    )

            coverage.set_coverage(data)
            coverage.set_replacement(data)
            coverage.set_perils(data)
            coverage.set_windstorm(data)
            coverage.set_liability(data)
            coverage.set_medical(data)
            coverage.set_year_built(data)
            coverage.set_construction(data)
            coverage.set_roof_type(data)
            coverage_baseline = snapshot_screen(
                page, "Location Coverage - baseline"
            )
            screens.append(coverage_baseline)

            coverage_conditions = (
                (
                    "Renovation",
                    "Is the residence under construction or major renovation?",
                ),
                (
                    "LivedHere",
                    "Has the customer lived at this location for less than 3 years?",
                ),
                ("Loses", "Any losses in the last three years?"),
            )
            for key, group in coverage_conditions:
                try:
                    attempts = 2 if key == "LivedHere" else 1
                    for attempt in range(1, attempts + 1):
                        changed = answer_and_snapshot(
                            coverage,
                            group,
                            "Yes",
                            f"Location Coverage - {key} Yes #{attempt}",
                        )
                        combinations.append(
                            {
                                "id": f"HO-COVERAGE-{len(combinations) + 1:03d}",
                                "testName": f"{key} Yes #{attempt}",
                                "values": {key: "Yes"},
                                "result": diff_snapshots(
                                    coverage_baseline, changed
                                ),
                                "screen": changed,
                            }
                        )
                        answer_and_snapshot(
                            coverage, group, "No", f"{key} reset #{attempt}"
                        )
                except Exception as exc:
                    technical_failures.append(
                        {"combination": f"{key}=Yes", "error": str(exc)}
                    )

            for pool_name in ("Swimming Pool", "Pool"):
                try:
                    group = page.get_by_role(
                        "radiogroup", name=re.compile(pool_name, re.I)
                    )
                    if group.count() == 0 or not group.first.is_visible():
                        continue
                    changed = answer_and_snapshot(
                        coverage, pool_name, "Yes", "Location Coverage - Pool Yes"
                    )
                    combinations.append(
                        {
                            "id": f"HO-COVERAGE-{len(combinations) + 1:03d}",
                            "testName": "Pool Yes",
                            "values": {"Pool": "Yes"},
                            "result": diff_snapshots(coverage_baseline, changed),
                            "screen": changed,
                        }
                    )
                    answer_and_snapshot(coverage, pool_name, "No", "Pool reset")
                    break
                except Exception as exc:
                    technical_failures.append(
                        {"combination": "Pool=Yes", "error": str(exc)}
                    )

            coverage.set_under_construction(data)
            coverage.set_lived_here(data)
            coverage.set_loses(data)
            coverage.click_save()

            for section in (
                "Additional Interests_1",
                "Optional Coverages",
                "Reinsurance",
                "Inspection",
                "Commission",
                "Manuscripts",
            ):
                try:
                    link = page.get_by_role("link", name=section, exact=True)
                    coverage.smart_click(link)
                    coverage.wait_for_app_ready()
                    screens.append(snapshot_screen(page, section))
                except Exception as exc:
                    technical_failures.append(
                        {"combination": f"TreeSection={section}", "error": str(exc)}
                    )

            generated_at = datetime.now().astimezone().isoformat(
                timespec="seconds"
            )
            result = {
                "schemaVersion": 1,
                "lob": "homeowner",
                "generatedAt": generated_at,
                "sourceScenario": "tools/probe_homeowner_elements.py",
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
            latest_path.write_text(
                json.dumps(result, indent=2), encoding="utf-8"
            )
            (history_dir / f"{timestamp}.json").write_text(
                json.dumps(result, indent=2), encoding="utf-8"
            )
            baseline_path = OUTPUT_DIR / "baseline.json"
            if not baseline_path.exists():
                baseline_path.write_text(
                    json.dumps(result, indent=2), encoding="utf-8"
                )

            print(f"Homeowner discovery inventory written to {latest_path}")
            print(f"Combinations captured: {len(combinations)}")
            print(f"Technical failures: {len(technical_failures)}")
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    main()
