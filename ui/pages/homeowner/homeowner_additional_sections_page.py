import allure

from ui.pages.common.base_page import BasePage


class HomeownerAdditionalSectionsPage(BasePage):
    """Handles Homeowner optional coverage and Add-driven child flows."""

    def __init__(self, page):
        super().__init__(page)
        self.optional_coverages_link = page.get_by_role(
            "link", name="Optional Coverages", exact=True
        )
        self.reinsurance_link = page.get_by_role(
            "link", name="Reinsurance", exact=True
        )
        self.inspection_link = page.get_by_role(
            "link", name="Inspection", exact=True
        )
        self.manuscripts_link = page.get_by_role(
            "link", name="Manuscripts", exact=True
        )
        self.additional_interests_link = page.get_by_role(
            "link", name="Additional Interests_1", exact=True
        )
        self.add_button = page.get_by_role("button", name="Add", exact=True)

        self.new_reinsurance_link = page.get_by_role(
            "link", name="New Reinsurance", exact=True
        )
        self.gross_premium_risk = page.get_by_role(
            "textbox", name="Gross Premium (Risk)"
        )
        self.gross_limit = page.get_by_role("combobox", name="Gross Limit")
        self.reinsurance_type = page.get_by_role("combobox", name="Type*")

        self.inspection_type = page.get_by_role(
            "combobox", name="Inspection Type*"
        )
        self.request_date_label = page.get_by_text(
            "Request Date", exact=True
        )
        self.inspection_company = page.get_by_role(
            "combobox", name="Inspection Company*"
        )
        self.inspection_date_label = page.get_by_text(
            "Inspection Date", exact=True
        )
        self.inspector = page.get_by_role("combobox", name="Inspector")
        self.inspection_completed = page.get_by_role(
            "combobox", name="Inspection Completed?*"
        )
        self.request_details = page.get_by_role(
            "textbox", name="Request Details*"
        )
        self.inspector_comments_label = page.get_by_text(
            "Inspector Comments", exact=True
        )

        self.search_manuscript = page.get_by_role(
            "textbox", name="Search Manuscript"
        )
        self.manuscript = page.get_by_role("combobox", name="Manuscript*")

    @allure.step("Exercise configured Homeowner optional coverage checkboxes")
    def exercise_optional_coverages(self, data):
        self._click_and_wait(self.optional_coverages_link, wait_for_response=True)
        for label in data["OptionalCoverageSelections"]:
            checkbox = self.page.get_by_role("checkbox", name=label, exact=True)
            checkbox.wait_for(state="visible", timeout=15000)
            if not checkbox.is_checked():
                checkbox.dispatch_event("click")
            assert checkbox.is_checked(), f"Optional coverage was not checked: {label}"

    @allure.step("Exercise Homeowner Reinsurance Add flow")
    def exercise_reinsurance(self, data):
        self._click_and_wait(self.reinsurance_link, wait_for_response=True)
        self._click_and_wait(self.add_button.first, wait_for_response=True)
        self._click_and_wait(self.new_reinsurance_link, wait_for_response=True)
        for locator in (
            self.gross_premium_risk,
            self.gross_limit,
            self.reinsurance_type,
        ):
            locator.wait_for(state="visible", timeout=15000)
        assert not self.gross_premium_risk.is_editable()
        assert not self.gross_limit.is_editable()
        expected = data["ExpectedReinsuranceTypes"]
        actual = self.get_extjs_options(self.reinsurance_type)
        assert not [value for value in expected if value not in actual]
        self.select_extjs_option(self.reinsurance_type, data["ReinsuranceType"])

    @allure.step("Exercise Homeowner Inspection Add flow")
    def exercise_inspection(self, data):
        self._click_and_wait(self.inspection_link, wait_for_response=True)
        initial_adds = self.page.get_by_role("button", name="Add", exact=True)
        assert initial_adds.count() >= 1
        self._click_and_wait(initial_adds.first, wait_for_response=True)
        for locator in (
            self.inspection_type,
            self.request_date_label,
            self.inspection_company,
            self.inspection_date_label,
            self.inspection_completed,
            self.request_details,
            self.inspector_comments_label,
        ):
            locator.wait_for(state="visible", timeout=15000)
        self.select_extjs_option(self.inspection_type, data["InspectionType"])
        self.select_extjs_option(
            self.inspection_company, data["InspectionCompany"]
        )
        self.select_extjs_option(
            self.inspection_completed, data["InspectionCompleted"]
        )
        self.smart_fill(self.request_details, data["InspectionRequestDetails"])

    @allure.step("Exercise Homeowner Manuscripts Add flow")
    def exercise_manuscript(self, data):
        self._click_and_wait(self.manuscripts_link, wait_for_response=True)
        self._click_and_wait(self.add_button.first, wait_for_response=True)
        self.search_manuscript.wait_for(state="visible", timeout=15000)
        self.manuscript.wait_for(state="visible", timeout=15000)
        self.smart_fill(self.search_manuscript, data["ManuscriptSearch"])
        self.get_extjs_options(self.manuscript)

    @allure.step("Review Homeowner Additional Interests Add actions")
    def exercise_additional_interests(self, data):
        self._click_and_wait(
            self.additional_interests_link,
            wait_for_response=True,
        )
        actions = {
            "Add": self.page.get_by_label("Additional Insured").get_by_role(
                "button", name="Add", exact=True
            ),
            "Add New Entity": self.page.get_by_label(
                "Additional Insured"
            ).get_by_role("button", name="Add New Entity", exact=True),
            "Add New Financial Service Provider": self.page.get_by_label(
                "Additional Interest"
            ).get_by_role(
                "button",
                name="Add New Financial Service Provider",
                exact=True,
            ),
        }
        for action in data["ExpectedAdditionalInterestActions"]:
            button = actions[action]
            button.wait_for(state="visible", timeout=15000)
