from ui.pages.common.base_page import BasePage


class HomeownerBindInformationPage(BasePage):
    """Handles homeowner bind information and rating navigation."""

    def __init__(self, page):
        super().__init__(page)
        self.save_button = page.get_by_role("button", name="save changes")
        self.rate_quote = page.get_by_role("button", name=">>> rate quote")

    def set_existing_client(self, data):
        self.answer_question("Existing Agency Client?", data["ExistingClient"])

    def set_refused_in_the_past(self, data):
        self.answer_question(
            "Has any company cancelled or refused to insure in the past 3 years?",
            data["Refused"],
        )

    def set_denied_coverage(self, data):
        self.answer_question(
            "Has coverage been non-renewed or Declined?",
            data["Declined"],
        )

    def click_save(self):
        self.smart_click(self.save_button)
        self.wait_for_loader_to_disappear()

    def click_rate_quote(self):
        self.smart_click(self.rate_quote)
        self.wait_for_loader_to_disappear()
