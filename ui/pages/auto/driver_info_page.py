import re

import allure

from ui.pages.common.base_page import BasePage


class DriverInfoPage(BasePage):
    """Handles driver information for auto insurance quotes."""
    
    def __init__(self, page):
        super().__init__(page)

        def field_by_label(label, role):
            return page.get_by_text(label, exact=True).locator(
                "xpath=ancestor::div[contains(@class,'x-field')][1]"
            ).get_by_role(role)

        self.gender = page.get_by_role("combobox", name="Gender*")
        self.prefix = page.get_by_role("combobox", name="Prefix")
        self.middle_name = page.get_by_role("textbox", name="MI/Middle Name")
        self.suffix = page.get_by_role("combobox", name="Suffix")
        self.relationship_to_insured = page.get_by_role(
            "combobox", name="Relationship to Insured"
        )
        self.ssn = page.get_by_role("textbox", name="SSN")
        self.marital_status = page.get_by_role("combobox", name="Marital Status*")
        self.driver_status = page.get_by_role("combobox", name="Driver Status*")
        self.employment = page.get_by_role("combobox", name="Employment Category")
        self.occupation = page.get_by_role("combobox", name="Occupation")
        self.licence = page.get_by_role("combobox", name="License Status*")
        self.country_of_issue = field_by_label("Country of Issue", "combobox")
        self.license_state = field_by_label("License State/Province", "combobox")
        self.license_year = field_by_label("License Year", "textbox")
        self.license_number = field_by_label("License Number", "textbox")
        self.licensed_another_state = field_by_label(
            "Have you been licensed in another state in the last three years?",
            "radiogroup",
        )
        self.sr22_filing_state = page.get_by_role(
            "combobox",
            name=re.compile(r"SR-?22 Filing State", re.I),
        )
        self.save_button = page.get_by_role("button", name="save changes")
        self.tree_vehicle_info = page.get_by_role("link", name="Vehicle_1")

    def fill_driver_info(self, data):
        """Fill driver information form."""
        self.fill_optional_driver_info(data)
        self.set_gender(data)
        self.set_marital_status(data)
        self.set_driver_status(data)
        self.set_employment_category(data)
        self.set_occupation(data)
        self.set_license_status(data)
        self.set_sr22_required(data)
        self.set_defensive_driver(data)
        self.click_save()
        self.click_vehicle_info_link()

    @allure.step("Fill optional driver fields")
    def fill_optional_driver_info(self, data):
        """Fill configured optional identity and license fields."""
        self._set_optional_combo(self.prefix, data.get("Prefix"))
        self._set_optional_text(self.middle_name, data.get("MiddleName"))
        self._set_optional_combo(self.suffix, data.get("Suffix"))
        self._set_optional_combo(
            self.relationship_to_insured,
            data.get("RelationshipToInsured"),
        )
        self._set_optional_text(self.ssn, data.get("SSN"), type_text=True)
        self._set_optional_combo(
            self.country_of_issue,
            data.get("CountryOfIssue"),
        )
        self._set_optional_combo(self.license_state, data.get("LicenseState"))
        self._set_optional_text(self.license_year, data.get("LicenseYear"))
        self._set_optional_text(self.license_number, data.get("LicenseNumber"))
        self.set_licensed_another_state(data.get("LicensedAnotherState"))

    def _set_optional_combo(self, locator, value):
        if not value:
            return
        try:
            locator.first.wait_for(state="visible", timeout=2_000)
        except Exception:
            self.logger.info("Configured optional combobox is not visible; skipping.")
            return
        expected = str(value).strip()
        if locator.first.input_value().strip() == expected:
            return
        self.select_extjs_option(locator.first, expected)
        self.wait_for_app_ready()

    def _set_optional_text(self, locator, value, type_text=False):
        if not value:
            return
        try:
            locator.first.wait_for(state="visible", timeout=2_000)
        except Exception:
            self.logger.info("Configured optional text field is not visible; skipping.")
            return
        if type_text:
            self.smart_type(locator.first, str(value))
        else:
            self.smart_fill(locator.first, str(value))

    @allure.step("Set licensed in another state: {answer}")
    def set_licensed_another_state(self, answer):
        if not answer:
            return
        group = self.licensed_another_state
        try:
            group.wait_for(state="visible", timeout=2_000)
        except Exception:
            self.logger.info(
                "Licensed-in-another-state question is not visible; skipping."
            )
            return
        radio = group.get_by_label(
            re.compile(f"^{re.escape(str(answer))}$", re.I)
        )
        radio.dispatch_event("click")

    def set_gender(self, data):
        """Set gender field."""
        self.smart_fill(self.gender, data["Gender"])

    def set_marital_status(self, data):
        """Set marital status field."""
        self.smart_fill(self.marital_status, data["MaritalStatus"])

    def set_driver_status(self, data):
        """Set driver status field."""
        self.smart_fill(self.driver_status, data["DriverStatus"])

    def set_employment_category(self, data):
        """Set employment category field."""
        self.smart_fill(self.employment, data["EmploymentCategory"])

    def set_occupation(self, data):
        """Set occupation field."""
        self.smart_fill(self.occupation, data["Occupation"])

    def set_license_status(self, data):
        """Set license status field."""
        self.smart_fill(self.licence, data["LicenseStatus"])

    def set_sr22_required(self, data):
        """Answer SR22 required question."""
        answer = data.get("SR22", "No")
        self.with_optional_oneshield_response(
            lambda: self.answer_question("Certificate of Insurance Required?", answer),
            url_parts=["FieldProcessorServlet"],
        )
        self.wait_for_app_ready()
        if str(answer).strip().lower() == "yes":
            self.set_sr22_filing_state(data)

    def set_sr22_filing_state(self, data):
        """Set the conditional SR-22 Filing State field."""
        filing_state = (
            data.get("SR22FilingState")
            or data.get("SR-22 Filing State")
            or data.get("State")
            or "Massachusetts"
        )
        self.sr22_filing_state.first.wait_for(state="visible", timeout=10_000)
        self.select_extjs_option(
            self.sr22_filing_state.first,
            filing_state,
            wait_for_response=True,
            url_parts=["FieldProcessorServlet"],
        )
        self.wait_for_app_ready()

    def set_defensive_driver(self, data):
        """Answer defensive driver course question if present on the page."""
        group = self.page.get_by_role(
            "radiogroup",
            name=re.compile("Has a Defensive Driver Course been completed in last 3 years", re.I)
        )
        if group.is_visible(timeout=2000):
            answer = data.get("DefensiveDriver", "No")
            radio = group.get_by_label(re.compile(f"^{answer}$", re.I))
            radio.dispatch_event("click")

    def click_save(self):
        """Click save button."""
        self.smart_click(self.save_button)

    def click_vehicle_info_link(self):
        """Navigate to vehicle information page."""
        self.smart_click(self.tree_vehicle_info)
