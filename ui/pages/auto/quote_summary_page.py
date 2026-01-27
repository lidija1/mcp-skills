import re
from ui.pages.base_page import BasePage


class QuoteSummaryPage(BasePage):
    """Handles quote summary information for auto insurance."""
    
    def __init__(self, page):
        super().__init__(page)
        self.billing = page.get_by_role("combobox", name="Billing Method*")
        self.save_button = page.get_by_role("button", name="save changes")

    def set_billing(self, data):
        """Set billing method."""
        self.billing.fill(data['BillingMethod'])

    def set_misleading_info(self, data):
        """Answer question about false/misleading information."""
        self.answer_question(
            "Has anyone knowingly provided material, false, or misleading information ",
            data["FalseInfo"]
        )

    def set_damage_info(self, data):
        """Answer question about existing vehicle damage."""
        self.answer_question(
            "Does any vehicle have any existing damage?",
            data["DamageInfo"]
        )

    def click_save(self):
        """Save changes."""
        self.save_button.click()

    def click_driver_info_link(self, data):
        """Navigate to driver information page."""
        first_name = data["FirstName"]
        driver_info_link = self.page.get_by_role("link", name=re.compile(first_name, re.IGNORECASE))
        driver_info_link.click()
