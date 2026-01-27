"""Auto insurance quote and policy workflow step definitions."""
from pytest_bdd import when, given, then


@when("i create a new quote")
def create_new_quote(new_quote_page, log):
    """Initiate a new quote creation process."""
    log.info("Starting new quote creation...")
    new_quote_page.click_quotes_button()
    new_quote_page.click_new_quote_button()
    new_quote_page.click_agent_radio_button()
    new_quote_page.click_next_button()
    log.info("Successfully created new quote.")


@when("i create a new customer")
def create_new_customer(customer_page, test_data, log):
    """Create a new customer with provided data."""
    log.info("Starting customer creation...")
    customer_page.fill_customer_form(test_data)
    customer_page.enter_email(test_data)
    customer_page.click_search()
    customer_page.click_create_new_customer()
    customer_page.click_next()
    customer_page.click_skip()
    log.info("Successfully created new customer.")


@when("I provide quote registration details")
def provide_quote_registration(quote_registration_page, test_data, log):
    """Fill quote registration details."""
    log.info("Filling quote registration details...")
    quote_registration_page.fill_producer(test_data)
    quote_registration_page.set_effective_date(test_data)
    quote_registration_page.fill_program(test_data)
    quote_registration_page.click_next()
    log.info("Successfully filled quote registration details.")


@when("I provide quote summary PA info")
def provide_quote_summary(quote_summary_page, test_data, log):
    """Fill quote summary information."""
    log.info("Filling quote summary information...")
    quote_summary_page.set_billing(test_data)
    quote_summary_page.set_misleading_info(test_data)
    quote_summary_page.set_damage_info(test_data)
    quote_summary_page.click_save()
    quote_summary_page.click_driver_info_link(test_data)
    log.info("Successfully filled quote summary information.")


@when("I provide Driver Details")
def provide_driver_details(driver_info_page, test_data, log):
    """Fill driver information."""
    log.info("Filling driver details...")
    driver_info_page.fill_driver_info(test_data)
    driver_info_page.click_vehicle_info_link(test_data)
    log.info("Successfully filled driver details.")


@when("I provide Vehicle Details")
def provide_vehicle_details(vehicle_info_page, test_data, log):
    """Fill vehicle information."""
    log.info("Filling vehicle details...")
    vehicle_info_page.fill_vehicle_info(test_data)
    vehicle_info_page.click_save()
    vehicle_info_page.click_coverages_link()
    log.info("Successfully filled vehicle details.")


@given("I provide policy term details")
def provide_policy_term_details(policy_term_page, test_data, log):
    """Fill policy term and coverage details."""
    log.info("Filling policy term details...")
    policy_term_page.set_coverage(test_data)
    policy_term_page.click_rate()
    log.info("Successfully filled policy term details.")


@then("I create a policy from the quote")
def create_policy_from_quote(create_policy_page, test_data, log):
    """Create and bind a policy from the quote."""
    log.info("Creating policy from quote...")
    create_policy_page.click_issue()
    create_policy_page.click_next()
    create_policy_page.click_next()
    create_policy_page.click_bind()
    log.info("Successfully created and bound policy.")
