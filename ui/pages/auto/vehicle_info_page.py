import allure

from ui.pages.common.base_page import BasePage


class VehicleInfoPage(BasePage):
    """Handles vehicle information for auto insurance quotes."""
    
    def __init__(self, page):
        super().__init__(page)
        self.vehicle_type = page.get_by_role("combobox", name="Vehicle Type*")
        self.year_input = page.get_by_role("combobox", name="Year*")
        self.make = page.get_by_role("combobox", name="Make*")
        self.model = page.get_by_role("combobox", name="Model*")
        self.specification = page.get_by_role("combobox", name="Specification*")
        self.vehicle_use = page.get_by_role("combobox", name="Vehicle Use*")
        self.ownership = page.get_by_role("combobox", name="Ownership")
        self.save_button = page.get_by_role("button", name="save changes")
        self.tree_coverages_button = page.get_by_role("link", name="Coverages")
        self.indicator_loading = page.locator(".x-loading-indicator")
        self.x_loading_mask = page.locator(".x-mask")

    @allure.step("Fill vehicle info")
    def fill_vehicle_info(self, data):
        """Fill complete vehicle information form."""
        self.logger.info("Filling vehicle information")
        self.set_year(data)
        self.set_make(data)
        self.set_model(data)
        self.set_specification(data)
        self.set_vehicle_use(data)
        self.set_ownership(data)
        if data.get("Ownership") != "Owned":
            self.add_loss_payee(data)
        self.click_save()
        self.click_coverages_link()

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
        self.smart_fill(self.ownership, ownership)

    @allure.step("Add loss payee / additional interest")
    def add_loss_payee(self, data):
        """Click Add and fill the mandatory Loss Payee / Additional Interest row.

        Interest Type options are 'Leased' or 'Financed' — mirrors the Ownership value.
        """
        self.logger.info("Adding loss payee / additional interest")
        add_btn = self.page.get_by_role("button", name="Add", exact=True)
        add_btn.dispatch_event("click")

        # Interest Type — required dropdown (options: Leased / Financed)
        interest_type = data.get("LossPayeeType", data.get("Ownership", "Leased"))
        interest_type_combo = self.page.get_by_role("combobox", name="Interest Type")
        self.smart_click(interest_type_combo)
        self.smart_click(self.page.locator(f"//li[contains(text(),'{interest_type}')]"))

        # Loss Payee / Additional Interest Name — required text field
        name_field = self.page.get_by_role("textbox", name="Loss Payee/Additional Interest Name")
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
