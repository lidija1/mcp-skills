from ui.pages.common.base_page import BasePage


class HomeownerDeliveryPreferencesPage(BasePage):
    """Handles homeowner delivery preference controls."""

    def __init__(self, page):
        super().__init__(page)
        self.next_button = page.get_by_role("button", name=">>> next")
        self.product = page.get_by_role("textbox", name="Product")
        self.billing_address = page.get_by_role("textbox", name="Billing Address")
        self.add_new_preference = page.get_by_role("button", name="+ Add A New Preference")
        self.add_preference = page.get_by_role("button", name="Add", exact=True)
        self.remove_preference = page.get_by_role("button", name="Remove")
        self.primary_email = page.get_by_role("textbox", name="Primary Email")
        self.validate_email = page.get_by_role("button", name="XxxValidate Email")

    def review_delivery_preference_elements(self):
        """Verify delivery preference controls before moving to billing."""
        self.wait_for_loader_to_disappear()
        for locator in (
            self.product,
            self.billing_address,
            self.add_new_preference,
            self.add_preference,
            self.remove_preference,
            self.primary_email,
            self.validate_email,
        ):
            locator.scroll_into_view_if_needed()
            locator.wait_for(state="visible", timeout=15000)

    def click_next(self):
        self.smart_click(self.next_button)
        self.wait_for_loader_to_disappear()
