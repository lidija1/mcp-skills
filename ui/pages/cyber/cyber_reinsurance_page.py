import allure

from ui.pages.common.base_page import BasePage


class CyberReinsurancePage(BasePage):
    """Cyber quote reinsurance list and new reinsurance detail form."""

    def __init__(self, page):
        super().__init__(page)
        self.tree_link = page.get_by_role("link", name="Reinsurance", exact=True)
        self.add_button = page.get_by_role("button", name="Add", exact=True)
        self.new_reinsurance_link = page.get_by_role(
            "link", name="New Reinsurance", exact=True
        )
        self.gross_premium_risk = page.get_by_role(
            "textbox", name="Gross Premium (Risk)"
        ).or_(page.locator(
            '[osviewid="PAI_492405_OT_2288705_OI_1_BI_902546_CI_14148146"]'
        ))
        self.gross_limit = page.get_by_role(
            "combobox", name="Gross Limit"
        ).or_(page.locator(
            '[osviewid="PAI_492405_OT_2288705_OI_1_BI_902546_CI_14084946"]'
        ))
        self.reinsurance_type = page.get_by_role(
            "combobox", name="Type*"
        ).or_(page.locator(
            '[osviewid="PAI_492405_OT_2288705_OI_1_BI_560505_CI_8548805"]'
        ))

    @allure.step("Open and review new Cyber reinsurance fields")
    def review_new_reinsurance_fields(self):
        self._click_and_wait(self.tree_link, wait_for_response=True)
        self._click_and_wait(self.add_button, wait_for_response=True)
        self._click_and_wait(self.new_reinsurance_link, wait_for_response=True)
        for control in (
            self.gross_premium_risk,
            self.gross_limit,
            self.reinsurance_type,
        ):
            control.wait_for(state="visible", timeout=15000)

    @allure.step("Fill Cyber reinsurance fields without saving")
    def fill_reinsurance_fields(self, data):
        self.review_new_reinsurance_fields()
        self._assert_read_only(
            self.gross_premium_risk,
            "Gross Premium (Risk)",
        )
        self._assert_read_only(self.gross_limit, "Gross Limit")
        reinsurance_type = data.get("ReinsuranceType")
        if reinsurance_type:
            self.select_extjs_option(
                self.reinsurance_type,
                reinsurance_type,
            )

    @staticmethod
    def _assert_read_only(locator, label):
        if locator.is_editable():
            raise AssertionError(f"Expected {label} to be read-only")
