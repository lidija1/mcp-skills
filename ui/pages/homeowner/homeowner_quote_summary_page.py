import re

from ui.pages.common.base_page import BasePage


class HomeOwnerQuoteSummaryPage(BasePage):
    """Handles quote summary information for homeowners insurance."""

    def __init__(self, page):
        super().__init__(page)
        self.billing = page.get_by_role("combobox", name="Billing Method*")
        self.program=page.get_by_role("combobox", name="Program Type*")
        self.save_button = page.get_by_role("button", name="save changes")
        self.quote_name = page.get_by_role("textbox", name="Quote Name*")
        self.term = page.get_by_role("combobox", name="Term*")
        self.effective_date = page.get_by_role("combobox", name="Effective Date*")
        self.expiration_date = page.get_by_role("combobox", name="Expiration Date*")
        self.add_named_insured = page.get_by_role("button", name="Add")
        self.delete_named_insured = page.get_by_role("button", name="DELETE")
        self.prefix = page.get_by_role("combobox", name="Prefix")
        self.first_name = page.get_by_role("textbox", name="First Name*")
        self.middle_name = page.get_by_role("textbox", name="MI/Middle Name")
        self.last_name = page.get_by_role("textbox", name="Last Name*")
        self.suffix = page.get_by_role("combobox", name="Suffix")
        self.dob = page.get_by_role("combobox", name="DOB*")

    def summary_steps(self, data):
        """Perform quote summary steps."""
        self.set_program(data)
        self.set_billing(data)
        self.wait_for_loader_to_disappear()
        self.set_optional_identity_dropdowns(data)
        self.set_day_care(data)
        self.set_underground_oil_tank(data)
        self.set_residence_rented(data)
        self.residence_vacant(data)
        self.set_animals(data)
        self.click_save()
        self.click_city_info_link(data)

    def set_billing(self, data):
        """Set billing method."""
        self._open_and_select(self.billing, data["BillingMethod"])
        self.wait_for_loader_to_disappear()

    def set_program(self, data):
        """Set program type."""
        self._open_and_select(self.program, data["ProgramType"])
        self.wait_for_loader_to_disappear()

    def set_optional_identity_dropdowns(self, data):
        """Set quote-summary dropdowns that are optional for the base flow."""
        optional_dropdowns = (
            ("Term", self.term),
            ("Prefix", self.prefix),
            ("Suffix", self.suffix),
        )
        for key, locator in optional_dropdowns:
            value = data.get(key)
            if value:
                self._open_and_select(locator, value)
                self.wait_for_loader_to_disappear()

    def set_day_care(self, data):
        """Answer question about day care."""
        self.answer_question(
            "Is Child or Day Care run out",
            data["DayCare"]
        )

    def set_underground_oil_tank(self, data):
        """Answer question about underground oil tank."""
        self.answer_question(
            "Any underground oil or",
            data["UndergroundOil"]
        )

    def set_residence_rented(self, data):
        """Answer question about residence rented."""
        self.answer_question(
            "Is the residence rented more",
            data["ResidenceRented"]
        )

    def residence_vacant(self, data):
        """Answer question about residence vacant."""
        self.answer_question(
            "Is the residence vacant?",
            data["ResidenceVacant"]
        )

    def set_animals(self, data):
        """Answer question about animals."""
        self.answer_question(
            "Are there any animals or",
            data["Animals"]
        )

    def click_save(self):
        """Save changes."""
        self.smart_click(self.save_button)
        self.wait_for_loader_to_disappear()

    def click_city_info_link(self, data):
        """Navigate to HO information page."""
        city = data["City"]
        city_info_link = self.page.get_by_role("link", name=re.compile(city, re.IGNORECASE))
        self.smart_click(city_info_link)
        self.wait_for_loader_to_disappear()

    def review_additional_summary_elements(self, data):
        """Verify visible quote-summary elements that the main flow does not change."""
        self.wait_for_loader_to_disappear()
        for locator in (
            self.quote_name,
            self.term,
            self.effective_date,
            self.expiration_date,
            self.add_named_insured,
            self.delete_named_insured,
            self.prefix,
            self.first_name,
            self.middle_name,
            self.last_name,
            self.suffix,
            self.dob,
        ):
            locator.scroll_into_view_if_needed()
            locator.wait_for(state="visible", timeout=15000)
        assert data["FirstName"].lower() in self.first_name.input_value().lower()
        assert data["LastName"].lower() in self.last_name.input_value().lower()

    def assert_dropdown_options(self, expected):
        """Assert every configured Quote Summary dropdown option is available."""
        dropdowns = {
            "ProgramType": self.program,
            "BillingMethod": self.billing,
            "Term": self.term,
            "Prefix": self.prefix,
            "Suffix": self.suffix,
        }
        for key, locator in dropdowns.items():
            configured = expected.get(key)
            if configured is None:
                continue
            try:
                actual = self.get_extjs_options(locator)
            except Exception as exc:
                raise AssertionError(
                    f"Could not collect Quote Summary options for {key}: {exc}"
                ) from exc
            missing = [option for option in configured if option not in actual]
            assert not missing, f"{key} missing dropdown options: {missing}"

    def _open_and_select(self, locator, value):
        self.select_extjs_option(locator, value)
