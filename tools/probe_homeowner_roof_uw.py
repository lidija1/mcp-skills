import argparse
import json
import os
import sys
import time
from copy import deepcopy
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.pages.common.customer_page import CustomerPage
from ui.pages.common.login_page import LoginPage
from ui.pages.common.new_quote_page import NewQuotePage
from ui.pages.common.quote_registration_page import QuoteRegistrationPage
from ui.pages.homeowner.homeowner_bind_information_page import HomeownerBindInformationPage
from ui.pages.homeowner.homeowner_city_information_page import HomeownerCityInformationPage
from ui.pages.homeowner.homeowner_coverage_page import HomeownerCoveragePage
from ui.pages.homeowner.homeowner_quote_summary_page import HomeOwnerQuoteSummaryPage

HOME_DATA = ROOT / "testdata" / "static" / "homeowner" / "HomeData.json"
DROPDOWN_OPTIONS = ROOT / "reports" / "homeowner_dropdown_options.json"
OUTPUT = ROOT / "reports" / "homeowner_roof_uw_results.json"

DEFAULT_ROOF_TYPES = [
    "Aluminum Shingles",
    "Asbestos Shakes",
    "Asphalt",
    "Cedar Shakes",
    "Cedar Shingles",
    "Clay Tile",
    "Composition",
    "Composition (Fiberglass, Asphalt, etc.)",
    "Concrete Tile",
    "Copper",
    "Fiberglass",
    "Flat",
    "Metal",
    "Other",
    "Plastic",
    "Poured",
    "Recycled Roofing Products",
    "Rock",
    "Roll Roofing",
    "Rolled Paper",
    "Single Ply Membrane Systems",
    "Slate",
    "Steel on Steel Joist",
    "Steel/Porcelain Shingles",
    "Tar & Gravel (Built-Up)",
    "Tile",
    "Tin",
    "WD Shingles",
    "Wood Shake/Shingle",
]


def load_base_case():
    payload = json.loads(HOME_DATA.read_text(encoding="utf-8"))
    for case in payload["testCases"]:
        if case.get("TC_ID") == "TC_ID_0001":
            data = deepcopy(case)
            break
    else:
        raise ValueError("TC_ID_0001 not found in HomeData.json")

    data["PaymentPlan"] = "Pay In Full"
    data["PolicyCoverageOption"] = "Gold"
    data["ResidenceType"] = "Homeowner"
    data["ReplacementCost"] = "300,000"
    data["AllPerilsDeductable"] = "5,000"
    data["WindstormDeductable"] = "5%"
    data["Liability"] = "100,000"
    data["MedPayments"] = "2,000"
    data["YearBuilt"] = "2010"
    data["ConstructionType"] = "Frame"
    data["Renovation"] = "No"
    data["LivedHere"] = "No"
    data["Loses"] = "No"
    data["ExistingClient"] = "No"
    data["Refused"] = "No"
    data["Declined"] = "No"
    data.pop("Pool", None)
    return data


def roof_types_from_options():
    if not DROPDOWN_OPTIONS.exists():
        return DEFAULT_ROOF_TYPES

    payload = json.loads(DROPDOWN_OPTIONS.read_text(encoding="utf-8"))
    for item in payload.get("location_coverage", []):
        if item.get("name") == "RoofType":
            return [
                option for option in item.get("options", [])
                if option not in {"- Select -", "-Select-"}
            ]
    return DEFAULT_ROOF_TYPES


def build_case(roof_type, index):
    data = load_base_case()
    data["TC_ID"] = f"ROOF_UW_{index:03d}"
    data["FirstName"] = f"Roof{index:03d}"
    data["LastName"] = "Probe"
    data["Email"] = f"roof_uw_{index:03d}_{{timestamp}}@home.com"
    data["Address"] = f"{500 + index} Old Taunton Ave"
    data["RoofType"] = roof_type
    return data


def visible_gridcells(page):
    cells = page.get_by_role("gridcell").all()
    return [cell.inner_text().strip() for cell in cells if cell.inner_text().strip()]


def detect_result(page):
    uw_indicator = page.locator("text=underwriting referral").or_(
        page.locator("text=Underwriting Issues")
    )
    premium_summary = page.locator("text=premium | summary")

    try:
        uw_indicator.first.wait_for(state="visible", timeout=5_000)
        return {
            "outcome": "uw",
            "conditions": visible_gridcells(page),
        }
    except PlaywrightTimeoutError:
        pass

    try:
        premium_summary.first.wait_for(state="visible", timeout=5_000)
        return {
            "outcome": "clean",
            "conditions": [],
        }
    except PlaywrightTimeoutError:
        return {
            "outcome": "unknown",
            "conditions": visible_gridcells(page),
        }


def run_roof_case(playwright, roof_type, index, headed):
    data = build_case(roof_type, index)
    browser = playwright.chromium.launch(headless=not headed)
    context = browser.new_context(viewport=None)
    page = context.new_page()
    started_at = time.time()

    try:
        login = LoginPage(page)
        login.navigate()
        login.click_splash_button()
        login.fill_credentials_from_env()
        login.click_login()

        NewQuotePage(page).new_quote_steps()
        CustomerPage(page).customer_steps(data)
        QuoteRegistrationPage(page).quote_registration_steps(data)

        quote = HomeOwnerQuoteSummaryPage(page)
        city = HomeownerCityInformationPage(page)
        quote.summary_steps(data)
        city.click_save()
        city.click_homeowners_link(data)

        coverage = HomeownerCoveragePage(page)
        bind = HomeownerBindInformationPage(page)
        coverage.coverage_steps(data)
        bind.set_existing_client(data)
        bind.set_refused_in_the_past(data)
        bind.set_denied_coverage(data)
        bind.click_save()
        bind.click_rate_quote()

        result = detect_result(page)
        result.update({
            "roof_type": roof_type,
            "tc_id": data["TC_ID"],
            "duration_seconds": round(time.time() - started_at, 2),
            "url": page.url,
        })
        return result
    except Exception as exc:
        result = detect_result(page)
        result.update({
            "roof_type": roof_type,
            "tc_id": data["TC_ID"],
            "outcome": result["outcome"] if result["outcome"] != "unknown" else "error",
            "error": str(exc),
            "duration_seconds": round(time.time() - started_at, 2),
            "url": page.url,
        })
        return result
    finally:
        context.close()
        browser.close()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Probe which Homeowner Roof Type options trigger UW at rating."
    )
    parser.add_argument(
        "--roof-type",
        action="append",
        help="Roof type to test. Repeat for multiple values. Defaults to all discovered options.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit the number of roof types tested.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium headless. Default is headed for OneShield exploration.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    load_dotenv(ROOT / "..env", override=True)

    roof_types = args.roof_type if args.roof_type else roof_types_from_options()
    if args.limit:
        roof_types = roof_types[:args.limit]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    results = []

    with sync_playwright() as playwright:
        for index, roof_type in enumerate(roof_types, start=1):
            print(f"[{index}/{len(roof_types)}] Testing RoofType={roof_type}")
            result = run_roof_case(playwright, roof_type, index, headed=not args.headless)
            results.append(result)
            OUTPUT.write_text(json.dumps({
                "roof_types_tested": len(results),
                "results": results,
            }, indent=2), encoding="utf-8")
            print(json.dumps(result, indent=2))

    print(f"Wrote results to {OUTPUT}")


if __name__ == "__main__":
    main()
