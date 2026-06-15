import re

from ui.pages.common.base_page import BasePage


class HomeownerCoveragePage(BasePage):

    def __init__(self, page):
        super().__init__(page)

        self.policy_coverage = page.get_by_role("combobox", name="Policy Coverage Option")
        self.residence_type = page.get_by_role("combobox", name="Residence Type")
        self.replacement_cost_contents = page.get_by_label("Replacement cost contents?")
        self.replacement_cost = page.get_by_role("textbox", name="Replacement Cost")
        self.contents = page.get_by_role("textbox", name="Contents")
        self.loss_of_use = page.get_by_role("textbox", name="Loss of Use")
        self.other_structures = page.get_by_role("textbox", name="Other Structures")
        self.number_of_floors = page.get_by_role("textbox", name="# of Floors")
        self.risk_floor = page.get_by_role(
            "textbox",
            name="The floor on which the risk is located",
        ).or_(
            page.locator(
                '[osviewid$="_CI_15064646_Label"]'
            ).locator("xpath=following::input[1]")
        )
        self.perils = page.get_by_role("combobox", name="All Perils Deductible")
        self.windstorm = page.get_by_role("combobox", name="Windstorm or Hail")
        self.liability = page.get_by_role("combobox", name="Liability")
        self.medical = page.get_by_role("combobox", name="Medical Payments")
        self.year_built = page.get_by_role("textbox", name="Year Built")
        self.construction = page.get_by_role("combobox", name="Construction Type")
        self.protection_class = page.get_by_role("combobox", name="Protection Class")
        self.bceg = page.get_by_role("combobox", name="BCEG")
        self.roof_type = page.get_by_role("combobox", name="Roof Type")
        self.roof_shape = page.get_by_role("combobox", name="Roof Shape")
        self.secondary_water_resistance = page.get_by_role("combobox", name="Secondary Water Resistance")
        self.opening_protection = page.get_by_role("combobox", name="Opening Protection")
        self.roof_wall_connection = page.get_by_role("combobox", name="Roof Wall Connection")
        self.roof_deck = page.get_by_role("combobox", name="Roof Deck", exact=True)
        self.roof_deck_attachment = page.get_by_role("combobox", name="Roof Deck Attachment")
        self.distance_to_shore = page.get_by_role("combobox", name="Distance to Shore")
        self.central_reporting_fire_alarm = page.get_by_label("Central Reporting Fire Alarm")
        self.guard_gated_community = page.get_by_label("Guard Gated Community")
        self.central_reporting_burglar_alarm = page.get_by_label("Central Reporting Burglar Alarm")
        self.residential_sprinkler_system = page.get_by_label("Residential Sprinkler System")
        self.permanently_installed_generator = page.get_by_label("Permanently Installed Generator")
        self.lightning_protection_system = page.get_by_label("Lightning Protection System")
        self.gas_leak_detector = page.get_by_label("Gas Leak Detector")
        self.pool_question_patterns = (
            "swimming pool",
            "pool",
        )
        self.external_perimeter_gate = page.get_by_label("External Perimeter Gate")
        self.full_time_live_in_caretaker = page.get_by_label("Full Time Live In Caretaker")
        self.hour_door_man = page.get_by_label("24 Hour Door Man")
        self.locked_or_manned_elevator = page.get_by_label("Locked or Manned Elevator")
        self.surveillance_camera = page.get_by_label("Surveillance Camera")
        self.hour_signal_continuity = page.get_by_label("24 Hour Signal Continuity")
        self.sprinkler_system_with_waterflow = page.get_by_label("Sprinkler System with Waterflow")
        self.perimeter_security_protection = page.get_by_role("combobox", name="Perimeter Security Protection")
        self.prior_address_line_1 = page.get_by_role("textbox", name="Address Line 1")
        self.prior_address_line_2 = page.get_by_role("textbox", name="Address Line 2")
        self.prior_city = page.get_by_role("textbox", name="City")
        self.prior_state = page.get_by_role("combobox", name="State")
        self.prior_zip = page.get_by_role("textbox", name="ZIP")
        self.prior_country = page.get_by_role("combobox", name="Country")
        self.save = page.get_by_role("button", name="save changes")
        self.bind_info = page.get_by_role("link", name="Bind Information")

    def coverage_steps(self, data):
        self.set_residency(data)
        self.set_coverage(data)
        self.wait_for_loader_to_disappear()
        self.set_number_of_floors(data)
        self.set_risk_floor(data)
        self.set_replacement(data)
        self.set_contents(data)
        self.set_loss_of_use(data)
        self.set_perils(data)
        self.set_windstorm(data)
        self.set_liability(data)
        self.set_medical(data)
        self.set_year_built(data)
        self.set_construction(data)
        self.set_roof_type(data)
        self.set_optional_dropdowns(data)
        self.set_security_protections(data)
        self.set_under_construction(data)
        self.set_lived_here(data)
        self.set_prior_address(data)
        self.set_loses(data)
        self.set_pool(data)
        self.click_save()
        self.click_bind_info()

    def set_coverage(self, data):
        self._open_and_select(self.policy_coverage, data["PolicyCoverageOption"])

    def set_residency(self, data):
        self.wait_for_loader_to_disappear()
        self.wait_for_app_ready()
        self.residence_type.wait_for(state="visible", timeout=30_000)
        self._open_and_select(self.residence_type, data["ResidenceType"])
        self.wait_for_loader_to_disappear()

    def set_replacement(self, data):
        if not data.get("ReplacementCost") or self.replacement_cost.count() == 0:
            return
        with self.page.expect_response("**/FieldProcessorServlet*"):
            self.smart_fill(self.replacement_cost, data["ReplacementCost"])

    def set_contents(self, data):
        if not data.get("Contents") or self.contents.count() == 0:
            return
        with self.page.expect_response("**/FieldProcessorServlet*"):
            self.smart_fill(self.contents, data["Contents"])
        self.wait_for_loader_to_disappear()

    def set_loss_of_use(self, data):
        if not data.get("LossOfUse") or self.loss_of_use.count() == 0:
            return
        with self.page.expect_response("**/FieldProcessorServlet*"):
            self.smart_fill(self.loss_of_use, data["LossOfUse"])
        self.wait_for_loader_to_disappear()

    def set_additional_limit_fields(self, data):
        """Exercise coverage limit fields that are visible but absent from the base flow."""
        self.set_contents(data)
        self.set_loss_of_use(data)
        self.other_structures.scroll_into_view_if_needed()
        self.other_structures.wait_for(state="visible", timeout=15000)

    def set_number_of_floors(self, data):
        value = data.get("NumberOfFloors")
        if not value or self.number_of_floors.count() == 0:
            return
        self.smart_fill(self.number_of_floors, str(value))

    def set_risk_floor(self, data):
        value = data.get("RiskFloor")
        if not value or self.risk_floor.count() == 0:
            return
        self.smart_fill(self.risk_floor, str(value))

    def review_mitigation_and_security_elements(self):
        """Verify discovered mitigation/security controls without changing rating inputs."""
        for locator in (
            self.replacement_cost_contents,
            self.protection_class,
            self.bceg,
            self.roof_shape,
            self.secondary_water_resistance,
            self.opening_protection,
            self.roof_wall_connection,
            self.roof_deck,
            self.roof_deck_attachment,
            self.distance_to_shore,
            self.central_reporting_fire_alarm,
            self.guard_gated_community,
            self.central_reporting_burglar_alarm,
            self.residential_sprinkler_system,
            self.permanently_installed_generator,
            self.lightning_protection_system,
            self.gas_leak_detector,
            self.external_perimeter_gate,
            self.full_time_live_in_caretaker,
            self.hour_door_man,
            self.locked_or_manned_elevator,
            self.surveillance_camera,
            self.hour_signal_continuity,
            self.sprinkler_system_with_waterflow,
            self.perimeter_security_protection,
        ):
            locator.scroll_into_view_if_needed()
            locator.wait_for(state="visible", timeout=15000)

    def set_perils(self, data):
        self._open_and_select(self.perils, data["AllPerilsDeductable"])

    def set_windstorm(self, data):
        self._open_and_select(self.windstorm, data["WindstormDeductable"])

    def set_liability(self, data):
        self._open_and_select(self.liability, data["Liability"])

    def set_medical(self, data):
        self._open_and_select(self.medical, data["MedPayments"])

    def set_year_built(self, data):
        with self.page.expect_response("**/FieldProcessorServlet*"):
            self.smart_type(self.year_built, data["YearBuilt"])

    def set_construction(self, data):
        self._open_and_select(self.construction, data["ConstructionType"])

    def set_roof_type(self, data):
        self._open_and_select(self.roof_type, data["RoofType"])

    def set_optional_dropdowns(self, data):
        """Set additional homeowner dropdowns when a test case provides values."""
        optional_dropdowns = (
            ("ProtectionClass", self.protection_class),
            ("BCEG", self.bceg),
            ("RoofShape", self.roof_shape),
            ("SecondaryWaterResistance", self.secondary_water_resistance),
            ("OpeningProtection", self.opening_protection),
            ("RoofWallConnection", self.roof_wall_connection),
            ("RoofDeck", self.roof_deck),
            ("RoofDeckAttachment", self.roof_deck_attachment),
            ("DistanceToShore", self.distance_to_shore),
            ("PerimeterSecurityProtection", self.perimeter_security_protection),
        )
        for key, locator in optional_dropdowns:
            value = data.get(key)
            if value:
                self._open_and_select(locator, value)
                self.wait_for_loader_to_disappear()

    def set_security_protections(self, data):
        configured = set(data.get("SecurityProtectionSelections", []))
        if not configured:
            return
        checkboxes = {
            "Central Reporting Fire Alarm": self.central_reporting_fire_alarm,
            "Guard Gated Community": self.guard_gated_community,
            "Central Reporting Burglar Alarm": self.central_reporting_burglar_alarm,
            "Residential Sprinkler System": self.residential_sprinkler_system,
            "Permanently Installed Generator": self.permanently_installed_generator,
            "Lightning Protection System": self.lightning_protection_system,
            "Gas Leak Detector": self.gas_leak_detector,
            "External Perimeter Gate": self.external_perimeter_gate,
            "Full Time Live In Caretaker": self.full_time_live_in_caretaker,
            "24 Hour Door Man": self.hour_door_man,
            "Locked or Manned Elevator": self.locked_or_manned_elevator,
            "Surveillance Camera": self.surveillance_camera,
            "24 Hour Signal Continuity": self.hour_signal_continuity,
            "Sprinkler System with Waterflow": self.sprinkler_system_with_waterflow,
        }
        for label in configured:
            locator = checkboxes.get(label)
            if locator is None:
                raise AssertionError(f"Unknown security protection label: {label!r}. Valid: {sorted(checkboxes)}")
            if not locator.is_checked():
                locator.dispatch_event("click")

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

    def set_prior_address(self, data):
        if data.get("LivedHere") != "Yes":
            return
        fields = (
            ("PriorAddressLine1", self.prior_address_line_1),
            ("PriorAddressLine2", self.prior_address_line_2),
            ("PriorCity", self.prior_city),
            ("PriorZIP", self.prior_zip),
        )
        for key, locator in fields:
            value = data.get(key)
            if value:
                self.smart_fill(locator, value)
        if data.get("PriorState"):
            self.select_extjs_option(self.prior_state, data["PriorState"])
        country = data.get("PriorCountry")
        if country and self.prior_country.input_value().strip() != country:
            self.select_extjs_option(self.prior_country, country)

    def set_loses(self, data):
        value = data["Loses"]
        self.smart_click(
            self.page.locator(
                f"//div[text()='Any losses in the last three years?']/../../../..//label[text()='{value}']/../span"
            )
        )

    def set_pool(self, data):
        """Answer the optional pool question when the test data includes it."""
        value = data.get("Pool")
        if not value:
            return

        for pattern in self.pool_question_patterns:
            group = self.page.get_by_role("radiogroup", name=re.compile(pattern, re.I))
            if group.count() == 0:
                continue

            try:
                group.first.scroll_into_view_if_needed()
                if not group.first.is_visible(timeout=2000):
                    continue
                radio = group.first.get_by_label(re.compile(f"^{value}$", re.I))
                radio.dispatch_event("click")
                return
            except Exception:
                continue

        raise AssertionError("Pool question was not found on Homeowner Location Coverage.")

    def click_save(self):
        self.smart_click(self.save)
        self.wait_for_loader_to_disappear()

    def click_bind_info(self):
        self.smart_click(self.bind_info)
        self.wait_for_loader_to_disappear()

    def assert_dropdown_options(self, expected):
        """Assert every configured Location Coverage dropdown option."""
        dropdowns = {
            "ResidenceType": self.residence_type,
            "PolicyCoverageOption": self.policy_coverage,
            "AllPerilsDeductable": self.perils,
            "WindstormDeductable": self.windstorm,
            "Liability": self.liability,
            "MedPayments": self.medical,
            "ConstructionType": self.construction,
            "ProtectionClass": self.protection_class,
            "BCEG": self.bceg,
            "RoofType": self.roof_type,
            "RoofShape": self.roof_shape,
            "SecondaryWaterResistance": self.secondary_water_resistance,
            "OpeningProtection": self.opening_protection,
            "RoofWallConnection": self.roof_wall_connection,
            "RoofDeck": self.roof_deck,
            "RoofDeckAttachment": self.roof_deck_attachment,
            "DistanceToShore": self.distance_to_shore,
            "PerimeterSecurityProtection": self.perimeter_security_protection,
        }
        for key, locator in dropdowns.items():
            configured = expected.get(key)
            if configured is None:
                continue
            try:
                actual = self.get_extjs_options(locator)
            except Exception as exc:
                raise AssertionError(
                    f"Could not collect Location Coverage options for {key}: {exc}"
                ) from exc
            missing = [option for option in configured if option not in actual]
            assert not missing, f"{key} missing dropdown options: {missing}"

    def _open_and_select(self, locator, value):
        self.select_extjs_option(locator, value)
