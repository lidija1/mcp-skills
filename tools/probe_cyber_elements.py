import argparse
import json
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
from ui.pages.cyber.cyber_policy_information_page import CyberPolicyInformationPage


OUTPUT_DIR = ROOT / "reports" / "lob-discovery" / "cyber"


def load_case(tc_id):
    data_path = ROOT / "testdata" / "static" / "cyber" / "CyberData.json"
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    for case in payload["testCases"]:
        if case.get("TC_ID") == tc_id:
            data = deepcopy(case)
            timestamp = datetime.now().strftime("%H%M%S")
            data["Email"] = f"cyber_discovery_{timestamp}_{{timestamp}}@cyber.com"
            data["FirstName"] = "Cyber"
            data["LastName"] = f"Probe{timestamp}"
            return data
    raise ValueError(f"Test case not found: {tc_id}")


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
            const normalize = value => (value || '').replace(/\\s+/g, ' ').trim();
            return [...document.querySelectorAll(
                'input, textarea, select, button, [role="combobox"], '
                + '[role="checkbox"], [role="radio"], [role="button"], a'
            )]
                .filter(visible)
                .map(el => {
                    const id = el.id || '';
                    const explicitLabel = id
                        ? document.querySelector(`label[for="${CSS.escape(id)}"]`)
                        : null;
                    const container = el.closest(
                        '.x-field, .x-form-item, li, td, div[class*="field"]'
                    );
                    const nearbyLabel = container
                        ? container.querySelector(
                            'label, .x-form-item-label, .x-form-cb-label'
                        )
                        : null;
                    return {
                        tag: el.tagName.toLowerCase(),
                        type: el.getAttribute('type'),
                        role: el.getAttribute('role'),
                        label: normalize(
                            el.getAttribute('aria-label')
                            || (explicitLabel && explicitLabel.textContent)
                            || (nearbyLabel && nearbyLabel.textContent)
                        ),
                        text: normalize(el.textContent),
                        value: 'value' in el ? normalize(el.value) : '',
                        required: el.required
                            || el.getAttribute('aria-required') === 'true',
                        disabled: el.disabled
                            || el.getAttribute('aria-disabled') === 'true',
                        osviewid: el.getAttribute('osviewid'),
                        name: el.getAttribute('name'),
                    };
                })
                .filter(item => item.label || item.text || item.value);
        }"""
    )


def collect_options(page_object, fields):
    results = {}
    for key, locator in fields.items():
        try:
            locator.scroll_into_view_if_needed()
            locator.click()
            page_object.page.wait_for_function(
                """() => [...document.querySelectorAll('.x-boundlist')]
                    .some(list => {
                        const rect = list.getBoundingClientRect();
                        const style = window.getComputedStyle(list);
                        return rect.width > 0 && rect.height > 0
                            && style.display !== 'none'
                            && style.visibility !== 'hidden';
                    })""",
                timeout=5000,
            )
            results[key] = page_object.page.evaluate(
                """() => {
                    const lists = [...document.querySelectorAll('.x-boundlist')]
                        .filter(list => {
                            const rect = list.getBoundingClientRect();
                            const style = window.getComputedStyle(list);
                            return rect.width > 0 && rect.height > 0
                                && style.display !== 'none'
                                && style.visibility !== 'hidden';
                        });
                    const active = lists[lists.length - 1];
                    return [...active.querySelectorAll('.x-boundlist-item')]
                        .filter(item => {
                            const rect = item.getBoundingClientRect();
                            return rect.width > 0 && rect.height > 0;
                        })
                        .map(item => (item.textContent || '').replace(/\\s+/g, ' ').trim())
                        .filter(Boolean);
                }"""
            )
            page_object.page.keyboard.press("Escape")
        except Exception as exc:
            page_object.page.keyboard.press("Escape")
            results[key] = {"error": str(exc)}
    return results


def select_and_capture(page_object, key, locator, value):
    page_object.select_extjs_option(
        locator,
        value,
        wait_for_response=True,
        url_parts=("FieldProcessorServlet",),
    )
    page_object.wait_for_app_ready()
    return {
        "id": f"CYBER-{key.upper()}-{value.upper().replace(' ', '-')}",
        "field": key,
        "value": value,
        "controls": visible_controls(page_object.page),
    }


def click_tree_link(page_object, name):
    link = page_object.page.get_by_role("link", name=name, exact=True)
    page_object.with_optional_oneshield_response(
        lambda: page_object.smart_click(link)
    )
    page_object.wait_for_app_ready()


def inspect_tree_page(page_object, name):
    click_tree_link(page_object, name)
    page = page_object.page
    add_buttons = page.get_by_role("button", name="Add", exact=True)
    add_count = add_buttons.count()
    result = {
        "name": name,
        "beforeAdd": visible_controls(page),
        "addButtonCount": add_count,
        "addPaths": [],
    }

    for index in range(add_count):
        if index:
            click_tree_link(page_object, name)
            add_buttons = page.get_by_role("button", name="Add", exact=True)
        button = add_buttons.nth(index)
        button_metadata = button.evaluate(
            """el => ({
                text: (el.textContent || '').replace(/\\s+/g, ' ').trim(),
                osviewid: el.getAttribute('osviewid'),
                title: el.getAttribute('title'),
                ariaLabel: el.getAttribute('aria-label'),
                parentText: (el.parentElement && el.parentElement.textContent || '')
                    .replace(/\\s+/g, ' ').trim()
            })"""
        )
        page_object.with_optional_oneshield_response(
            lambda button=button: page_object.smart_click(button)
        )
        page_object.wait_for_app_ready()
        if name == "Reinsurance":
            new_reinsurance = page.get_by_role(
                "link", name="New Reinsurance", exact=True
            )
            if new_reinsurance.is_visible():
                page_object.with_optional_oneshield_response(
                    lambda: page_object.smart_click(new_reinsurance)
                )
                page_object.wait_for_app_ready()
        after_add = visible_controls(page)
        option_fields = {}
        for control in after_add:
            if control["role"] != "combobox" or not control["label"]:
                continue
            osviewid = control.get("osviewid")
            if not osviewid:
                continue
            key = f'{control["label"]}|{osviewid}'
            option_fields[key] = page.locator(f'[osviewid="{osviewid}"]')
        result["addPaths"].append({
            "index": index,
            "button": button_metadata,
            "afterAdd": after_add,
            "dropdownOptions": collect_options(page_object, option_fields),
        })

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tc-id", default="TC_ID_0001")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--slow-mo", type=int, default=50)
    args = parser.parse_args()

    load_dotenv(ROOT / ".env", override=True)
    data = load_case(args.tc_id)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=not args.headed,
            slow_mo=args.slow_mo,
        )
        context = browser.new_context(viewport=None)
        page = context.new_page()

        login = LoginPage(page)
        login.navigate("https://inforcedev.oneshield.com/oneshield/")
        if page.locator(login.employee_portal).is_visible(timeout=3000):
            login.click_splash_button()
        login.wait_for_login_page()
        login.fill_credentials_from_env()
        login.click_login()

        NewQuotePage(page).new_quote_steps()
        CustomerPage(page).customer_steps(data)
        QuoteRegistrationPage(page).quote_registration_steps(data)

        cyber = CyberPolicyInformationPage(page)
        fields = {
            "BillingMethod": cyber.billing_method,
            "NatureOfBusiness": cyber.nature_of_business,
            "AggregateLimit": cyber.aggregate_limit,
            "PerClaimDeductible": cyber.per_claim_deductible,
            "PerClaimLimit": cyber.per_claim_limit,
            "CommonEligibility1": cyber.common_eligibility_1,
            "CommonEligibility2": cyber.common_eligibility_2,
            "CommonEligibility3": cyber.common_eligibility_3,
        }
        options = collect_options(cyber, fields)
        baseline_controls = visible_controls(page)

        combinations = []
        eligibility_fields = {
            "CommonEligibility1": cyber.common_eligibility_1,
            "CommonEligibility2": cyber.common_eligibility_2,
            "CommonEligibility3": cyber.common_eligibility_3,
        }
        for key, locator in eligibility_fields.items():
            values = options.get(key, [])
            if not isinstance(values, list):
                continue
            baseline_value = data[key]
            for value in values:
                if (
                    value == baseline_value
                    or value.lower().replace(" ", "") == "-select-"
                    or len(combinations) >= 30
                ):
                    continue
                combinations.append(
                    select_and_capture(cyber, key, locator, value)
                )
                select_and_capture(cyber, key, locator, baseline_value)

        treePages = {
            "Reinsurance": inspect_tree_page(cyber, "Reinsurance"),
            "Inspection": inspect_tree_page(cyber, "Inspection"),
        }

        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        result = {
            "schemaVersion": 1,
            "lob": "cyber",
            "generatedAt": timestamp,
            "sourceCase": args.tc_id,
            "limits": {
                "maxCombinations": 30,
                "maxBoundPolicies": 0,
            },
            "quotesCreated": 1,
            "rated": False,
            "requestedIssue": False,
            "boundPolicies": 0,
            "url": page.url,
            "baselineControls": baseline_controls,
            "dropdownOptions": options,
            "combinations": combinations,
            "treePages": treePages,
        }
        raw_path = OUTPUT_DIR / "probe_raw.json"
        raw_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
