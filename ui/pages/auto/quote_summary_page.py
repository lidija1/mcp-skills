import re
from ui.pages.common.base_page import BasePage


class QuoteSummaryPage(BasePage):
    """Handles quote summary information for auto insurance."""
    
    def __init__(self, page):
        super().__init__(page)
        self.billing = page.get_by_role("combobox", name="Billing Method*")
        self.save_button = page.get_by_role("button", name="save changes")

    def summary_steps(self, data):
        """Perform quote summary steps."""
        self.set_billing(data)
        self.wait_for_loader_to_disappear()
        self.set_misleading_info(data)
        self.set_damage_info(data)
        self.click_save()
        self.click_driver_info_link(data)

    def set_billing(self, data):
        """Set billing method."""
        self.smart_fill(self.billing, data['BillingMethod'])

    def wait_for_loader_to_disappear(self):
        self.spinner_wait("#ajax-sub-pre-loading")

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
        self.smart_click(self.save_button)

    def click_driver_info_link(self, data):
        """Navigate to driver information page."""
        first_name = data["FirstName"]
        driver_info_link = self.page.get_by_role("link", name=re.compile(first_name, re.IGNORECASE))
        self.smart_click(driver_info_link)
