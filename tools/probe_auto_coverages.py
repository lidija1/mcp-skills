"""Probe Personal Auto coverage controls and package-dependent values.

Creates one quote, reaches Coverages, inventories every visible control and
combobox option for Bronze, Silver, Gold, and Platinum, and stops before rate.
"""

import argparse
import json
import os
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.probe_auto_elements import snapshot_screen
from ui.pages.auto.driver_info_page import DriverInfoPage
from ui.pages.auto.quote_summary_page import QuoteSummaryPage
from ui.pages.auto.vehicle_info_page import VehicleInfoPage
from ui.pages.common.customer_page import CustomerPage
from ui.pages.common.login_page import LoginPage
from ui.pages.common.new_quote_page import NewQuotePage
from ui.pages.common.quote_registration_page import QuoteRegistrationPage


OUTPUT_DIR = ROOT / "reports" / "lob-discovery" / "auto"


def load_case():
    payload = json.loads(
        (ROOT / "testdata" / "static" / "auto" / "AutoData.json").read_text(
            encoding="utf-8"
        )
    )
    data = deepcopy(payload["testCases"][0])
    suffix = datetime.now().strftime("%H%M%S")
    data.update(
        {
            "TC_ID": "TC_ID_AUTO_COVERAGE_DISCOVERY_0001",
            "FirstName": "Casey",
            "LastName": f"Coverage{suffix}",
            "Email": f"auto_coverage_{suffix}_{{timestamp}}@example.com",
        }
    )
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--slow-mo", type=int, default=50)
    args = parser.parse_args()

    load_dotenv(ROOT / ".env", override=True)
    data = load_case()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
        QuoteSummaryPage(page).summary_steps(data)
        DriverInfoPage(page).fill_driver_info(data)

        vehicle = VehicleInfoPage(page)
        vehicle.fill_vehicle_info(data)

        coverage = page.get_by_role(
            "combobox", name="Policy Coverage Option*", exact=True
        )
        coverage.wait_for(state="visible", timeout=30_000)

        packages = {}
        for package in ("Bronze", "Silver", "Gold", "Platinum"):
            vehicle.select_extjs_option(
                coverage,
                package,
                wait_for_response=True,
                url_parts=["FieldProcessorServlet"],
            )
            vehicle.wait_for_app_ready()
            packages[package] = snapshot_screen(
                page, f"Coverages - {package}"
            )

        result = {
            "schemaVersion": 1,
            "lob": "auto",
            "generatedAt": datetime.now().astimezone().isoformat(
                timespec="seconds"
            ),
            "sourceScenario": "tools/probe_auto_coverages.py",
            "quotesCreated": 1,
            "rated": False,
            "requestedIssue": False,
            "boundPolicies": 0,
            "packages": packages,
        }
        output = OUTPUT_DIR / "coverage_probe.json"
        output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Auto coverage inventory written to {output}")

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
