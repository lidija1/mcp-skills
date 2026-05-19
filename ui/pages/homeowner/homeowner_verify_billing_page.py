from ui.pages.common.base_page import BasePage


class HomeownerVerifyBillingPage(BasePage):
    """Handles homeowner final billing review and bind actions."""

    def __init__(self, page):
        super().__init__(page)
        self.billing_plan_name = page.get_by_role("textbox", name="Billing Plan Name")
        self.payment_plan = page.get_by_role("textbox", name="Payment Plan")
        self.payment_mode = page.get_by_role("textbox", name="Payment Mode")
        self.bind_button = page.get_by_role("button", name=">>> bind", exact=True)
        self.bind_with_payment = page.get_by_role("button", name=">>> Bind With Payment")

    def review_verify_billing_elements(self):
        """Verify final billing review actions before bind."""
        self.wait_for_loader_to_disappear()
        for locator in (
            self.billing_plan_name,
            self.payment_plan,
            self.payment_mode,
            self.bind_button,
            self.bind_with_payment,
        ):
            locator.scroll_into_view_if_needed()
            locator.wait_for(state="visible", timeout=15000)

    def click_bind(self):
        self.smart_click(self.bind_button)
        self.wait_for_loader_to_disappear()
