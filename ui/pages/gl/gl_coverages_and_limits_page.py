import re

from ui.pages.common.base_page import BasePage


class GeneralLiabilityCoverageAndLimitsPage(BasePage):
    """General Liability coverage and limits page."""

    def __init__(self, page):
        super().__init__(page)

        self.coverage_and_limits_link = page.get_by_role("link", name="GL Coverage and Limits")
        self.policy_type = page.get_by_role("combobox", name="Policy Type*")
        self.form_type = page.get_by_role("combobox", name="Form Type*")
        self.defense_treatment = page.get_by_role("combobox", name="Defense Treatment*")
        self.foreign_sales_question = "foreign sales"
        self.limit_ventilation_required = page.get_by_role("combobox", name="Limit Ventilation Required*")
        self.each_occurrence_limit = page.get_by_role("combobox", name="Each Occurrence Limit*")
        self.general_aggregate_limit = page.get_by_role("combobox", name="General Aggregate Limit*")
        self.personal_and_advertising_injury = page.get_by_role("combobox", name="Personal & Advertising Injury")
        self.products_and_completed_operations = page.get_by_role("combobox", name="Products & Completed")
        self.fire_damage_legal_liability = page.get_by_role("combobox", name="Fire Damage Legal Liability")
        self.medical_expense_limit = page.get_by_role("combobox", name="Medical Expense Limit - Any")
        self.excess_attachment_point = page.get_by_role("combobox", name="GL Excess Attachment Point*")
        self.general_liability_deductible = page.get_by_role("combobox", name="General Liability Deductible")
        self.deductible_type = page.get_by_role("combobox", name="Deductible Type*")
        self.deductible_applies = page.get_by_role("combobox", name="Deductible Applies*")
        self.coverage_save_button = page.get_by_role("button", name="save changes")

        # Optional endorsement checkboxes
        self.hired_auto_coverage = page.get_by_role(
            "checkbox", name="Hired Auto Coverage", exact=True
        )
        self.non_owned_auto_coverage = page.get_by_role(
            "checkbox", name="Non-Owned Auto Coverage", exact=True
        )
        self.employee_benefits_coverage = page.get_by_role(
            "checkbox", name="Employee Benefits Coverage", exact=True
        )
        self.liquor_liability_coverage = page.get_by_role(
            "checkbox", name="Liquor Liability Coverage", exact=True
        )
        self.gl_enhancement_endorsement = page.get_by_role(
            "checkbox", name="General Liability Enhancement Endorsement", exact=True
        )
        self.gl_manual_coverages = page.get_by_role(
            "checkbox", name="General Liability Manual Coverages", exact=True
        )
        self.contractual_liability_exclusion = page.get_by_role(
            "checkbox", name="Contractual Liability Exclusion", exact=True
        )
        self.exclude_employees_additional_insureds = page.get_by_role(
            "checkbox", name="Exclude Employees as Additional Insureds", exact=True
        )
        self.hazards_designated_premises = page.get_by_role(
            "checkbox",
            name="Hazards in Connection with Designated Premises",
            exact=True,
        )

        # Optional rating modifier textboxes
        self.schedule_mod = page.get_by_role("textbox", name="Schedule Mod", exact=True)
        self.judgment = page.get_by_role("textbox", name="Judgment", exact=True)
        self.commission_mod = page.get_by_role("textbox", name="Commission", exact=True)
        self.experience_mod = page.get_by_role(
            "textbox", name="Experience Mod", exact=True
        )

    def coverage_and_limits_steps(self, data):
        self.open_coverage_and_limits()
        self.select_coverage_type(data)
        self.set_policy_type(data)
        self.set_form_type(data)
        self.set_defense_treatment(data)
        self.set_foreign_sales(data)
        self.set_limit_ventilation_required(data)
        self.set_each_occurrence_limit(data)
        self.set_general_aggregate_limit(data)
        self.set_personal_and_advertising_injury(data)
        self.set_products_and_completed_operations(data)
        self.set_fire_damage_legal_liability(data)
        self.set_medical_expense_limit(data)
        self.set_excess_attachment_point(data)
        self.set_general_liability_deductible(data)
        self.set_deductible_type(data)
        self.set_deductible_applies(data)
        self.set_rating_modifiers(data)
        self.set_optional_endorsements(data)
        self.click_coverage_save()

    def inventory_dropdown_options(self):
        return {
            "CoverageType": self.collect_visible_role_texts("option"),
            "PolicyType": self.collect_extjs_options(self.policy_type),
            "FormType": self.collect_extjs_options(self.form_type),
            "DefenseTreatment": self.collect_extjs_options(self.defense_treatment),
            "ForeignSales": self.collect_radio_options(self.foreign_sales_question),
            "LimitVentilationRequired": self.collect_extjs_options(self.limit_ventilation_required),
            "EachOccurrenceLimit": self.collect_extjs_options(self.each_occurrence_limit),
            "GeneralAggregateLimit": self.collect_extjs_options(self.general_aggregate_limit),
            "PersonalAndAdvertisingInjuryLimit": self.collect_extjs_options(self.personal_and_advertising_injury),
            "ProductsAndCompletedOperationsAggregateLimit": self.collect_extjs_options(
                self.products_and_completed_operations
            ),
            "FireDamageLegalLiabilityLimitAnyOneFire": self.collect_extjs_options(
                self.fire_damage_legal_liability
            ),
            "MedicalExpenseLimitAnyOnePerson": self.collect_extjs_options(self.medical_expense_limit),
            "GeneralLiabilityDeductible": self.collect_extjs_options(self.general_liability_deductible),
            "DeductibleType": self.collect_extjs_options(self.deductible_type),
            "DeductibleApplies": self.collect_extjs_options(self.deductible_applies),
        }

    def inventory_and_fill(self, data):
        options = {}
        self.open_coverage_and_limits()
        options["CoverageType"] = self.collect_visible_role_texts("option")
        self.select_coverage_type(data)
        options["PolicyType"] = self.collect_extjs_options(self.policy_type)
        self.set_policy_type(data)
        options["FormType"] = self.collect_extjs_options(self.form_type)
        self.set_form_type(data)
        options["DefenseTreatment"] = self.collect_extjs_options(self.defense_treatment)
        self.set_defense_treatment(data)
        options["ForeignSales"] = self.collect_radio_options(self.foreign_sales_question)
        self.set_foreign_sales(data)
        options["LimitVentilationRequired"] = self.collect_extjs_options(self.limit_ventilation_required)
        self.set_limit_ventilation_required(data)
        options["EachOccurrenceLimit"] = self.collect_extjs_options(self.each_occurrence_limit)
        self.set_each_occurrence_limit(data)
        options["GeneralAggregateLimit"] = self.collect_extjs_options(self.general_aggregate_limit)
        self.set_general_aggregate_limit(data)
        options["PersonalAndAdvertisingInjuryLimit"] = self.collect_extjs_options(self.personal_and_advertising_injury)
        self.set_personal_and_advertising_injury(data)
        options["ProductsAndCompletedOperationsAggregateLimit"] = self.collect_extjs_options(
            self.products_and_completed_operations
        )
        self.set_products_and_completed_operations(data)
        options["FireDamageLegalLiabilityLimitAnyOneFire"] = self.collect_extjs_options(
            self.fire_damage_legal_liability
        )
        self.set_fire_damage_legal_liability(data)
        options["MedicalExpenseLimitAnyOnePerson"] = self.collect_extjs_options(self.medical_expense_limit)
        self.set_medical_expense_limit(data)
        options["GeneralLiabilityDeductible"] = self.collect_extjs_options(self.general_liability_deductible)
        self.set_general_liability_deductible(data)
        options["DeductibleType"] = self.collect_extjs_options(self.deductible_type)
        self.set_deductible_type(data)
        options["DeductibleApplies"] = self.collect_extjs_options(self.deductible_applies)
        self.set_deductible_applies(data)
        self.click_coverage_save()
        return options

    def open_coverage_and_limits(self):
        self._click_and_wait(self.coverage_and_limits_link, wait_for_response=False)

    def select_coverage_type(self, data):
        coverage_type_option = self.page.get_by_role(
            "option",
            name=re.compile(re.escape(data["CoverageType"]), re.I),
        )
        self.smart_click(coverage_type_option)
        self.wait_for_loader_to_disappear()

    def set_policy_type(self, data):
        self.select_extjs_option(self.policy_type, data["PolicyType"])
        self.wait_for_loader_to_disappear()

    def set_form_type(self, data):
        self.select_extjs_option(self.form_type, data["FormType"])
        self.wait_for_loader_to_disappear()

    def set_defense_treatment(self, data):
        self.select_extjs_option(self.defense_treatment, data["DefenseTreatment"])
        self.wait_for_loader_to_disappear()

    def set_foreign_sales(self, data):
        self.answer_question(self.foreign_sales_question, data["ForeignSales"])
        self.wait_for_loader_to_disappear()

    def set_limit_ventilation_required(self, data):
        self.select_extjs_option(self.limit_ventilation_required, data["LimitVentilationRequired"])
        self.wait_for_loader_to_disappear()

    def set_each_occurrence_limit(self, data):
        self.select_extjs_option(self.each_occurrence_limit, data["EachOccurrenceLimit"])
        self.wait_for_loader_to_disappear()

    def set_general_aggregate_limit(self, data):
        self.select_extjs_option(self.general_aggregate_limit, data["GeneralAggregateLimit"])
        self.wait_for_loader_to_disappear()

    def set_personal_and_advertising_injury(self, data):
        self.select_extjs_option(self.personal_and_advertising_injury, data["PersonalAndAdvertisingInjuryLimit"])
        self.wait_for_loader_to_disappear()

    def set_products_and_completed_operations(self, data):
        self.select_extjs_option(
            self.products_and_completed_operations,
            data["ProductsAndCompletedOperationsAggregateLimit"],
        )
        self.wait_for_loader_to_disappear()

    def set_fire_damage_legal_liability(self, data):
        self.select_extjs_option(self.fire_damage_legal_liability, data["FireDamageLegalLiabilityLimitAnyOneFire"])
        self.wait_for_loader_to_disappear()

    def set_medical_expense_limit(self, data):
        self.select_extjs_option(self.medical_expense_limit, data["MedicalExpenseLimitAnyOnePerson"])
        self.wait_for_loader_to_disappear()

    def set_excess_attachment_point(self, data):
        attachment_point = data.get("ExcessAttachmentPoint")
        if not attachment_point:
            return

        self.select_extjs_option(self.excess_attachment_point, str(attachment_point))
        self.wait_for_loader_to_disappear()

    def set_general_liability_deductible(self, data):
        self.select_extjs_option(self.general_liability_deductible, data["GeneralLiabilityDeductible"])
        self.wait_for_loader_to_disappear()

    def set_deductible_type(self, data):
        self.select_extjs_option(self.deductible_type, data["DeductibleType"])
        self.wait_for_loader_to_disappear()

    def set_deductible_applies(self, data):
        self.select_extjs_option(self.deductible_applies, data["DeductibleApplies"])
        self.wait_for_loader_to_disappear()

    def set_optional_endorsements(self, data):
        _ENDORSEMENTS = [
            ("HiredAutoCoverage",                    self.hired_auto_coverage),
            ("NonOwnedAutoCoverage",                 self.non_owned_auto_coverage),
            ("EmployeeBenefitsCoverage",             self.employee_benefits_coverage),
            ("LiquorLiabilityCoverage",              self.liquor_liability_coverage),
            ("GLEnhancementEndorsement",             self.gl_enhancement_endorsement),
            ("GLManualCoverages",                    self.gl_manual_coverages),
            ("ContractualLiabilityExclusion",        self.contractual_liability_exclusion),
            ("ExcludeEmployeesAsAdditionalInsureds", self.exclude_employees_additional_insureds),
            ("HazardsDesignatedPremises",            self.hazards_designated_premises),
        ]
        active = [(k, loc) for k, loc in _ENDORSEMENTS if data.get(k) is True]
        if not active:
            return
        for key, locator in active:
            locator.scroll_into_view_if_needed()
            locator.dispatch_event("click")
            self.wait_for_loader_to_disappear()

    def set_rating_modifiers(self, data):
        _MODIFIERS = [
            ("ScheduleMod",    self.schedule_mod),
            ("Judgment",       self.judgment),
            ("CommissionMod",  self.commission_mod),
            ("ExperienceMod",  self.experience_mod),
        ]
        for key, locator in _MODIFIERS:
            value = data.get(key)
            if value is not None and str(value).strip():
                self.smart_fill(locator, str(value))
                self.wait_for_loader_to_disappear()

    def click_coverage_save(self):
        self._click_and_wait(self.coverage_save_button, wait_for_response=True)

