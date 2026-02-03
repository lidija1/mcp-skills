import re

from ui.pages.common.base_page import BasePage


class HomeownerQuoteSummary(BasePage):
    """Handles quote summary information for homeowner insurance."""

    def __init__(self, page):
        super().__init__(page)
        self.billing = page.get_by_role("combobox", name="Billing Method*")
        self.program_type = page.get_by_role("combobox", name="Program Type*")
        self.save_button = page.get_by_role("button", name="save changes")

    def quote_summary(self, data):
        """Fill quote summary information."""
        self.set_billing(data)
        self.set_program_type(data)
        self.set_day_care_info(data)
        self.set_oil_info(data)
        self.set_rented_info(data)
        self.set_rent_info(data)
        self.set_animals_info(data)
        self.click_save()
        self.click_city_info_link(data)
        self.click_save()

    def set_billing(self, data):
        """Set billing method."""
        self.billing.fill(data['BillingMethod'])

    def set_program_type(self, data):
        """Set program type."""
        self.program_type.fill(data['ProgramType'])

    def set_day_care_info(self, data):
        """Answer question about daycare."""
        self.answer_question(
            "Is Child or Day Care run out of the home?",
            data["Day Care"]
        )

    def set_oil_info(self, data):
        """Answer question about oil."""
        self.answer_question(
            "Any underground oil or storage tanks?",
            data["Underground oil"]
        )

    def set_rented_info(self, data):
        """Answer question about rental."""
        self.answer_question(
            "Is the residence rented more than 10 weeks per year?",
            data["Residence more than 10"]
        )

    def set_rent_info(self, data):
        """Answer question about rental."""
        self.answer_question(
            "Residence rented",
            data["Residence rented"]
        )

    def set_animals_info(self, data):
        """Answer question about animals."""
        self.answer_question(
            "Are there any animals or exotic pets kept on the premises?",
            data["Animals"]
        )

    def click_save(self):
        """Save changes."""
        self.save_button.click()

    def click_city_info_link(self, data):
        """Navigate to driver information page."""
        city = data["City"]
        city_info_link = self.page.get_by_role("link", name=re.compile(city, re.IGNORECASE))
        city_info_link.click()

    def click_homeowners_info_link(self, data):
        homeowners_info_link = self.page.get_by_role("link", name="homeowners | location coverage")
        homeowners_info_link.click()