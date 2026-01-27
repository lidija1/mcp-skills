import time
from ui.pages.base_page import BasePage


class PolicyTermPage(BasePage):
    """Handles policy term and coverage details."""
    
    def __init__(self, page):
        super().__init__(page)
        self.coverage = page.get_by_role("combobox", name="Policy Coverage Option*")
        self.rate_quote_button = page.get_by_role("button", name=">>> Rate Quote")

    def set_coverage(self, data):
        """Set policy coverage option."""
        coverage = data["PolicyCoverage"]
        self.coverage.fill(coverage)
        self.page.keyboard.press("Enter")  # Sometimes needed after fill on combobox
        time.sleep(0.5)

    def click_rate(self):
        """Rate the quote."""
        self.rate_quote_button.click()
