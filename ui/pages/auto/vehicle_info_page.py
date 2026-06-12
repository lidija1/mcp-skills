import allure

from ui.pages.common.base_page import BasePage


class VehicleInfoPage(BasePage):
    """Handles vehicle information for auto insurance quotes."""
    
    def __init__(self, page):
        super().__init__(page)
        self.vehicle_type = page.get_by_role("combobox", name="Vehicle Type*")
        self.vehicle_detail_entry_mode = page.get_by_role(
            "combobox", name="Vehicle Detail Entry Mode", exact=True
        )
        self.year_input = page.get_by_role("combobox", name="Year*")
        self.make = page.get_by_role("combobox", name="Make*")
        self.model = page.get_by_role("combobox", name="Model*")
        self.specification = page.get_by_role("combobox", name="Specification*")
        self.vehicle_use = page.get_by_role("combobox", name="Vehicle Use*")
        self.ownership = page.get_by_role("combobox", name="Ownership")
        self.physical_damage_symbol = page.get_by_role(
            "textbox", name="Physical Damage Symbol (Override)"
        )
        self.garaging_address1 = page.get_by_role("textbox", name="Address Line 1")
        self.garaging_address2 = page.get_by_role("textbox", name="Address Line 2")
        self.garaging_city = page.get_by_role("textbox", name="City")
        self.garaging_state = page.get_by_role(
            "combobox", name="State/Province", exact=True
        )
        self.garaging_zip = page.get_by_role("textbox", name="ZIP")
        self.title_jointly_owned = page.get_by_role(
            "group", name="Title jointly owned?"
        )
        self.save_button = page.get_by_role("button", name="save changes")
        self.tree_coverages_button = page.get_by_role("link", name="Coverages")
        self.indicator_loading = page.locator(".x-loading-indicator")
        self.x_loading_mask = page.locator(".x-mask")

    @allure.step("Fill vehicle info")
    def fill_vehicle_info(self, data):
        """Fill complete vehicle information form."""
        self.logger.info("Filling vehicle information")
        self.set_vehicle_detail_entry_mode(data)
        self.set_year(data)
        self.set_make(data)
        self.set_model(data)
        self.set_specification(data)
        self.set_vehicle_use(data)
        self.set_ownership(data)
        if data.get("Ownership") != "Owned":
            self.add_loss_payee(data)
        self.fill_optional_vehicle_info(data)
        self.click_save()
        self.click_coverages_link()

    @allure.step("Set vehicle detail entry mode")
    def set_vehicle_detail_entry_mode(self, data):
        value = data.get("VehicleDetailEntryMode")
        if not value:
            return
        self.select_extjs_option(
            self.vehicle_detail_entry_mode,
            value,
        )
        self.wait_for_app_ready()

    @allure.step("Fill optional vehicle fields")
    def fill_optional_vehicle_info(self, data):
        self._set_optional_text(
            self.physical_damage_symbol,
            data.get("PhysicalDamageSymbol"),
        )
        self._set_optional_text(
            self.garaging_address1,
            data.get("GaragingAddress1"),
        )
        self._set_optional_text(
            self.garaging_address2,
            data.get("GaragingAddress2"),
        )
        self._set_optional_text(self.garaging_city, data.get("GaragingCity"))
        self._set_optional_combo(self.garaging_state, data.get("GaragingState"))
        self._set_optional_text(self.garaging_zip, data.get("GaragingZIP"))

        if str(data.get("TitleJointlyOwned", "")).strip().lower() in {
            "yes",
            "true",
            "1",
        }:
            checkbox = self.title_jointly_owned.get_by_role("checkbox").first
            if not checkbox.is_checked():
                checkbox.dispatch_event("click")

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

    def _set_optional_text(self, locator, value):
        if not value:
            return
        try:
            locator.first.wait_for(state="visible", timeout=2_000)
        except Exception:
            self.logger.info("Configured optional text field is not visible; skipping.")
            return
        expected = str(value).strip()
        if not locator.first.is_editable():
            actual = locator.first.input_value().strip()
            assert actual == expected, (
                f"Read-only optional field mismatch: expected '{expected}', "
                f"got '{actual}'"
            )
            self.logger.info("Read-only optional field already matches configured value.")
            return
        self.smart_fill(locator.first, expected)

    @allure.step("Set vehicle year")
    def set_year(self, data):
        """Select vehicle year."""
        year = data["Year"]
        self.logger.info(f"Setting year: {year}")
        # Define expected network response
        with self.page.expect_response("**/FieldProcessorServlet*") as response_info:
        # Akcija koja okida mrežni poziv
            self.smart_click(self.year_input)
            self.smart_click(self.page.locator(f"//li[text()='{year}']"))

        # Opciono: Provera da li je server vratio 'OK' status
        response = response_info.value
        if response.status != 200:
            print(f"Warning: FieldProcessor returned status {response.status}")
        # time.sleep(0.5)

    @allure.step("Set vehicle make")
    def set_make(self, data):
        """Select vehicle make."""
        make = data["Make"]
        self.logger.info(f"Setting make: {make}")
        with self.page.expect_response("**/FieldProcessorServlet*") as response_info:
            self.smart_click(self.make)
            self.smart_click(self.page.locator(f"//li[text()='{make}']"))
        response = response_info.value
        if response.status != 200:
            print(f"Warning: FieldProcessor returned status {response.status}")


    @allure.step("Set vehicle model")
    def set_model(self, data):
        """Select vehicle model."""
        model = data["Model"]
        self.logger.info(f"Setting model: {model}")
        with self.page.expect_response("**/FieldProcessorServlet*") as response_info:
            self.smart_click(self.model)
            self.smart_click(self.page.locator(f"//li[text()='{model}']"))
        response = response_info.value
        if response.status != 200:
            print(f"Warning: FieldProcessor returned status {response.status}")

    @allure.step("Set vehicle specification")
    def set_specification(self, data):
        """Select vehicle specification."""
        specification = data["Spec"]
        self.logger.info(f"Setting specification: {specification}")
        self.smart_click(self.specification)
        self.smart_click(self.page.locator(f"//li[text()='{specification}']"))

    @allure.step("Set vehicle use")
    def set_vehicle_use(self, data):
        """Select vehicle use type."""
        vehicle_use = data["VehicleUse"]
        self.logger.info(f"Setting vehicle use: {vehicle_use}")
        self.smart_click(self.vehicle_use)
        self.smart_click(self.page.locator(f"//li[text()='{vehicle_use}']"))

    @allure.step("Set vehicle ownership")
    def set_ownership(self, data):
        """Select ownership type."""
        ownership = data["Ownership"]
        self.logger.info(f"Setting ownership: {ownership}")
        self.select_extjs_option(
            self.ownership,
            ownership,
        )
        self.wait_for_app_ready()

    @allure.step("Add loss payee / additional interest")
    def add_loss_payee(self, data):
        """Click Add and fill the mandatory Loss Payee / Additional Interest row.

        Interest Type options are 'Leased' or 'Financed' — mirrors the Ownership value.
        """
        self.logger.info("Adding loss payee / additional interest")
        add_btn = self.page.get_by_role("button", name="Add", exact=True)
        add_btn.wait_for(state="visible", timeout=10_000)
        self.smart_click(add_btn)
        self.wait_for_app_ready()

        # Interest Type — required dropdown (options: Leased / Financed)
        interest_type = data.get("LossPayeeType", data.get("Ownership", "Leased"))
        interest_type_combo = self.page.get_by_role("combobox", name="Interest Type")
        interest_type_combo.wait_for(state="visible", timeout=10_000)
        self.select_extjs_option(interest_type_combo, interest_type)

        # Loss Payee / Additional Interest Name — required text field
        name_field = self.page.get_by_role("textbox", name="Loss Payee/Additional Interest Name")
        name_field.wait_for(state="visible", timeout=10_000)
        self.smart_fill(name_field, data.get("LossPayeeName", "Leasing Company"))

    @allure.step("Click save")
    def click_save(self):
        """Save vehicle information."""
        self.logger.info("Clicking save button")
        self.smart_click(self.save_button)

    @allure.step("Click coverages link")
    def click_coverages_link(self):
        """Navigate to coverages page."""
        self.logger.info("Navigating to coverages")
        self.smart_click(self.tree_coverages_button)
        self.page.get_by_role(
            "combobox", name="Policy Coverage Option*", exact=True
        ).wait_for(state="visible", timeout=30_000)
