import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.pages.auto.create_policy_page import CreatePolicyPage
from ui.pages.common.customer_page import CustomerPage
from ui.pages.common.login_page import LoginPage
from ui.pages.common.new_quote_page import NewQuotePage
from ui.pages.common.policy_summary_page import PolicySummary
from ui.pages.common.quote_registration_page import QuoteRegistrationPage
from ui.pages.homeowner.homeowner_bind_information_page import HomeownerBindInformationPage
from ui.pages.homeowner.homeowner_city_information_page import HomeownerCityInformationPage
from ui.pages.homeowner.homeowner_coverage_page import HomeownerCoveragePage
from ui.pages.homeowner.homeowner_quote_summary_page import HomeOwnerQuoteSummaryPage


DATA = ROOT / "testdata" / "static" / "homeowner" / "HomeownerDropdownOptionsData.json"


def load_case(tc_id):
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    for case in payload["testCases"]:
        if case["TC_ID"] == tc_id:
            return case
    raise ValueError(f"Test case not found: {tc_id}")


def run_case(tc_id):
    load_dotenv(ROOT / "..env", override=True)
    data = load_case(tc_id)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport=None)
        page = context.new_page()
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

            CreatePolicyPage(page).policy_creation_steps()
            details = PolicySummary(page).extract_details(data)
            print(json.dumps({"tc_id": tc_id, "details": details}, indent=2))
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    case_id = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TC_ID", "TC_HO_DD_0001")
    run_case(case_id)
