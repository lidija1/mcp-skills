"""Auto insurance quote and policy workflow step definitions."""
import allure
from pytest_bdd import when, given, then, parsers


@when("i create a new quote")
def create_new_quote(new_quote_page, log, api_flow_recorder):
    """Initiate a new quote creation process."""
    log.info("Starting new quote creation...")
    api_flow_recorder.mark_page("auto_new_quote")
    new_quote_page.new_quote_steps()
    log.info("Successfully created new quote.")


@when("i create a new customer")
def create_new_customer(customer_page, test_data, log, api_flow_recorder):
    """Create a new customer with provided data."""
    log.info("Starting customer creation...")
    api_flow_recorder.mark_page("auto_customer")
    customer_page.customer_steps(test_data)
    log.info("Successfully created new customer.")


@when("I provide quote registration details")
def provide_quote_registration(quote_registration_page, test_data, log, api_flow_recorder):
    """Fill quote registration details."""
    log.info("Filling quote registration details...")
    api_flow_recorder.mark_page("auto_quote_registration")
    quote_registration_page.quote_registration_steps(test_data)
    log.info("Successfully filled quote registration details.")


@when("I provide quote summary PA info")
def provide_quote_summary(quote_summary_page, test_data, log, api_flow_recorder):
    """Fill quote summary information."""
    log.info("Filling quote summary information...")
    api_flow_recorder.mark_page("auto_quote_summary")
    quote_summary_page.summary_steps(test_data)
    log.info("Successfully filled quote summary information.")


@when("I provide Driver Details")
def provide_driver_details(driver_info_page, test_data, log, api_flow_recorder):
    """Fill driver information."""
    log.info("Filling driver details...")
    api_flow_recorder.mark_page("auto_driver")
    driver_info_page.fill_driver_info(test_data)
    log.info("Successfully filled driver details.")


@when("I provide Vehicle Details")
def provide_vehicle_details(vehicle_info_page, test_data, log, api_flow_recorder):
    """Fill vehicle information."""
    log.info("Filling vehicle details...")
    api_flow_recorder.mark_page("auto_vehicle")
    vehicle_info_page.fill_vehicle_info(test_data)
    log.info("Successfully filled vehicle details.")


@given("I provide policy term details")
def provide_policy_term_details(policy_term_page, test_data, log, api_flow_recorder):
    """Fill policy term and coverage details."""
    log.info("Filling policy term details...")
    api_flow_recorder.mark_page("auto_coverages_rating")
    policy_term_page.policy_term_steps(test_data)
    log.info("Successfully filled policy term details.")


@when("I create a policy from the quote")
def create_policy_from_quote(create_policy_page, log, api_flow_recorder):
    """Create and bind a policy from the quote."""
    log.info("Creating policy from quote...")
    api_flow_recorder.mark_page("auto_premium_summary")
    create_policy_page.click_issue()
    create_policy_page.wait_for_loader_to_disappear()
    api_flow_recorder.mark_page("auto_delivery_preferences")
    create_policy_page.click_next()
    create_policy_page.wait_for_loader_to_disappear()
    api_flow_recorder.mark_page("auto_billing_plan")
    create_policy_page.click_next()
    create_policy_page.wait_for_loader_to_disappear()
    api_flow_recorder.mark_page("auto_verify_billing")
    create_policy_page.click_bind()
    create_policy_page.wait_for_loader_to_disappear()
    log.info("Successfully created and bound policy.")


@when("I complete quote summary and save")
def complete_quote_summary_and_save(quote_summary_page, test_data, log):
    """
    Fill quote summary fields (billing, FalseInfo, DamageInfo) and save.

    Used in UW hard-stop scenarios where saving the quote summary immediately
    redirects to the UW referral page before driver/vehicle data is entered.
    Unlike 'I provide quote summary PA info', this step does NOT attempt to
    navigate to the driver info tree link afterward.
    """
    log.info("Completing quote summary (UW hard-stop path) — saving without driver navigation...")
    quote_summary_page.summary_steps_save_only(test_data)
    log.info("Quote summary saved — expecting UW referral page.")


@when("I select coverage and rate the quote")
def select_coverage_and_rate(page, policy_term_page, test_data, log):
    """
    Select the policy coverage tier and click Rate Quote, then expect UW referral.

    Handles three trigger points where UW can fire during the rating workflow:
      1. UW already visible before coverage — some profiles redirect to the UW
         referral page immediately after vehicle info (e.g. Leased + SR-22).
      2. UW fires when landing on the coverage page — Rate Quote button is absent
         because the page already shows a UW condition (e.g. driver age).
      3. UW fires on Rate Quote click — the standard soft-referral flow.

    In cases 1 and 2 the step exits early; the following Then assertion step
    validates the UW condition on whichever page is currently active.
    """
    uw_indicator = page.locator("text=underwriting referral")

    # Case 1 — UW page already shown before we even attempt coverage selection
    if uw_indicator.is_visible(timeout=2000):
        log.info("UW referral page already visible before coverage step — skipping rate.")
        return

    try:
        log.info("Selecting coverage and rating quote...")
        policy_term_page.policy_term_steps(test_data)
        log.info("Quote rated — expecting UW referral page.")
    except Exception as exc:
        # Case 2 — UW fired on the coverage page (e.g. Rate Quote button absent
        # because UW hard-stop or referral was shown at page load time)
        if uw_indicator.is_visible(timeout=5000):
            log.info("UW referral page appeared during coverage step — proceeding to assertion.")
            return
        raise exc


@then(parsers.parse('the UW referral page shows a "{uw_type}" condition containing "{expected_condition}"'))
def assert_uw_referral_condition(uw_referral_page, uw_type, expected_condition, log):
    """
    Assert that the UW referral page is visible and contains a row in the
    underwriting issues grid matching the expected type and condition keyword.

    Args:
        uw_type: 'Hard-Stop' or 'Underwriting' — must match the Type column exactly.
        expected_condition: Substring to search for inside the Condition column.
    """
    expected_conditions = [
        condition.strip()
        for condition in expected_condition.split(";")
        if condition.strip()
    ]
    log.info(f"Asserting UW condition(s) | type='{uw_type}' | contains={expected_conditions}")
    for condition in expected_conditions:
        with allure.step(f"Verify UW rule: [{uw_type}] - '{condition}'"):
            uw_referral_page.assert_uw_condition(uw_type, condition)
    log.info("UW condition assertion passed.")


@when("I override all UW conditions and accept")
def override_all_uw_conditions(uw_referral_page, log):
    """Override editable UW conditions and accept the referral."""
    log.info("Checking whether all UW conditions are editable...")
    assert uw_referral_page.can_be_overridden(), (
        "UW referral cannot be fully overridden by the current user."
    )
    log.info("Overriding all UW conditions and accepting...")
    uw_referral_page.override_all_and_accept()
    log.info("UW conditions overridden and accepted.")


@when("I complete Contact Information with Email permission")
def complete_contact_information_with_email(contact_information_page, log):
    """Complete the post-UW Contact Information page."""
    log.info("Completing Contact Information with Email permission...")
    assert contact_information_page.complete_email_permission_if_visible(), (
        "Contact Information page was not visible after UW accept."
    )
    log.info("Contact Information completed with Email permission.")


@when("I re-rate the quote after UW override")
def rerate_quote_after_uw_override(create_policy_page, log):
    """Re-rate the quote after UW override/contact information."""
    log.info("Re-rating quote after UW override...")
    assert create_policy_page.click_re_rate_if_visible(), (
        "Re-rate button was not visible after Contact Information."
    )
    log.info("Quote re-rated after UW override.")


@then("I read and extract policy summary page details")
def read_extract_summary(policy_summary_page, test_data, log, api_flow_recorder):
    """Extract details from the policy summary page."""
    log.info("Extracting policy summary details...")
    api_flow_recorder.mark_page("auto_policy_summary")

    details = policy_summary_page.extract_details(test_data)
    path = policy_summary_page.save_lob_report(details)
    log.info("Data is saved to CSV file at: " + path)
    
    log.info("-" * 40)
    log.info("POLICY SUMMARY DETAILS:")
    for key, value in details.items():
        log.info(f"{key}: {value}")
    log.info("-" * 40)
    
    # Also print to stdout so it's visible in console output during -s run
    print("\n" + "=" * 50)
    print("POLICY SUMMARY REPORT")
    print("=" * 50)
    for key, value in details.items():
        print(f"{key:20}: {value}")
    print("=" * 50 + "\n")
