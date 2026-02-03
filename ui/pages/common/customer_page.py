import time
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
        time.sleep(0.5)

    def fill_customer_form(self, data):
        """Fill out the customer form with provided data."""
        self.first_name.fill(data["FirstName"])
        self.last_name.fill(data["LastName"])
        self.safe_fill(self.zip_code, data["ZIP"])
        self.safe_fill(self.address, data["Address"])
        self.dob.fill(data["DOB"])
        self.phone_number.fill(data["PhoneNum"])

    def enter_email(self, data):
        """Enter and process email address."""
        email_from_excel = data.get("Email")
        processed_email = process_email(email_from_excel)
        self.email.fill(processed_email)

    def click_search(self):
        """Search for existing customer."""
        self.search_button.click()

    def click_create_new_customer(self):
        """Create a new customer."""
        self.create_new_customer.click()

    def click_next(self):
        """Proceed to next step."""
        self.next_button.click()

    def click_skip(self):
        """Skip current step."""
        self.skip_button.click()
