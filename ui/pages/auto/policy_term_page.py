from ui.pages.common.base_page import BasePage


class PolicyTermPage(BasePage):
    """Handles policy term and coverage details."""
    
    def __init__(self, page):
        super().__init__(page)
        self.coverage = page.get_by_role("combobox", name="Policy Coverage Option*")
        self.rate_quote_button = page.get_by_role("button", name=">>> Rate Quote")

    def policy_term_steps(self, data):
        """Perform policy term steps."""
        self.set_coverage(data)
        self.wait_for_loader_to_disappear()
        self.click_rate()

    def set_coverage(self, data):
        """Set policy coverage option."""
        coverage = data["PolicyCoverage"]
        self.smart_click(self.coverage)
        self.smart_click(self.page.locator(f"//li[text()='{coverage}']"))

    def wait_for_loader_to_disappear(self):
        self.spinner_wait("#ajax-sub-pre-loading")

    def click_rate(self):
        """Rate the quote."""
        self.smart_click(self.rate_quote_button)
