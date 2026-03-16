import re

from ui.pages.common.base_page import BasePage


class HomeownerCoveragePage(BasePage):

    def __init__(self, page):
        super().__init__(page)

        self.policy_coverage = page.get_by_role("combobox", name="Policy Coverage Option")
        self.residence_type = page.get_by_role("combobox", name="Residence Type")
        self.replacement_cost = page.get_by_role("textbox", name="Replacement Cost")
        self.contents = page.get_by_role("textbox", name="Contents")
        self.perils = page.get_by_role("combobox", name="All Perils Deductible")
        self.windstorm = page.get_by_role("combobox", name="Windstorm or Hail")
        self.liability = page.get_by_role("combobox", name="Liability")
        self.medical = page.get_by_role("combobox", name="Medical Payments")
        self.year_built = page.get_by_role("textbox", name="Year Built")
        self.construction = page.get_by_role("combobox", name="Construction Type")
        self.roof_type = page.get_by_role("combobox", name="Roof Type")
        self.save = page.get_by_role("button", name="save changes")
        self.bind_info = page.get_by_role("link", name="Bind Information")
        self.rate_quote = page.get_by_role("button", name=">>> rate quote")

    def coverage_steps(self, data):
        self.set_residency(data)
        self.set_coverage(data)
        self.wait_for_loader_to_disappear()
        self.set_replacement(data)
        # self.set_contents(data)
        self.set_perils(data)
        self.set_windstorm(data)
        self.set_liability(data)
        self.set_medical(data)
        self.set_year_built(data)
        self.set_construction(data)
        self.set_roof_type(data)
        self.set_under_construction(data)
        self.set_lived_here(data)
        self.set_loses(data)
        self.click_save()
        self.click_bind_info()
        self.set_existing_client(data)
        self.set_refused_in_the_past(data)
        self.set_denied_coverage(data)
        self.click_save()
        self.click_rate_quote()

    def set_coverage(self, data):
        self.smart_fill(self.policy_coverage, data["PolicyCoverageOption"])
        # self.policy_coverage.fill(data["PolicyCoverageOption"])

    def wait_for_loader_to_disappear(self):
        self.spinner_wait("#ajax-sub-pre-loading")

    def set_residency(self, data):
        self.smart_fill(self.residence_type, data["ResidenceType"])
        self.page.expect_response("**/FieldProcessorServlet*")

    def set_replacement(self, data):
        self.smart_fill(self.replacement_cost, data["ReplacementCost"])
        self.page.expect_response("**/FieldProcessorServlet*")

    # def set_contents(self, data):
    #     self.contents.fill(data["Contents"])

    def set_perils(self, data):
        self.smart_fill(self.perils, data["AllPerilsDeductable"])

    def set_windstorm(self, data):
        self.smart_fill(self.windstorm, data["WindstormDeductable"])

    def set_liability(self, data):
        self.smart_fill(self.liability, data["Liability"])

    def set_medical(self, data):
        self.smart_fill(self.medical, data["MedPayments"])

    def set_year_built(self, data):
        self.smart_type(self.year_built, data["YearBuilt"])
        self.page.expect_response("**/FieldProcessorServlet*")

    def set_construction(self, data):
        self.smart_fill(self.construction, data["ConstructionType"])

    def set_roof_type(self, data):
        self.smart_type(self.roof_type, data["RoofType"])

    def set_under_construction(self, data):
        self.answer_question(
            "Is the residence under construction or major renovation?",
            data["Renovation"]
        )

    def set_lived_here(self, data):
        self.answer_question(
            "Has the customer lived at this location for less than 3 years?",
            data["LivedHere"]
        )

    def set_loses(self, data):
        value = data["Loses"]
        self.smart_click(
            self.page.locator(
                f"//div[text()='Any losses in the last three years?']/../../../..//label[text()='{value}']/../span"
            )
        )

    def click_save(self):
        self.smart_click(self.save)

    def click_bind_info(self):
        self.smart_click(self.bind_info)

    def set_existing_client(self, data):
        self.answer_question(
            "Existing Agency Client?",
            data["ExistingClient"]
        )

    def set_refused_in_the_past(self, data):
        self.answer_question(
            "Has any company cancelled or refused to insure in the past 3 years?",
            data["Refused"]
        )

    def set_denied_coverage(self, data):
        self.answer_question(
            "Has coverage been non-renewed or Declined?",
            data["Declined"]
        )

    def click_rate_quote(self):
        self.smart_click(self.rate_quote)
