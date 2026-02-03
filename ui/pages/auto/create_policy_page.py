import time
from ui.pages.common.base_page import BasePage


class CreatePolicyPage(BasePage):
    """Handles policy creation from quote."""
    
    def __init__(self, page):
        super().__init__(page)
        self.request_issue = page.get_by_role("button", name=">>> request issue")
        self.next_button = page.get_by_role("button", name=">>> next")
        self.bind_button = page.get_by_role("button", name=">>> bind", exact=True)

    def click_issue(self):
        """Request policy issue."""
        self.request_issue.click()

    def click_next(self):
        """Proceed to next step."""
        self.next_button.click()
        time.sleep(1)

    def click_bind(self):
        """Bind the policy."""
        self.bind_button.click()
