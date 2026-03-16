import re

from ui.pages.common.base_page import BasePage


class HomeOwnerQuoteSummaryPage(BasePage):
    """Handles quote summary information for homeowners insurance."""

    def __init__(self, page):
        super().__init__(page)
        self.billing = page.get_by_role("combobox", name="Billing Method*")
        self.program=page.get_by_role("combobox", name="Program Type*")
        self.save_button = page.get_by_role("button", name="save changes")

    def summary_steps(self, data):
        """Perform quote summary steps."""
        self.set_program(data)
        self.set_billing(data)
        self.wait_for_loader_to_disappear()
        self.set_day_care(data)
        self.set_underground_oil_tank(data)
        self.set_residence_rented(data)
        self.residence_vacant(data)
        self.set_animals(data)
        self.set_save()
        self.click_city_info_link(data)
        self.set_save()
        self.click_homeowners_link(data)

    def set_billing(self, data):
        """Set billing method."""
        self.smart_fill(self.billing, data["BillingMethod"])

    def wait_for_loader_to_disappear(self):
        self.spinner_wait("#ajax-sub-pre-loading")

    def set_program(self, data):
        """Set program type."""  
        self.program.click()
        self.page.get_by_role("option", name=data['ProgramType'], exact=True).click()

    def set_day_care(self, data):
        """Answer question about day care."""
        self.answer_question(
            "Is Child or Day Care run out",
            data["DayCare"]
        )

    def set_underground_oil_tank(self, data):
        """Answer question about underground oil tank."""
        self.answer_question(
            "Any underground oil or",
            data["UndergroundOil"]
        )

    def set_residence_rented(self, data):
        """Answer question about residence rented."""
        self.answer_question(
            "Is the residence rented more",
            data["ResidenceRented"]
        )

    def residence_vacant(self, data):
        """Answer question about residence vacant."""
        self.answer_question(
            "Is the residence vacant?",
            data["ResidenceVacant"]
        )

    def set_animals(self, data):
        """Answer question about animals."""
        self.answer_question(
            "Are there any animals or",
            data["Animals"]
        )

    def set_save(self):
        """Save changes."""
        self.smart_click(self.save_button)

    def click_city_info_link(self, data):
        """Navigate to HO information page."""
        city = data["City"]
        city_info_link = self.page.get_by_role("link", name=re.compile(city, re.IGNORECASE))
        self.smart_click(city_info_link)

    def click_homeowners_link(self, data):
        """Navigate to coverage options"""
        program = data["Program"]
        program_link = self.page.get_by_role("link", name=re.compile(program, re.IGNORECASE))
        self.smart_click(program_link)

