import allure

from ui.pages.common.base_page import BasePage


class PolicyTermPage(BasePage):
    """Handles policy term and coverage details."""
    
    def __init__(self, page):
        super().__init__(page)
        self.coverage = page.get_by_role("combobox", name="Policy Coverage Option*")
        self.medical_expense = page.get_by_role(
            "combobox", name="Medical Expense", exact=True
        )
        self.wages_loss_basic = page.get_by_role(
            "combobox", name="Wages Loss Basic", exact=True
        )
        self.funeral_expense = page.get_by_role(
            "combobox", name="Funeral Expense", exact=True
        )
        self.accidental_death = page.get_by_role(
            "combobox", name="Accidental Death", exact=True
        )
        self.combination_base = page.get_by_role(
            "combobox", name="Combination Base", exact=True
        )
        self.otc_deductible = page.get_by_role(
            "combobox", name="OTC Deductible", exact=True
        )
        self.collision_deductible = page.get_by_role(
            "combobox", name="COLL Deductible", exact=True
        )
        self.comp_otc_options = page.get_by_role(
            "combobox", name="COMP/OTC - Options", exact=True
        )
        self.transportation_and_labor_limit = page.get_by_role(
            "combobox", name="T& L Limit", exact=True
        )
        self.substitute_transportation = page.get_by_role(
            "combobox", name="Substitute Transportation", exact=True
        )
        self.gap = page.get_by_role("combobox", name="Gap", exact=True)
        self.sound_equipment = page.get_by_role(
            "combobox", name="Sound Equip", exact=True
        )
        self.tapes = page.get_by_role("combobox", name="Tapes", exact=True)
        self.custom_amount = page.get_by_role(
            "combobox", name="Custom Amount", exact=True
        )
        self.rate_quote_button = page.get_by_role("button", name=">>> Rate Quote")

    def policy_term_steps(self, data):
        """Perform policy term steps."""
        self.set_coverage(data)
        self.verify_package_coverage_values(data)
        self.click_rate()

    def set_coverage(self, data):
        """Set policy coverage option."""
        coverage = data["PolicyCoverage"]
        self.select_extjs_option(
            self.coverage,
            coverage,
            wait_for_response=True,
            url_parts=["FieldProcessorServlet"],
        )
        self.wait_for_app_ready()

    @allure.step("Verify package-derived Auto coverage values")
    def verify_package_coverage_values(self, data):
        """Assert the read-only coverage values populated by the package."""
        fields = {
            "MedicalExpense": self.medical_expense,
            "WagesLossBasic": self.wages_loss_basic,
            "FuneralExpense": self.funeral_expense,
            "AccidentalDeath": self.accidental_death,
            "CombinationBase": self.combination_base,
            "OTCDeductible": self.otc_deductible,
            "CollisionDeductible": self.collision_deductible,
            "CompOTCOptions": self.comp_otc_options,
            "TransportationAndLaborLimit": self.transportation_and_labor_limit,
            "SubstituteTransportation": self.substitute_transportation,
            "Gap": self.gap,
            "SoundEquipment": self.sound_equipment,
            "Tapes": self.tapes,
            "CustomAmount": self.custom_amount,
        }
        for key, locator in fields.items():
            expected = str(data.get(key, "")).strip()
            if not expected:
                continue
            locator.wait_for(state="visible", timeout=10_000)
            actual = locator.input_value().strip()
            assert actual == expected, (
                f"{key} mismatch for {data['PolicyCoverage']}: "
                f"expected '{expected}', got '{actual}'"
            )
            assert not locator.is_editable(), (
                f"{key} was expected to be package-derived and read-only."
            )
            self.logger.info(
                "Verified %s=%s for package %s",
                key,
                actual,
                data["PolicyCoverage"],
            )

    def click_rate(self):
        """Rate the quote."""
        self.smart_click(self.rate_quote_button)
