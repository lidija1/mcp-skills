import allure

from ui.pages.common.base_page import BasePage


class CyberInspectionPage(BasePage):
    """Cyber inspection request and inspection assignment controls."""

    def __init__(self, page):
        super().__init__(page)
        self.tree_link = page.get_by_role("link", name="Inspection", exact=True)
        self.add_buttons = page.get_by_role("button", name="Add", exact=True)
        self.order_inspection = page.get_by_role(
            "button", name="order inspection", exact=True
        )

        self.inspection_type = page.get_by_role(
            "combobox", name="Inspection Type*"
        ).or_(page.locator(
            '[osviewid="PAI_625646_OT_2365076_OI_1_BI_763276_CI_11648776"]'
        ))
        self.request_date = page.get_by_role(
            "combobox", name="Request Date*"
        ).or_(page.locator(
            '[osviewid="PAI_625646_OT_2365076_OI_1_BI_763276_CI_11649276"]'
        ))
        self.inspection_company = page.get_by_role(
            "combobox", name="Inspection Company*"
        ).or_(page.locator(
            '[osviewid="PAI_625646_OT_2365076_OI_1_BI_763276_CI_11648476"]'
        ))
        self.inspection_date = page.get_by_role(
            "combobox", name="Inspection Date*"
        ).or_(page.locator(
            '[osviewid="PAI_625646_OT_2365076_OI_1_BI_763276_CI_11664376"]'
        ))
        self.request_inspector = page.locator(
            '[osviewid="PAI_625646_OT_2365076_OI_1_BI_763276_CI_11648576"]'
        )
        self.inspection_completed = page.get_by_role(
            "combobox", name="Inspection Completed?*"
        ).or_(page.locator(
            '[osviewid="PAI_625646_OT_2365076_OI_1_BI_763276_CI_11649376"]'
        ))
        self.request_details = page.get_by_role(
            "textbox", name="Request Details*"
        ).or_(page.locator(
            '[osviewid="PAI_625646_OT_2365076_OI_1_BI_763276_CI_11648976"]'
        ))
        self.inspector_comments = page.get_by_role(
            "textbox", name="Inspector Comments*"
        ).or_(page.locator(
            '[osviewid="PAI_625646_OT_2365076_OI_1_BI_763276_CI_11648676"]'
        ))

        self.assignment_company = page.locator(
            '[osviewid="PAI_625646_OT_2360546_OI_1_BI_736546_CI_11522746"]'
        )
        self.assignment_inspector = page.locator(
            '[osviewid="PAI_625646_OT_2360546_OI_1_BI_736546_CI_11522946"]'
        )
        self.assignment_comments = page.get_by_role(
            "textbox", name="Inspection Comments", exact=True
        ).or_(page.locator(
            '[osviewid="PAI_625646_OT_2360546_OI_1_BI_736546_CI_11521346"]'
        ))

    @allure.step("Open and review Cyber inspection request fields")
    def review_inspection_request_fields(self):
        self._open_inspection_list()
        self._click_initial_add(0)
        for control in (
            self.inspection_type,
            self.request_date,
            self.inspection_company,
            self.inspection_date,
            self.request_inspector,
            self.inspection_completed,
            self.request_details,
            self.inspector_comments,
        ):
            control.wait_for(state="visible", timeout=15000)

    @allure.step("Open and review Cyber inspection assignment fields")
    def review_inspection_assignment_fields(self):
        self._open_inspection_list()
        self._click_initial_add(1)
        for control in (
            self.assignment_company,
            self.assignment_inspector,
            self.assignment_comments,
            self.order_inspection,
        ):
            control.wait_for(state="visible", timeout=15000)

    @allure.step("Fill Cyber inspection request fields without saving")
    def fill_inspection_request_fields(self, data):
        self.review_inspection_request_fields()
        self.select_extjs_option(
            self.inspection_type,
            data["InspectionType"],
        )
        self._assert_read_only(self.request_date, "Request Date")
        self.select_extjs_option(
            self.inspection_company,
            data["InspectionCompany"],
        )
        self._assert_read_only(self.inspection_date, "Inspection Date")
        self.select_extjs_option(
            self.inspection_completed,
            data["InspectionCompleted"],
        )
        self.smart_fill(
            self.request_details,
            data["InspectionRequestDetails"],
        )
        self._assert_read_only(
            self.inspector_comments,
            "Inspector Comments",
        )

    @allure.step("Fill Cyber inspection assignment comments without saving")
    def fill_inspection_assignment_fields(self, data):
        self.review_inspection_assignment_fields()
        self.smart_fill(
            self.assignment_comments,
            data["InspectionAssignmentComments"],
        )

    def _open_inspection_list(self):
        self._click_and_wait(self.tree_link, wait_for_response=True)

    def _click_initial_add(self, index):
        count = self.add_buttons.count()
        if count != 2:
            raise AssertionError(
                f"Expected two Inspection Add buttons, found {count}"
            )
        self._click_and_wait(
            self.add_buttons.nth(index),
            wait_for_response=True,
        )

    @staticmethod
    def _assert_read_only(locator, label):
        if locator.is_editable():
            raise AssertionError(f"Expected {label} to be read-only")
