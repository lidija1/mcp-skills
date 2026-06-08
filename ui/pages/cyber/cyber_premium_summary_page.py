from ui.pages.common.base_page import BasePage


class CyberPremiumSummaryPage(BasePage):
    """Cyber premium summary actions after rating."""

    def __init__(self, page):
        super().__init__(page)
        self.request_issue = page.get_by_role("button", name=">>> request issue")

    def click_request_issue(self):
        self.with_optional_oneshield_response(
            lambda: self.smart_click(self.request_issue)
        )
        self.wait_for_app_ready()
