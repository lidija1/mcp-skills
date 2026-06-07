from pytest_bdd import when


@when("I provide Cyber policy information")
def provide_cyber_policy_information(
    cyber_policy_information_page,
    test_data,
    log,
):
    log.info("Providing Cyber policy information...")
    cyber_policy_information_page.fill_policy_information(test_data)


@when("I review discovered Cyber policy information elements")
def review_discovered_cyber_elements(cyber_policy_information_page, log):
    log.info("Reviewing discovered Cyber policy information controls...")
    cyber_policy_information_page.review_discovered_controls()


@when("I review Cyber Reinsurance and Inspection elements")
def review_cyber_reinsurance_and_inspection(
    cyber_reinsurance_page,
    cyber_inspection_page,
    log,
):
    log.info("Reviewing Cyber Reinsurance controls...")
    cyber_reinsurance_page.review_new_reinsurance_fields()
    log.info("Reviewing Cyber Inspection request controls...")
    cyber_inspection_page.review_inspection_request_fields()
    log.info("Reviewing Cyber Inspection assignment controls...")
    cyber_inspection_page.review_inspection_assignment_fields()


@when("I exercise configured Cyber optional fields")
def exercise_configured_cyber_optional_fields(
    cyber_policy_information_page,
    cyber_reinsurance_page,
    cyber_inspection_page,
    test_data,
    log,
):
    flow = test_data["OptionalFlow"]
    log.info("Exercising Cyber optional flow: %s", flow)
    cyber_policy_information_page.fill_policy_information(test_data)

    if flow == "PolicyOptionalCoverage":
        return
    if flow == "Reinsurance":
        cyber_reinsurance_page.fill_reinsurance_fields(test_data)
        return
    if flow == "InspectionRequest":
        cyber_inspection_page.fill_inspection_request_fields(test_data)
        return
    if flow == "InspectionAssignment":
        cyber_inspection_page.fill_inspection_assignment_fields(test_data)
        return
    raise AssertionError(f"Unsupported Cyber optional flow: {flow}")


@when("I rate and issue the Cyber quote")
def rate_and_issue_cyber_quote(
    cyber_policy_information_page,
    cyber_premium_summary_page,
    log,
):
    log.info("Rating and requesting issue for the Cyber quote...")
    cyber_policy_information_page.click_rate_quote()
    cyber_premium_summary_page.click_request_issue()


@when("I complete Cyber policy binding")
def complete_cyber_policy_binding(
    delivery_preferences_page,
    billing_plan_page,
    verify_billing_page,
    test_data,
    log,
):
    log.info("Completing Cyber delivery, billing, and bind...")
    delivery_preferences_page.click_next()
    billing_plan_page.complete_billing_plan(test_data)
    verify_billing_page.click_bind()
    verify_billing_page.wait_for_app_ready()
