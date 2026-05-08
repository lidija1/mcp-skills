import json
from pathlib import Path

from pytest_bdd import scenario

from utils.json_reader import DataLoader


@scenario(
    "../features/general_liability/general_liability_creation.feature",
    "Exercise the General Liability creation flow",
)
def test_general_liability_creation():
    pass


def test_general_liability_dropdown_inventory(
    login_page,
    new_quote_page,
    customer_page,
    quote_registration_page,
    general_liability_risk_address_page,
    general_liability_basic_policy_information_page,
    general_liability_coverage_and_limits_page,
    general_liability_liability_location_list_page,
    general_liability_rating_basis_and_classification_page,
    billing_plan_page,
):
    """Capture live dropdown values for General Liability pages."""
    data_path = Path("testdata/static/general_liability/GeneralLiabilityData.json")
    payload = DataLoader.get_data(str(data_path))
    test_data = next(
        row for row in payload.get("testCases", [])
        if str(row.get("TC_ID", "")).strip() == "TC_ID_0001"
    )

    login_page.navigate()
    login_page.click_splash_button()
    login_page.fill_credentials_from_env()
    login_page.click_login()

    new_quote_page.new_quote_steps()
    customer_page.customer_steps(test_data)
    quote_registration_page.quote_registration_steps(test_data)

    general_liability_risk_address_page.risk_address_steps(test_data)

    general_liability_basic_policy_information_page.basic_policy_information_steps(test_data)
    basic_options = general_liability_basic_policy_information_page.inventory_dropdown_options()

    general_liability_coverage_and_limits_page.coverage_and_limits_steps(test_data)
    coverage_options = general_liability_coverage_and_limits_page.inventory_dropdown_options()

    general_liability_liability_location_list_page.liability_location_list_steps(test_data)

    general_liability_rating_basis_and_classification_page.rating_basis_and_classification_steps(test_data)
    rating_options = general_liability_rating_basis_and_classification_page.inventory_dropdown_options(test_data)

    billing_options = {
        "PayerCurrency": [test_data.get("PayerCurrency")],
        "PaymentPlan": [test_data.get("PaymentPlan")],
    }

    output = Path("reports") / "general_liability_dropdown_inventory.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "TC_ID": test_data.get("TC_ID"),
                "basic_policy_information": basic_options,
                "coverage_and_limits": coverage_options,
                "rating_basis_and_classification": rating_options,
                "billing_plan": billing_options,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
