from ui.pages.common.base_page import BasePage


class HomeownerPremiumSummaryPage(BasePage):
    """Handles homeowner premium summary actions after rating."""

    def __init__(self, page):
        super().__init__(page)
        self.request_issue = page.get_by_role("button", name=">>> request issue")
        self.rating_detail = page.get_by_role("button", name="RATING DETAIL")
        self.re_rate = page.get_by_role("button", name="Re-Rate")
        self.print_quote_letter = page.get_by_role("button", name="Print Quote Letter")
        self.premium_package_selected = page.get_by_role("combobox", name="Premium Package Selected")

    def review_premium_summary_elements(self):
        """Verify premium-summary actions visible after rating."""
        self.wait_for_loader_to_disappear()
        for locator in (
            self.rating_detail,
            self.premium_package_selected,
            self.re_rate,
            self.print_quote_letter,
        ):
            locator.scroll_into_view_if_needed()
            locator.wait_for(state="visible", timeout=15000)

    def click_issue(self):
        self.smart_click(self.request_issue)
