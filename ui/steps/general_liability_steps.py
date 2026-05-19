from pytest_bdd import then, when, parsers


@when("I provide general liability risk address details")
def provide_general_liability_risk_address_details(general_liability_risk_address_page, test_data, log):
    log.info("Providing general liability risk address details...")
    general_liability_risk_address_page.risk_address_steps(test_data)
    log.info("Successfully provided general liability risk address details.")


@when("I provide general liability basic policy information")
def provide_general_liability_basic_policy_information(general_liability_basic_policy_information_page, test_data, log):
    log.info("Providing general liability basic policy information...")
    general_liability_basic_policy_information_page.basic_policy_information_steps(test_data)
    log.info("Successfully provided general liability basic policy information.")


@when("I provide general liability coverage and limits")
def provide_general_liability_coverage_and_limits(general_liability_coverage_and_limits_page, test_data, log):
    log.info("Providing general liability coverage and limits...")
    general_liability_coverage_and_limits_page.coverage_and_limits_steps(test_data)
    log.info("Successfully provided general liability coverage and limits.")


@when("I provide general liability liability location list details")
def provide_general_liability_liability_location_list(general_liability_liability_location_list_page, test_data, log):
    log.info("Providing general liability liability location list details...")
    general_liability_liability_location_list_page.liability_location_list_steps(test_data)
    log.info("Successfully provided general liability liability location list details.")


@when("I provide general liability rating basis and classification details")
def provide_general_liability_rating_basis_and_classification(
    general_liability_rating_basis_and_classification_page,
    test_data,
    log,
):
    log.info("Providing general liability rating basis and classification details...")
    general_liability_rating_basis_and_classification_page.rating_basis_and_classification_steps(test_data)
    log.info("Successfully provided general liability rating basis and classification details.")


@when("I rate the general liability quote")
def rate_general_liability_quote(general_liability_rating_basis_and_classification_page, log):
    log.info("Clicking general liability rate quote...")
    general_liability_rating_basis_and_classification_page.click_rate_quote()
    log.info("General liability quote rated successfully.")


@when("I request issue for the general liability quote")
def request_issue_general_liability(general_liability_rating_basis_and_classification_page, log):
    log.info("Clicking general liability request issue...")
    general_liability_rating_basis_and_classification_page.click_request_issue()
    log.info("General liability request issue submitted.")


@when("I proceed to the general liability billing plan")
def proceed_to_general_liability_billing_plan(general_liability_rating_basis_and_classification_page, log):
    log.info("Proceeding to the general liability billing plan...")
    general_liability_rating_basis_and_classification_page.click_next()
    log.info("Arrived at the general liability billing plan.")


@when("I complete the general liability billing plan")
def complete_general_liability_billing_plan(billing_plan_page, test_data, log):
    log.info("Completing general liability billing plan...")
    billing_plan_page.complete_billing_plan(test_data)
    log.info("General liability billing plan completed.")


@when("I bind the general liability policy")
def bind_general_liability_policy(verify_billing_page, log):
    log.info("Binding general liability policy...")
    verify_billing_page.click_bind()
    log.info("General liability policy bind action completed.")


@then("the general liability flow is complete")
def general_liability_flow_complete(log):
    log.info("General liability flow reached the final page.")


@then("I read and extract policy summary page details for general liability")
def read_extract_gl_summary(policy_summary_page, test_data, log):
    log.info("Extracting General Liability policy summary details...")

    details = policy_summary_page.extract_details(test_data)
    path = policy_summary_page.save_lob_report(details)
    log.info("Data saved to CSV: " + path)

    log.info("-" * 40)
    log.info("POLICY SUMMARY DETAILS:")
    for key, value in details.items():
        log.info(f"{key}: {value}")
    log.info("-" * 40)

    print("\n" + "=" * 50)
    print("POLICY SUMMARY REPORT")
    print("=" * 50)
    for key, value in details.items():
        print(f"{key:35}: {value}")
    print("=" * 50 + "\n")
