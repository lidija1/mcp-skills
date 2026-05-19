import json
import os
import sys
from copy import deepcopy
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


OUTPUT = ROOT / "reports" / "homeowner_dropdown_options.json"


def load_case(tc_id="TC_ID_0001"):
    data_path = ROOT / "testdata" / "static" / "homeowner" / "HomeData.json"
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    for case in payload["testCases"]:
        if case.get("TC_ID") == tc_id:
            data = deepcopy(case)
            data["Email"] = "dropdown_probe_{timestamp}@home.com"
            data["FirstName"] = "Drop"
            data["LastName"] = "Probe"
            data["Address"] = "290 Old Taunton Ave"
            return data
    raise ValueError(f"Test case not found: {tc_id}")


def visible_boundlist_items(page):
    return page.evaluate(
        """() => [...document.querySelectorAll('.x-boundlist-item')]
            .filter(el => {
                const r = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return r.width > 0 && r.height > 0 && style.visibility !== 'hidden';
            })
            .map(el => el.textContent.trim())
            .filter(Boolean)"""
    )


def collect_options(page, name, locator):
    try:
        locator.scroll_into_view_if_needed()
        locator.click()
        page.wait_for_function(
            "() => [...document.querySelectorAll('.x-boundlist-item')]"
            ".some(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; })",
            timeout=5000,
        )
        options = visible_boundlist_items(page)
        page.keyboard.press("Escape")
        return {"name": name, "options": sorted(set(options), key=options.index)}
    except Exception as exc:
        page.keyboard.press("Escape")
        return {"name": name, "options": [], "error": str(exc)}


def main():
    load_dotenv(ROOT / ".env", override=True)
    data = load_case()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport=None)
        page = context.new_page()

        login = LoginPage(page)
        login.navigate()
        login.click_splash_button()
        login.fill_credentials_from_env()
        login.click_login()

        NewQuotePage(page).new_quote_steps()
        CustomerPage(page).customer_steps(data)
        QuoteRegistrationPage(page).quote_registration_steps(data)

        quote = HomeOwnerQuoteSummaryPage(page)
        results = {
            "source_case": data["TC_ID"],
            "quote_summary": [],
            "location_coverage": [],
        }

        for name, locator in (
            ("ProgramType", quote.program),
            ("BillingMethod", quote.billing),
            ("Term", quote.term),
            ("Prefix", quote.prefix),
            ("Suffix", quote.suffix),
        ):
            results["quote_summary"].append(collect_options(page, name, locator))

        quote.summary_steps(data)
        city = HomeownerCityInformationPage(page)
        city.click_save()
        city.click_homeowners_link(data)

        coverage = HomeownerCoveragePage(page)
        for name, locator in (
            ("ResidenceType", coverage.residence_type),
            ("PolicyCoverageOption", coverage.policy_coverage),
            ("AllPerilsDeductable", coverage.perils),
            ("WindstormDeductable", coverage.windstorm),
            ("Liability", coverage.liability),
            ("MedPayments", coverage.medical),
            ("ConstructionType", coverage.construction),
            ("ProtectionClass", coverage.protection_class),
            ("BCEG", coverage.bceg),
            ("RoofType", coverage.roof_type),
            ("RoofShape", coverage.roof_shape),
            ("SecondaryWaterResistance", coverage.secondary_water_resistance),
            ("OpeningProtection", coverage.opening_protection),
            ("RoofWallConnection", coverage.roof_wall_connection),
            ("RoofDeck", coverage.roof_deck),
            ("RoofDeckAttachment", coverage.roof_deck_attachment),
            ("DistanceToShore", coverage.distance_to_shore),
            ("PerimeterSecurityProtection", coverage.perimeter_security_protection),
        ):
            results["location_coverage"].append(collect_options(page, name, locator))

        if any(item["name"] == "RoofType" and not item["options"] for item in results["location_coverage"]):
            coverage.set_residency(data)
            coverage.set_coverage(data)
            coverage.wait_for_loader_to_disappear()
            coverage.set_replacement(data)
            coverage.set_perils(data)
            coverage.set_windstorm(data)
            coverage.set_liability(data)
            coverage.set_medical(data)
            coverage.set_year_built(data)
            coverage.set_construction(data)
            results["location_coverage"].append(
                collect_options(page, "RoofTypeAfterRequiredFields", coverage.roof_type)
            )

        OUTPUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(json.dumps(results, indent=2))

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
