from ui.pages.common.base_page import BasePage


class HomeownerBillingPlanPage(BasePage):
    """Handles homeowner billing plan controls."""

    def __init__(self, page):
        super().__init__(page)
        self.next_button = page.get_by_role("button", name=">>> next")
        self.billing_plan_name = page.get_by_role("textbox", name="Billing Plan Name")
        self.default_name = page.get_by_label("Default Name")
        self.billing_options = page.get_by_role("radiogroup", name="Options")
        self.same_method_all_payments = self.billing_options.get_by_label("Use the same method for all the payments")
        self.different_down_payment_method = self.billing_options.get_by_label(
            "Use a different method for the down payment"
        )
        self.edit_profile_details = page.get_by_text("Edit Profile Details").first
        self.payer_currency = page.get_by_role("combobox", name="Payer Currency")
        self.payment_plan = page.get_by_role("combobox", name="Payment Plan*")

    def review_billing_plan_elements(self):
        """Verify billing plan controls before moving to verify billing."""
        self.wait_for_loader_to_disappear()
        for locator in (
            self.billing_plan_name,
            self.default_name,
            self.billing_options,
            self.same_method_all_payments,
            self.different_down_payment_method,
            self.edit_profile_details,
            self.payer_currency,
            self.payment_plan,
        ):
            locator.scroll_into_view_if_needed()
            locator.wait_for(state="visible", timeout=15000)

    def click_next(self):
        self.smart_click(self.next_button)
        self.wait_for_loader_to_disappear()
