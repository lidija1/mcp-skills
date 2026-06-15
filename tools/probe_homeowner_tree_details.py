"""Discover Homeowner detail fields behind unmapped left-tree Add actions.

Creates one quote, completes required Homeowner data, inventories detail forms
for Additional Interests, Reinsurance, Inspection, and Manuscripts, and stops
without rating, requesting issue, or binding.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.probe_homeowner_elements import load_case, snapshot_screen
from ui.pages.common.customer_page import CustomerPage
from ui.pages.common.login_page import LoginPage
from ui.pages.common.new_quote_page import NewQuotePage
from ui.pages.common.quote_registration_page import QuoteRegistrationPage
from ui.pages.homeowner.homeowner_city_information_page import HomeownerCityInformationPage
from ui.pages.homeowner.homeowner_coverage_page import HomeownerCoveragePage
from ui.pages.homeowner.homeowner_quote_summary_page import HomeOwnerQuoteSummaryPage


OUTPUT = (
    ROOT
    / "reports"
    / "lob-discovery"
    / "homeowner"
    / "tree-details.json"
)


def navigate_to_section(page_object, name):
    locator = page_object.page.get_by_role("link", name=name, exact=True)
    page_object.smart_click(locator)
    page_object.wait_for_app_ready()


def add_and_snapshot(page_object, section, screen_name, add_name="Add"):
    navigate_to_section(page_object, section)
    add_button = page_object.page.get_by_role(
        "button", name=add_name, exact=True
    ).first
    page_object.smart_click(add_button)
    page_object.wait_for_app_ready()
    return snapshot_screen(page_object.page, screen_name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--slow-mo", type=int, default=25)
    args = parser.parse_args()

    load_dotenv(ROOT / ".env", override=True)
    data = load_case()
    data["FirstName"] = "Harper"
    data["LastName"] = f"TreeDiscovery{datetime.now():%H%M%S}"
    data["Email"] = "homeowner_tree_{timestamp}@example.com"

    screens = []
    failures = []
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
            quote.summary_steps(data)
            city = HomeownerCityInformationPage(page)
            city.click_save()
            city.click_homeowners_link(data)

            coverage = HomeownerCoveragePage(page)
            coverage.coverage_steps(data)

            probes = (
                ("Additional Interests_1", "Additional Interest - Add", "Add"),
                ("Reinsurance", "Reinsurance - Add", "Add"),
                ("Inspection", "Inspection - Add", "Add"),
                ("Manuscripts", "Manuscripts - Add", "Add"),
            )
            for section, screen_name, add_name in probes:
                try:
                    screens.append(
                        add_and_snapshot(
                            coverage, section, screen_name, add_name
                        )
                    )
                except Exception as exc:
                    failures.append(
                        {"section": section, "error": str(exc)}
                    )
                    location = page.get_by_role(
                        "link",
                        name=re.compile(
                            r"homeowners\s*\|\s*location coverage", re.I
                        ),
                    )
                    if location.count() and location.first.is_visible():
                        coverage.smart_click(location.first)
                        coverage.wait_for_app_ready()

            result = {
                "schemaVersion": 1,
                "lob": "homeowner",
                "generatedAt": datetime.now().astimezone().isoformat(
                    timespec="seconds"
                ),
                "sourceScenario": "tools/probe_homeowner_tree_details.py",
                "quotesCreated": 1,
                "rated": False,
                "requestedIssue": False,
                "boundPolicies": 0,
                "screens": screens,
                "technicalFailures": failures,
            }
            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(f"Homeowner tree detail inventory written to {OUTPUT}")
            print(f"Detail screens captured: {len(screens)}")
            print(f"Technical failures: {len(failures)}")
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    main()
