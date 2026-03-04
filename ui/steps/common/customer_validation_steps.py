"""Customer validation step definitions."""
import allure
from pytest_bdd import when, then


@when("I fill all customer fields with test data")
def fill_all_customer_fields(customer_page, test_data, log):
    """Fill all customer fields but don't click search yet."""
    log.info("Filling all customer fields with test data...")
    customer_page.fill_all_customer_fields(test_data)
    log.info("Successfully filled all customer fields.")

    # Log the data being used
    log.info(f"Test Case ID: {test_data.get('TC_ID')}")
    log.info(f"Description: {test_data.get('Description')}")
    log.info(f"Email: {test_data.get('Email')}")
    log.info(f"DOB: {test_data.get('DOB')}")
    log.info(f"Expected Validation: {test_data.get('ValidationType')}")


@when("I click search for customer")
def click_search_for_customer(customer_page, log):
    """Click the search button to trigger validation."""
    log.info("Clicking search button to trigger validation...")
    customer_page.click_search()
    log.info("Search button clicked.")


@then("I should see email validation error message")
def verify_email_validation_error(customer_page, test_data, log):
    """Verify that the email validation error is displayed correctly."""
    log.info("Verifying email validation error message...")

    email = test_data.get("Email", "")
    expected_error = test_data.get("ExpectedValidationError")

    log.info(f"Expected to see error for email: {email}")

    with allure.step(f"Verify email validation error for: {email}"):
        # Take screenshot before validation
        allure.attach(
            customer_page.page.screenshot(),
            name="Before Email Validation Check",
            attachment_type=allure.attachment_type.PNG
        )

        # Verify the error message
        customer_page.verify_email_validation_error(email)

        # Take screenshot after validation
        allure.attach(
            customer_page.page.screenshot(),
            name="Email Validation Error Displayed",
            attachment_type=allure.attachment_type.PNG
        )

    log.info(f"✓ Email validation error verified successfully for: {email}")


@then("I should see date of birth validation error message")
def verify_dob_validation_error(customer_page, test_data, log):
    """Verify that the date of birth validation error is displayed correctly."""
    log.info("Verifying date of birth validation error message...")

    dob = test_data.get("DOB", "")
    expected_error = test_data.get("ExpectedValidationError")

    log.info(f"Expected to see error for DOB: {dob}")

    with allure.step(f"Verify DOB validation error for: {dob}"):
        # Take screenshot before validation
        allure.attach(
            customer_page.page.screenshot(),
            name="Before DOB Validation Check",
            attachment_type=allure.attachment_type.PNG
        )

        # Verify the error message contains expected text
        if expected_error:
            customer_page.verify_dob_validation_error(expected_error)
        else:
            customer_page.verify_dob_validation_error("date")

        # Take screenshot after validation
        allure.attach(
            customer_page.page.screenshot(),
            name="DOB Validation Error Displayed",
            attachment_type=allure.attachment_type.PNG
        )

    log.info(f"✓ DOB validation error verified successfully for: {dob}")


@then("I should not see any email validation errors")
def verify_no_email_errors(customer_page, test_data, log):
    """Verify that no email validation errors are displayed."""
    log.info("Verifying no email validation errors are displayed...")

    email = test_data.get("Email", "")
    log.info(f"Validating that email is accepted: {email}")

    with allure.step(f"Verify no email errors for valid email: {email}"):
        # Take screenshot
        allure.attach(
            customer_page.page.screenshot(),
            name="Valid Email - No Errors",
            attachment_type=allure.attachment_type.PNG
        )

        # Verify no email errors
        customer_page.verify_no_email_validation_errors()

    log.info(f"✓ No email validation errors (as expected) for: {email}")


@then("I should not see any date of birth validation errors")
def verify_no_dob_errors(customer_page, test_data, log):
    """Verify that no date of birth validation errors are displayed."""
    log.info("Verifying no DOB validation errors are displayed...")

    dob = test_data.get("DOB", "")
    log.info(f"Validating that DOB is accepted: {dob}")

    with allure.step(f"Verify no DOB errors for valid DOB: {dob}"):
        # Take screenshot
        allure.attach(
            customer_page.page.screenshot(),
            name="Valid DOB - No Errors",
            attachment_type=allure.attachment_type.PNG
        )

        # Verify no DOB errors
        customer_page.verify_no_dob_validation_errors()

    log.info(f"✓ No DOB validation errors (as expected) for: {dob}")


@then("I should see all required field validation errors")
def verify_required_field_errors(customer_page, test_data, log):
    """Verify that required field validation errors are displayed."""
    log.info("Verifying required field validation errors...")

    tc_id = test_data.get("TC_ID", "")
    expected_error = test_data.get("ExpectedValidationError")

    log.info(f"Test Case: {tc_id}")
    log.info(f"Expected Error: {expected_error}")

    with allure.step(f"Verify required field errors for: {tc_id}"):
        # Take screenshot
        allure.attach(
            customer_page.page.screenshot(),
            name="Required Field Validation Errors",
            attachment_type=allure.attachment_type.PNG
        )

        # Verify required field errors are present
        customer_page.verify_required_field_errors()

    log.info(f"✓ Required field validation errors verified for: {tc_id}")

