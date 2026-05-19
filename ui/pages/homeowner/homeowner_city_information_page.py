import re

from ui.pages.common.base_page import BasePage


class HomeownerCityInformationPage(BasePage):
    """Handles the homeowner city information page."""

    def __init__(self, page):
        super().__init__(page)
        self.address_line_1 = page.get_by_role("textbox", name="Address Line 1")
        self.city = page.get_by_role("textbox", name="City")
        self.state = page.get_by_role("textbox", name="State")
        self.zip_code = page.get_by_role("textbox", name="ZIP")
        self.country = page.get_by_role("textbox", name="Country")
        self.save_button = page.get_by_role("button", name="save changes")

    def review_city_information_elements(self, data):
        """Verify city information display fields discovered in the live homeowner flow."""
        self.wait_for_loader_to_disappear()
        for locator in (
            self.address_line_1,
            self.city,
            self.state,
            self.zip_code,
            self.country,
        ):
            locator.scroll_into_view_if_needed()
            locator.wait_for(state="visible", timeout=15000)
        assert data["City"].lower() in self.page.get_by_text(data["City"]).first.inner_text().lower()

    def click_save(self):
        self.smart_click(self.save_button)
        self.wait_for_loader_to_disappear()

    def click_homeowners_link(self, data):
        """Return to the homeowner location coverage page from city information."""
        program = data["Program"]
        program_link = self.page.get_by_role("link", name=re.compile(program, re.IGNORECASE))
        self.smart_click(program_link)
        self.wait_for_loader_to_disappear()
