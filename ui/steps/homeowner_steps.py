import allure
from pytest_bdd import when, then, parsers


@when("I provide quote summary HO info")
def homeowner_quote(homeowner_quote_summary_page, homeowner_city_information_page, test_data, log):
    """Fill quote summary information for homeowner insurance."""
    log.info("Filling homeowner quote summary information...")
    homeowner_quote_summary_page.summary_steps(test_data)
    homeowner_city_information_page.click_save()
    homeowner_city_information_page.click_homeowners_link(test_data)
    log.info("Successfully filled homeowner quote summary information.")


@when("I provide quote summary HO info for UW testing")
def homeowner_quote_uw(page, homeowner_quote_summary_page, homeowner_city_information_page, test_data, log):
    """Fill Quote Summary and handle a UW referral that may fire on save."""
    uw_indicator = page.locator("text=underwriting referral")
    try:
        log.info("Filling homeowner quote summary for UW testing...")
        homeowner_quote_summary_page.summary_steps(test_data)
        homeowner_city_information_page.click_save()
        homeowner_city_information_page.click_homeowners_link(test_data)
        log.info("Quote summary completed - proceeding to coverage.")
    except Exception:
        if uw_indicator.is_visible(timeout=5_000):
            log.info("UW referral detected on quote summary save - proceeding to assertion.")
            return
        raise


@when("I provide location coverage info")
def ho_coverage_info(homeowner_coverage_page, homeowner_bind_information_page, test_data, log):
    log.info("Filling homeowner location coverage information...")
    homeowner_coverage_page.coverage_steps(test_data)
    homeowner_bind_information_page.set_existing_client(test_data)
    homeowner_bind_information_page.set_refused_in_the_past(test_data)
    homeowner_bind_information_page.set_denied_coverage(test_data)
    homeowner_bind_information_page.click_save()
    homeowner_bind_information_page.click_rate_quote()
    log.info("Successfully filled homeowner location coverage information.")


@when("I exercise additional homeowner elements")
def exercise_additional_homeowner_elements(
    homeowner_quote_summary_page,
    homeowner_city_information_page,
    homeowner_coverage_page,
    homeowner_bind_information_page,
    homeowner_premium_summary_page,
    homeowner_delivery_preferences_page,
    homeowner_billing_plan_page,
    homeowner_verify_billing_page,
    test_data,
    log,
):
    log.info("Exercising additional homeowner elements discovered in the live flow...")
    review_homeowner_quote_summary_additional_elements(homeowner_quote_summary_page, test_data, log)
    complete_homeowner_quote_summary_details(homeowner_quote_summary_page, test_data, log)
    review_homeowner_city_information_elements(homeowner_city_information_page, test_data, log)
    provide_homeowner_location_coverage_additional_elements(homeowner_coverage_page, test_data, log)
    provide_homeowner_bind_information(homeowner_bind_information_page, test_data, log)
    review_homeowner_premium_summary_elements(homeowner_premium_summary_page, log)
    review_homeowner_delivery_preference_elements(homeowner_delivery_preferences_page, log)
    review_homeowner_billing_plan_elements(homeowner_billing_plan_page, log)
    review_homeowner_verify_billing_elements_and_bind(homeowner_verify_billing_page, log)
    log.info("Successfully exercised additional homeowner elements.")


@when("I review homeowner quote summary additional elements")
def review_homeowner_quote_summary_additional_elements(homeowner_quote_summary_page, test_data, log):
    log.info("Reviewing homeowner quote summary additional elements...")
    homeowner_quote_summary_page.review_additional_summary_elements(test_data)


@when("I complete homeowner quote summary details")
def complete_homeowner_quote_summary_details(homeowner_quote_summary_page, test_data, log):
    log.info("Completing homeowner quote summary details...")
    homeowner_quote_summary_page.set_program(test_data)
    homeowner_quote_summary_page.set_billing(test_data)
    homeowner_quote_summary_page.set_day_care(test_data)
    homeowner_quote_summary_page.set_underground_oil_tank(test_data)
    homeowner_quote_summary_page.set_residence_rented(test_data)
    homeowner_quote_summary_page.residence_vacant(test_data)
    homeowner_quote_summary_page.set_animals(test_data)
    homeowner_quote_summary_page.click_save()
    homeowner_quote_summary_page.click_city_info_link(test_data)


@when("I review homeowner city information elements")
def review_homeowner_city_information_elements(homeowner_city_information_page, test_data, log):
    log.info("Reviewing homeowner city information elements...")
    homeowner_city_information_page.review_city_information_elements(test_data)
    homeowner_city_information_page.click_save()
    homeowner_city_information_page.click_homeowners_link(test_data)


@when("I provide homeowner location coverage additional elements")
def provide_homeowner_location_coverage_additional_elements(homeowner_coverage_page, test_data, log):
    log.info("Providing homeowner location coverage and reviewing additional elements...")
    homeowner_coverage_page.set_residency(test_data)
    homeowner_coverage_page.set_coverage(test_data)
    homeowner_coverage_page.wait_for_loader_to_disappear()
    homeowner_coverage_page.set_replacement(test_data)
    homeowner_coverage_page.set_additional_limit_fields(test_data)
    homeowner_coverage_page.set_perils(test_data)
    homeowner_coverage_page.set_windstorm(test_data)
    homeowner_coverage_page.set_liability(test_data)
    homeowner_coverage_page.set_medical(test_data)
    homeowner_coverage_page.set_year_built(test_data)
    homeowner_coverage_page.set_construction(test_data)
    homeowner_coverage_page.set_roof_type(test_data)
    homeowner_coverage_page.set_under_construction(test_data)
    homeowner_coverage_page.set_lived_here(test_data)
    homeowner_coverage_page.set_loses(test_data)
    homeowner_coverage_page.review_mitigation_and_security_elements()
    homeowner_coverage_page.click_save()
    homeowner_coverage_page.click_bind_info()


@when("I provide homeowner bind information")
def provide_homeowner_bind_information(homeowner_bind_information_page, test_data, log):
    log.info("Providing homeowner bind information...")
    homeowner_bind_information_page.set_existing_client(test_data)
    homeowner_bind_information_page.set_refused_in_the_past(test_data)
    homeowner_bind_information_page.set_denied_coverage(test_data)
    homeowner_bind_information_page.click_save()
    homeowner_bind_information_page.click_rate_quote()


@when("I review homeowner premium summary elements")
def review_homeowner_premium_summary_elements(homeowner_premium_summary_page, log):
    log.info("Reviewing homeowner premium summary elements...")
    homeowner_premium_summary_page.review_premium_summary_elements()
    homeowner_premium_summary_page.click_issue()
    homeowner_premium_summary_page.wait_for_loader_to_disappear()


@when("I review homeowner delivery preference elements")
def review_homeowner_delivery_preference_elements(homeowner_delivery_preferences_page, log):
    log.info("Reviewing homeowner delivery preference elements...")
    homeowner_delivery_preferences_page.review_delivery_preference_elements()
    homeowner_delivery_preferences_page.click_next()


@when("I review homeowner billing plan elements")
def review_homeowner_billing_plan_elements(homeowner_billing_plan_page, log):
    log.info("Reviewing homeowner billing plan elements...")
    homeowner_billing_plan_page.review_billing_plan_elements()
    homeowner_billing_plan_page.click_next()


@when("I review homeowner verify billing elements and bind")
def review_homeowner_verify_billing_elements_and_bind(homeowner_verify_billing_page, log):
    log.info("Reviewing homeowner verify billing elements and binding policy...")
    homeowner_verify_billing_page.review_verify_billing_elements()
    homeowner_verify_billing_page.click_bind()


@when("I provide location coverage info for UW testing")
def ho_coverage_info_uw(page, homeowner_coverage_page, homeowner_bind_information_page, test_data, log):
    """
    Fill Location Coverage and handle UW conditions that may appear during
    location coverage, bind information, or rating.
    """
    uw_indicator = page.locator("text=underwriting referral")

    if uw_indicator.is_visible(timeout=2_000):
        log.info("UW referral already visible before coverage step - skipping.")
        return

    try:
        log.info("Filling location coverage for UW testing...")
        homeowner_coverage_page.coverage_steps(test_data)
        homeowner_bind_information_page.set_existing_client(test_data)
        homeowner_bind_information_page.set_refused_in_the_past(test_data)
        homeowner_bind_information_page.set_denied_coverage(test_data)
        homeowner_bind_information_page.click_save()
        homeowner_bind_information_page.click_rate_quote()
        log.info("Coverage steps completed - Rate Quote clicked, UW referral expected.")
    except Exception:
        if uw_indicator.is_visible(timeout=5_000):
            log.info("UW referral detected during coverage/rating - proceeding to assertion.")
            return
        raise


@then(parsers.parse('the UW referral page shows a "{uw_type}" condition containing "{expected_condition}"'))
def assert_uw_condition_present(uw_referral_page, uw_type, expected_condition, log):
    allure.dynamic.parameter("UW Type", uw_type)
    allure.dynamic.parameter("Triggered Condition", expected_condition)
    expected_conditions = [
        condition.strip()
        for condition in expected_condition.split(";")
        if condition.strip()
    ]
    log.info(f"Asserting UW condition(s): type='{uw_type}', contains={expected_conditions}")
    for condition in expected_conditions:
        uw_referral_page.assert_uw_condition(uw_type, condition)
    log.info("UW condition assertion passed.")


@then("no active UW conditions are present")
def assert_no_active_uw(page, log):
    uw_breadcrumb = page.locator("text=underwriting referral")
    assert not uw_breadcrumb.is_visible(timeout=3_000), (
        "Expected clean rating (no UW referral) but 'underwriting referral' breadcrumb is visible."
    )
    premium_summary = page.locator("text=premium | summary")
    assert premium_summary.is_visible(timeout=5_000), (
        "Expected to land on premium summary after clean rating but it is not visible."
    )
    log.info("Clean profile confirmed - no active UW conditions, on premium summary.")
