import re

from ui.pages.common.base_page import BasePage


class GeneralLiabilityLiabilityLocationListPage(BasePage):
    """General Liability liability location list page."""

    def __init__(self, page):
        super().__init__(page)

        self.location_save_button = page.get_by_role("button", name="save changes")

    def liability_location_list_steps(self, data):
        self.open_liability_location_list(data)
        self.click_location_save()

    def open_liability_location_list(self, data):
        liability_state = self.page.get_by_role(
            "link",
            name=re.compile(re.escape(data["LiabilityState"]), re.I),
        )
        self.smart_click(liability_state)
        self.wait_for_loader_to_disappear()

    def click_location_save(self):
        self._click_and_wait(self.location_save_button, wait_for_response=True)

