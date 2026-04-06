from pytest_bdd import when


@when("I provide Cyber quote details")
def provide_cyber_quote_details(cyber_quote_page, test_data, log):
    log.info("Filling Cyber quote details...")
    cyber_quote_page.fill_cyber_quote_details(test_data)
    log.info("Successfully filled Cyber quote details.")


@when("I rate the Cyber quote")
def rate_cyber_quote(cyber_quote_page, log):
    log.info("Clicking rate quote...")
    cyber_quote_page.click_rate_quote()
    log.info("Cyber quote rated successfully.")


@when("I request issue for the Cyber quote")
def request_issue_cyber(cyber_premium_summary_page, log):
    log.info("Clicking request issue...")
    cyber_premium_summary_page.click_request_issue()
    log.info("Request issue submitted.")


@when("I complete delivery preferences")
def complete_delivery_preferences(delivery_preferences_page, log):
    log.info("Proceeding through delivery preferences...")
    delivery_preferences_page.click_next()
    log.info("Delivery preferences completed.")


@when("I complete billing plan")
def complete_billing_plan(billing_plan_page, test_data, log):
    log.info("Completing billing plan...")
    billing_plan_page.complete_billing_plan(test_data)
    log.info("Billing plan completed.")


@when("I bind the Cyber policy")
def bind_cyber_policy(verify_billing_page, log):
    log.info("Binding Cyber policy...")
    verify_billing_page.click_bind()
    log.info("Cyber policy bind action completed.")
