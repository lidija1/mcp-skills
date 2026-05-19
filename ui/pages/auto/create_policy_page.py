from ui.pages.common.base_page import BasePage


class CreatePolicyPage(BasePage):
    """Handles policy creation from quote."""
    
    def __init__(self, page):
        super().__init__(page)
        self.request_issue = page.get_by_role("button", name=">>> request issue")
        self.next_button = page.get_by_role("button", name=">>> next")
        self.bind_button = page.get_by_role("button", name=">>> bind", exact=True)

    def policy_creation_steps(self):
        """Execute steps to create a policy."""
        self.click_issue()
        self.wait_for_loader_to_disappear()
        self.click_next()
        self.wait_for_loader_to_disappear()
        self.click_next()
        self.wait_for_loader_to_disappear()
        self.click_bind()
        self.wait_for_loader_to_disappear()

    def click_issue(self):
        """Request policy issue."""
        self.smart_click(self.request_issue)

    def click_next(self):
        """Proceed to next step."""
        self.smart_click(self.next_button)

    def click_bind(self):
        """Bind the policy."""
        self.smart_click(self.bind_button)
