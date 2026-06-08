from ui.pages.common.base_page import BasePage


class GeneralLiabilityOptionalCoveragesPage(BasePage):
    """Supporting fields created by selected General Liability endorsements."""

    def __init__(self, page):
        super().__init__(page)

        self.optional_coverages_link = page.get_by_role(
            "link", name="GL Optional Coverages", exact=True
        )
        self.auto_territory_code = page.get_by_role(
            "combobox", name="Auto Territory Code*"
        )
        self.non_owned_auto_territory = page.locator(
            '[osviewid="PAI_1419346_OT_3388246_OI_1_BI_1360746_CI_17672246"]'
        )
        self.hired_auto_limit = page.get_by_role(
            "combobox", name="Hired Auto Limit*"
        )
        self.estimated_cost_of_hire = page.get_by_role(
            "combobox", name="Estimated Cost of Hire*"
        )
        self.non_owned_auto_limit = page.get_by_role(
            "combobox", name="Non-Owned Auto Limit*"
        )
        self.number_of_employees = page.get_by_role(
            "textbox", name="Number of Employees Covered*"
        )
        self.employee_benefits_amount = page.get_by_role(
            "combobox", name="Amount of Insurance*"
        )
        self.employee_benefits_deductible = page.get_by_role(
            "combobox", name="Deductible Per Claim*"
        )
        self.liquor_classification = page.get_by_role(
            "combobox", name="Liquor Classification*"
        )
        self.liquor_occurrence_limit = page.get_by_role(
            "combobox", name="Liquor Occurrence Limit*"
        )
        self.liquor_gross_sales = page.get_by_role(
            "textbox", name="Liquor Gross Sales*"
        )
        self.liquor_rate = page.get_by_role(
            "textbox", name='Liquor Liability "A" Rate*'
        )
        self.liquor_aggregate_limit = page.get_by_role(
            "combobox", name="Liquor Aggregate Limit*"
        )
        self.save_button = page.get_by_role("button", name="save changes")

    def complete_if_required(self, data):
        active_endorsements = self._active_endorsements(data)
        if not active_endorsements:
            return

        if not self.optional_coverages_link.is_visible(timeout=3000):
            return

        self._click_and_wait(self.optional_coverages_link, wait_for_response=True)

        supported = {
            "HiredAutoCoverage",
            "NonOwnedAutoCoverage",
            "EmployeeBenefitsCoverage",
            "LiquorLiabilityCoverage",
        }
        unsupported = [key for key in active_endorsements if key not in supported]
        if unsupported:
            raise AssertionError(
                "GL optional coverage handler is not implemented for: "
                + ", ".join(unsupported)
                + f". Visible required controls: {self._visible_required_controls()}"
            )

        if data.get("HiredAutoCoverage") is True:
            self._complete_hired_auto(data)
        if data.get("NonOwnedAutoCoverage") is True:
            self._complete_non_owned_auto(data)
        if data.get("EmployeeBenefitsCoverage") is True:
            self._complete_employee_benefits(data)
        if data.get("LiquorLiabilityCoverage") is True:
            self._complete_liquor_liability(data)

        self._click_and_wait(self.save_button, wait_for_response=True)

    def _complete_hired_auto(self, data):
        self._select_required_option(
            self.auto_territory_code.first, data.get("AutoTerritoryCode")
        )
        self._select_required_option(
            self.hired_auto_limit, data.get("HiredAutoLimit")
        )
        self._select_required_option(
            self.estimated_cost_of_hire, data.get("EstimatedCostOfHire")
        )

    def _complete_non_owned_auto(self, data):
        self._select_required_option(
            self.non_owned_auto_territory, data.get("AutoTerritoryCode")
        )
        self._select_required_option(
            self.non_owned_auto_limit, data.get("NonOwnedAutoLimit")
        )
        self._fill_required_text(
            self.number_of_employees.last, data.get("NonOwnedEmployeesCovered")
        )

    def _complete_employee_benefits(self, data):
        self._select_required_option(
            self.employee_benefits_amount, data.get("EmployeeBenefitsAmount")
        )
        self._select_required_option(
            self.employee_benefits_deductible,
            data.get("EmployeeBenefitsDeductible"),
        )
        self._fill_required_text(
            self.number_of_employees.first,
            data.get("EmployeeBenefitsEmployeesCovered"),
        )

    def _complete_liquor_liability(self, data):
        self._select_required_option(
            self.liquor_classification, data.get("LiquorClassification")
        )
        self._select_required_option(
            self.liquor_occurrence_limit, data.get("LiquorOccurrenceLimit")
        )
        self._fill_required_text(
            self.liquor_gross_sales, data.get("LiquorGrossSales")
        )
        self._fill_required_text(self.liquor_rate, data.get("LiquorRate"))
        self._select_required_option(
            self.liquor_aggregate_limit, data.get("LiquorAggregateLimit")
        )

    def _select_required_option(self, locator, configured_value):
        if not configured_value:
            options = self.collect_extjs_options(locator)
            configured_value = next(
                (
                    option
                    for option in options
                    if option.strip().lower()
                    not in {"- select -", "-select-", "select"}
                ),
                None,
            )
        if not configured_value:
            raise AssertionError(f"No selectable value found for required field: {locator}")

        self.logger.info(
            "Selecting required GL optional coverage value: %s", configured_value
        )
        self.select_extjs_option(locator, str(configured_value))
        self.wait_for_app_ready()

    def _fill_required_text(self, locator, configured_value):
        if configured_value in (None, ""):
            raise AssertionError(f"Missing test data for required field: {locator}")
        self.with_optional_oneshield_response(
            lambda: self.smart_fill(locator, str(configured_value))
        )
        self.wait_for_app_ready()

    @staticmethod
    def _active_endorsements(data):
        endorsement_keys = [
            "HiredAutoCoverage",
            "NonOwnedAutoCoverage",
            "EmployeeBenefitsCoverage",
            "LiquorLiabilityCoverage",
            "GLEnhancementEndorsement",
            "GLManualCoverages",
            "ContractualLiabilityExclusion",
            "ExcludeEmployeesAsAdditionalInsureds",
            "HazardsDesignatedPremises",
        ]
        return [key for key in endorsement_keys if data.get(key) is True]

    def _visible_required_controls(self):
        return self.page.evaluate(
            """() => {
                const visible = el => {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    return rect.width > 0 && rect.height > 0
                        && style.display !== 'none'
                        && style.visibility !== 'hidden';
                };
                const normalize = value => (value || '').replace(/\\s+/g, ' ').trim();
                return [...document.querySelectorAll('input, textarea, select')]
                    .filter(visible)
                    .map(el => {
                        const field = el.closest('.x-field, .x-form-item');
                        const label = field && field.querySelector(
                            'label, .x-form-item-label'
                        );
                        return {
                            label: normalize(
                                el.getAttribute('aria-label')
                                || (label && label.textContent)
                            ),
                            role: el.getAttribute('role'),
                            value: normalize(el.value),
                            required: el.getAttribute('aria-required') === 'true'
                                || normalize(label && label.textContent).endsWith('*'),
                            osviewid: el.getAttribute('osviewid'),
                        };
                    })
                    .filter(item => item.required);
            }"""
        )
