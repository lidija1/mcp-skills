import time

import allure

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
        self.address = page.get_by_role("textbox", name="Address Line 1")
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
        self.dob_input(data)
        self.phone_number_input(data)
        self.enter_email(data)
        self.click_search()
        self.click_create_new_customer()
        self.click_next()
        self.skip_button.click()
        self.wait_for_loader_to_disappear()

    @allure.step("Enter First Name")
    def first_name_input(self, data):
        self.first_name.fill(data["FirstName"])

    @allure.step("Enter Last Name")
    def last_name_input(self, data):
        self.last_name.fill(data["LastName"])

    @allure.step("Enter ZIP Code")
    def zip_code_input(self, data):
        with self.page.expect_response("**/FieldProcessorServlet*") as response_info:
            self.zip_code.fill(data["ZIP"])
        response = response_info.value
        if response.status != 200:
            self.logger.info(f"Warning: FieldProcessor returned status {response.status}")

    @allure.step("Select State")
    def state_input(self, data):
        self.state.fill(data["State"])

    @allure.step("Select City")
    def city_input(self, data):
        self.city.fill(data["City"])

    @allure.step("Enter Address")
    def address_input(self, data):
        self.address.fill(data["Address"])

    @allure.step("Select Customer Type")
    def customer_type_input(self, data):
        with self.page.expect_response("**/FieldProcessorServlet*") as response_info:
            self.customer_type.fill(data["CustomerType"])
        response = response_info.value
        if response.status != 200:
            self.logger.info(f"Warning: FieldProcessor returned status {response.status}")

    @allure.step("Enter Date of Birth")
    def dob_input(self, data):
        self.dob.fill(data["DOB"])

    @allure.step("Enter Phone Number")
    def phone_number_input(self, data):
        self.phone_number.fill(data["PhoneNum"])

    @allure.step("Enter Email")
    def enter_email(self, data):
        """Enter and process email address."""
        email_from_excel = data.get("Email")
        processed_email = process_email(email_from_excel)
        self.email.fill(processed_email)

    @allure.step("Search for Customer")
    def click_search(self):
        """Search for existing customer."""
        self.search_button.click()

    @allure.step("Create New Customer Button")
    def click_create_new_customer(self):
        """Create a new customer."""
        self.create_new_customer.click()

    @allure.step("Click Next")
    def click_next(self):
        """Proceed to next step."""
        self.next_button.click()

    @allure.step("Skip Current Step")
    def click_skip(self):
        """Skip current step."""
        self.skip_button.click()

    def wait_for_loader_to_disappear(self):
        self.spinner_wait("#ajax-sub-pre-loading")

    def check_next_page_loaded(self):
        page_msg = self.page.get_by_text("Search Page")
        expect(page_msg).to_be_visible()