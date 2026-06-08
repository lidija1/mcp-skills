import allure

from ui.pages.common.base_page import BasePage


class CyberPolicyInformationPage(BasePage):
    """Cyber policy information, coverage, eligibility, and rating controls."""

    def __init__(self, page):
        super().__init__(page)

        self.quote_name = page.get_by_role("textbox", name="Quote Name")
        self.effective_date = page.get_by_role(
            "combobox", name="Effective Date*"
        ).or_(page.locator(
            '[osviewid="PAI_1513848_OT_3381148_OI_1_BI_1402548_CI_17477148"]'
        ))
        self.expiration_date = page.get_by_role(
            "combobox", name="Expiration Date*"
        ).or_(page.locator(
            '[osviewid="PAI_1513848_OT_3381148_OI_1_BI_1402548_CI_17477248"]'
        ))
        self.billing_method = page.get_by_role(
            "combobox", name="Billing Method*"
        ).or_(page.locator("li").filter(has_text="Direct Billed"))
        self.business_start_date = page.get_by_role(
            "textbox", name="Business Start Date*"
        ).or_(page.locator(
            '[osviewid="PAI_1513848_OT_3381148_OI_1_BI_1403248_CI_17481348"]'
        ))
        self.nature_of_business = page.get_by_role(
            "combobox", name="Nature of Business*"
        ).or_(page.locator(
            '[osviewid="PAI_1513848_OT_3381148_OI_1_BI_1403248_CI_17479348"]'
        ))
        self.number_of_employees = page.get_by_role(
            "textbox", name="Total Number of Employees*"
        ).or_(page.locator(
            '[osviewid="PAI_1513848_OT_3381148_OI_1_BI_1403248_CI_17479248"]'
        ))
        self.percentage_of_online_sale = page.get_by_role(
            "textbox", name="Percentage Annual Online Sales*"
        ).or_(page.locator(
            '[osviewid="PAI_1513848_OT_3381148_OI_1_BI_1403248_CI_17479448"]'
        ))
        self.aggregate_limit = page.get_by_role(
            "combobox", name="Aggregate Limit*"
        ).or_(page.locator(
            '[osviewid="PAI_1513848_OT_3381548_OI_1_BI_1403348_CI_17479548"]'
        ))
        self.per_claim_deductible = page.get_by_role(
            "combobox", name="Per Claim Deductible*"
        ).or_(page.locator(
            '[osviewid="PAI_1513848_OT_3381548_OI_1_BI_1403348_CI_17480448"]'
        ))
        self.per_claim_limit = page.get_by_role(
            "combobox", name="Per Claim Limit*"
        ).or_(page.locator(
            '[osviewid="PAI_1513848_OT_3381548_OI_1_BI_1403348_CI_17480348"]'
        ))
        self.business_interruption = page.get_by_role(
            "textbox", name="Business Interruption"
        ).or_(page.locator(
            '[osviewid="PAI_1513848_OT_3381648_OI_1_BI_1403448_CI_17480548"]'
        ))
        self.cyber_extortion = page.get_by_role(
            "textbox", name="Cyber Extortion"
        ).or_(page.locator(
            '[osviewid="PAI_1513848_OT_3381648_OI_1_BI_1403448_CI_17480648"]'
        ))
        self.common_eligibility_1 = page.get_by_role(
            "combobox",
            name="Does the company conduct cyber security training for its employees?*",
        ).or_(page.locator(
            '[osviewid="PAI_1513848_OT_3391746_OI_1_BI_1403548_CI_17480948"]'
        ))
        self.common_eligibility_2 = page.get_by_role(
            "combobox",
            name="Has the Company experienced any of the following situations within the last three years?*",
        ).or_(page.locator(
            '[osviewid="PAI_1513848_OT_3391746_OI_1_BI_1403548_CI_17481048"]'
        ))
        self.common_eligibility_3 = page.get_by_role(
            "combobox",
            name="Does the company have cyber security regulations in place as per the jurisdictional guidelines?*",
        ).or_(page.locator(
            '[osviewid="PAI_1513848_OT_3391746_OI_1_BI_1403548_CI_17481248"]'
        ))

        self.save_changes = page.get_by_role("button", name="save changes")
        self.exit = page.get_by_role("button", name="exit")
        self.rate_quote = page.get_by_role("button", name=">>> rate quote")

    @allure.step("Fill Cyber policy information")
    def fill_policy_information(self, data):
        self._select_billing_method(data["BillingMethod"])
        self.smart_fill(self.business_start_date, data["BusinessStartDate"])
        self.select_extjs_option(self.nature_of_business, data["NatureOfBusiness"])
        self.smart_fill(self.number_of_employees, data["NumberOfEmployees"])
        self.smart_fill(
            self.percentage_of_online_sale,
            data["PercentageOfOnlineSale"],
        )
        self.select_extjs_option(self.aggregate_limit, data["AggregateLimit"])
        self.select_extjs_option(
            self.per_claim_deductible,
            data["PerClaimDeductible"],
        )
        self.select_extjs_option(self.per_claim_limit, data["PerClaimLimit"])
        self._fill_optional_coverage(
            self.business_interruption,
            data.get("BusinessInterruption"),
        )
        self._fill_optional_coverage(
            self.cyber_extortion,
            data.get("CyberExtortion"),
        )
        self.select_extjs_option(
            self.common_eligibility_1,
            data["CommonEligibility1"],
        )
        self.select_extjs_option(
            self.common_eligibility_2,
            data["CommonEligibility2"],
        )
        self.select_extjs_option(
            self.common_eligibility_3,
            data["CommonEligibility3"],
        )
        self.with_optional_oneshield_response(
            lambda: self.smart_click(self.save_changes)
        )
        self.wait_for_app_ready()

    @allure.step("Review discovered Cyber policy information controls")
    def review_discovered_controls(self):
        controls = (
            self.quote_name,
            self.effective_date,
            self.expiration_date,
            self.business_interruption,
            self.cyber_extortion,
            self.exit,
        )
        for control in controls:
            control.wait_for(state="visible", timeout=15000)

    @allure.step("Rate Cyber quote")
    def click_rate_quote(self):
        self.with_optional_oneshield_response(
            lambda: self.smart_click(self.rate_quote)
        )
        self.wait_for_app_ready()

    def _select_billing_method(self, value):
        if self.billing_method.get_attribute("role") == "combobox":
            self.select_extjs_option(self.billing_method, value)
            return
        self.smart_click(self.billing_method)
        self.wait_for_app_ready()

    def _fill_optional_coverage(self, locator, value):
        if value not in (None, ""):
            self.smart_fill(locator, str(value), verify_fill=False)
