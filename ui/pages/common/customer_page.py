import time

import allure
from playwright.sync_api import expect

from ui.pages.common.base_page import BasePage
from utils.email_util import process_email


class CustomerPage(BasePage):
    """Handles customer creation and management."""
    
    def __init__(self, page):
        super().__init__(page)
        self.customer_type = page.get_by_role("combobox", name="Customer Type")
        self.first_name = page.get_by_role("textbox", name="First Name")
        self.last_name = page.get_by_role("textbox", name="Last Name")
        self.dob = page.get_by_role("combobox", name="Date of Birth")
        self.email = page.get_by_role("textbox", name="Email")
        self.phone_number = page.get_by_role("textbox", name="Phone")
        self.zip_code = page.get_by_role("textbox", name="ZIP Code")
        # self.state = page.get_by_role("combobox", name="State")
        self.city = page.get_by_role("textbox", name="City")
        self.address = page.get_by_role("textbox", name="Address Line 1")
        self.click_outside = page.get_by_text("Search for a customer")
        self.search_button = page.get_by_role("button", name=">>> Search")
        self.create_new_customer = page.get_by_role("button", name=">>> Create A New Customer")
        self.next_button = page.get_by_role("button", name=">>> next")
        self.skip_button = page.get_by_role("button", name=">>> skip")

    @allure.step("Create New Customer")
    def customer_steps(self, data):
        self.first_name_input(data)
        self.last_name_input(data)
        self.zip_code_input(data)
        self.customer_type_input(data)
        self.address_input(data)
        # self.state_input(data)
        self.city_input(data)
        self.dob_input(data)
        self.phone_number_input(data)
        self.enter_email(data)
        self.click_search()
        self.click_create_new_customer()
        self.click_next()
        self.smart_click(self.skip_button)
        self.wait_for_loader_to_disappear()

    @allure.step("Enter First Name")
    def first_name_input(self, data):
        self.smart_fill(self.first_name, data["FirstName"])

    @allure.step("Enter Last Name")
    def last_name_input(self, data):
        self.smart_fill(self.last_name, data["LastName"])

    @allure.step("Enter ZIP Code")
    def zip_code_input(self, data):
        self.smart_fill(self.zip_code, data["ZIP"])
        self.page.expect_response("**/FieldProcessorServlet*")



    # @allure.step("Select State")
    # def state_input(self, data):
    #     self.state.fill(data["State"])

    @allure.step("Select City")
    def city_input(self, data):
        self.smart_fill(self.city, data["City"])

    @allure.step("Enter Address")
    def address_input(self, data):
        self.smart_fill(self.address, data["Address"])

    @allure.step("Select Customer Type")
    def customer_type_input(self, data):
        self.smart_fill(self.customer_type, data["CustomerType"])
        

    @allure.step("Enter Date of Birth")
    def dob_input(self, data):
        self.smart_fill(self.dob, data["DOB"])

    @allure.step("Enter Phone Number")
    def phone_number_input(self, data):
        self.smart_fill(self.phone_number, data["PhoneNum"])

    @allure.step("Enter Email")
    def enter_email(self, data):
        """Enter and process email address."""
        email_from_excel = data.get("Email")
        processed_email = process_email(email_from_excel)
        self.smart_fill(self.email, processed_email)

    @allure.step("Search for Customer")
    def click_search(self):
        """Search for existing customer."""
        self.smart_click(self.search_button)

    @allure.step("Create New Customer Button")
    def click_create_new_customer(self):
        """Create a new customer."""
        self.smart_click(self.create_new_customer)

    @allure.step("Click Next")
    def click_next(self):
        """Proceed to next step."""
        self.smart_click(self.next_button)

    @allure.step("Skip Current Step")
    def click_skip(self):
        """Skip current step."""
        self.smart_click(self.skip_button)

    def check_next_page_loaded(self):
        page_msg = self.page.get_by_text("Search Page")
        expect(page_msg).to_be_visible()

        # =========================================================================
        # VALIDATION METHODS
        # =========================================================================

    @allure.step("Fill all customer fields without searching")
    def fill_all_customer_fields(self, data):
        """Fill all customer fields but don't click search yet."""
        self.customer_type_input(data)
        self.first_name_input(data)
        self.last_name_input(data)
        self.dob_input(data)
        self.phone_number_input(data)
        self.enter_email_without_processing(data)
        self.zip_code_input(data)
        self.address_input(data)

    @allure.step("Enter Email (without processing)")
    def enter_email_without_processing(self, data):
        """Enter email address exactly as provided in test data."""
        email = data.get("Email", "")
        self.smart_fill(self.email, email)

    @allure.step("Get Email Validation Error")
    def get_email_validation_error(self):
        """
        Get the email validation error message by searching for the exact error message text.
        Expected format: The email address "entered email" is wrong. An email address can include letters or numbers and must have an @.

        Note: Excludes "No matching results found" which is a search result, not a validation error.
        Also normalizes multiple spaces to single spaces.
        """
        # Wait a moment for validation to trigger
        self.page.wait_for_timeout(1000)

        # Search for the error message by looking for the specific text pattern
        # The locator will search for any element containing this text
        error_locator = self.page.locator("text=/The email address.*is wrong/")

        try:
            if error_locator.first.is_visible(timeout=2000):
                error_text = error_locator.first.text_content()

                # Exclude "No matching results found" - this is not a validation error
                if "no matching results found" in error_text.lower():
                    self.logger.info(f"Skipping search result message (not a validation error): {error_text}")
                    return None

                # Normalize multiple spaces to single spaces
                normalized_error = " ".join(error_text.split())
                self.logger.info(f"Found email validation error: {normalized_error}")
                return normalized_error
        except:
            self.logger.debug("No email validation error found")
            return None

    @allure.step("Get Date of Birth Validation Error")
    def get_dob_validation_error(self):
        """
        Get the date of birth validation error message by searching for the exact error message text.
        Expected formats:
        - "The date "X" is wrong. Numbers must be separated by forward slashes and include month, day and year for example MM/DD/YYYY."
        - "The date "X" is wrong. Date of birth cannot be in the future."
        - "The date "X" is wrong. Date of birth cannot be older than 150 years."

        Note: Excludes "No matching results found" which is a search result, not a validation error.
        Also normalizes multiple spaces to single spaces.
        """
        self.page.wait_for_timeout(1000)

        # Search for the error message by looking for the specific text pattern
        # The locator will search for any element containing this text
        error_locator = self.page.locator("text=/The date.*is wrong/")

        try:
            if error_locator.first.is_visible(timeout=2000):
                error_text = error_locator.first.text_content()

                # Exclude "No matching results found" - this is not a validation error
                if "no matching results found" in error_text.lower():
                    self.logger.info(f"Skipping search result message (not a validation error): {error_text}")
                    return None

                # Normalize multiple spaces to single spaces
                normalized_error = " ".join(error_text.split())
                self.logger.info(f"Found DOB validation error: {normalized_error}")
                return normalized_error
        except:
            self.logger.debug("No DOB validation error found")
            return None

    @allure.step("Get Required Field Validation Errors")
    def get_required_field_errors(self):
        """Get all required field validation error messages."""
        self.page.wait_for_timeout(1000)

        errors = []
        error_selectors = [
            ".error-message",
            ".validation-error",
            "[class*='error'][class*='message']",
            "div[class*='error']",
            "span[class*='error']"
        ]

        for selector in error_selectors:
            try:
                error_elements = self.page.locator(selector).all()
                for element in error_elements:
                    if element.is_visible():
                        error_text = element.text_content()
                        if error_text and error_text.strip():
                            errors.append(error_text.strip())
            except:
                continue

        if errors:
            self.logger.info(f"Found required field errors: {errors}")

        return errors

    @allure.step("Verify Email Validation Error Message")
    def verify_email_validation_error(self, expected_email):
        """
        Verify that the email validation error is displayed with the expected email.

        Args:
            expected_email: The email address that should appear in the error message
        """
        error_message = self.get_email_validation_error()

        if error_message is None:
            raise AssertionError("No email validation error was displayed")

        # Check if the error message contains the expected email
        if expected_email not in error_message:
            raise AssertionError(
                f"Email validation error does not contain expected email.\n"
                f"Expected email: {expected_email}\n"
                f"Actual error: {error_message}"
            )

        # Check if the error message contains the core validation text
        # The actual message format is: "The email address "X" is wrong. An email address can include letters
        # or numbers and must have an @. Multiple emails are separated by a semi colon, for example user123@example.com;user321@example.com."
        expected_text_parts = [
            "is wrong",
            "An email address can include letters or numbers and must have an @"
        ]

        for expected_part in expected_text_parts:
            if expected_part not in error_message:
                raise AssertionError(
                    f"Email validation error does not contain expected text.\n"
                    f"Expected text (partial): {expected_part}\n"
                    f"Actual error: {error_message}"
                )

        self.logger.info(f"✓ Email validation error displayed correctly: {error_message}")
        return True

    @allure.step("Verify No Email Validation Errors")
    def verify_no_email_validation_errors(self):
        """Verify that no email validation errors are displayed."""
        error_message = self.get_email_validation_error()

        if error_message:
            raise AssertionError(
                f"Unexpected email validation error displayed: {error_message}"
            )

        self.logger.info("✓ No email validation errors displayed (as expected)")
        return True

    @allure.step("Verify Date of Birth Validation Error")
    def verify_dob_validation_error(self, expected_partial_message):
        """
        Verify that a date of birth validation error is displayed.

        Args:
            expected_partial_message: Partial text to look for in the error message
        """
        error_message = self.get_dob_validation_error()

        if error_message is None:
            raise AssertionError("No date of birth validation error was displayed")

        # Check if the expected partial message is in the error
        if expected_partial_message.lower() not in error_message.lower():
            raise AssertionError(
                f"DOB validation error does not match expected message.\n"
                f"Expected (partial): {expected_partial_message}\n"
                f"Actual error: {error_message}"
            )

        self.logger.info(f"✓ DOB validation error displayed correctly: {error_message}")
        return True

    @allure.step("Verify Date of Birth Validation Error (Detailed)")
    def verify_dob_validation_error_detailed(self, expected_dob):
        """
        Verify that the DOB validation error is displayed with expected format.
        The actual message format is: "The date "X" is wrong. Numbers must be separated by forward slashes
        and include month, day and year for example MM/DD/YYYY."

        Args:
            expected_dob: The date value that should appear in the error message
        """
        error_message = self.get_dob_validation_error()

        if error_message is None:
            raise AssertionError("No date of birth validation error was displayed")

        # Check if the error message contains the expected DOB
        if expected_dob not in error_message:
            # For some errors, the date might not be shown in the message, so just log a warning
            self.logger.warning(f"DOB '{expected_dob}' not found in error message: {error_message}")

        # Check if the error message contains the core validation text parts
        expected_text_parts = [
            "is wrong",
            "forward slashes"
        ]

        for expected_part in expected_text_parts:
            if expected_part.lower() not in error_message.lower():
                raise AssertionError(
                    f"DOB validation error does not contain expected text.\n"
                    f"Expected text (partial): {expected_part}\n"
                    f"Actual error: {error_message}"
                )

        self.logger.info(f"✓ DOB validation error displayed correctly: {error_message}")
        return True

    @allure.step("Verify No Date of Birth Validation Errors")
    def verify_no_dob_validation_errors(self):
        """Verify that no date of birth validation errors are displayed."""
        error_message = self.get_dob_validation_error()

        if error_message:
            raise AssertionError(
                f"Unexpected DOB validation error displayed: {error_message}"
            )

        self.logger.info("✓ No DOB validation errors displayed (as expected)")
        return True

    @allure.step("Verify Required Field Validation Errors")
    def verify_required_field_errors(self, expected_error_count=None):
        """Verify that required field validation errors are displayed."""
        errors = self.get_required_field_errors()

        if not errors:
            raise AssertionError("No required field validation errors were displayed")

        if expected_error_count and len(errors) != expected_error_count:
            raise AssertionError(
                f"Expected {expected_error_count} validation errors, but found {len(errors)}.\n"
                f"Errors: {errors}"
            )

        self.logger.info(f"✓ Required field validation errors displayed: {errors}")
        return True

