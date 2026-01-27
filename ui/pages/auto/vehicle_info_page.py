import time
import allure
from ui.pages.base_page import BasePage


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
        self.click_save()

    @allure.step("Set vehicle year")
    def set_year(self, data):
        """Select vehicle year."""
        year = data["Year"]
        self.logger.info(f"Setting year: {year}")
        self.year_input.click()
        self.page.locator(f"//li[text()='{year}']").click()
        time.sleep(0.5)

    @allure.step("Set vehicle make")
    def set_make(self, data):
        """Select vehicle make."""
        make = data["Make"]
        self.logger.info(f"Setting make: {make}")
        self.make.click()
        self.page.locator(f"//li[text()='{make}']").click()
        time.sleep(0.3)

    @allure.step("Set vehicle model")
    def set_model(self, data):
        """Select vehicle model."""
        model = data["Model"]
        self.logger.info(f"Setting model: {model}")
        self.model.click()
        self.page.locator(f"//li[text()='{model}']").click()
        time.sleep(0.3)

    @allure.step("Set vehicle specification")
    def set_specification(self, data):
        """Select vehicle specification."""
        specification = data["Spec"]
        self.logger.info(f"Setting specification: {specification}")
        self.specification.click()
        self.page.locator(f"//li[text()='{specification}']").click()
        time.sleep(0.3)

    @allure.step("Set vehicle use")
    def set_vehicle_use(self, data):
        """Select vehicle use type."""
        vehicle_use = data["VehicleUse"]
        self.logger.info(f"Setting vehicle use: {vehicle_use}")
        self.vehicle_use.click()
        self.page.locator(f"//li[text()='{vehicle_use}']").click()
        time.sleep(0.3)

    @allure.step("Set vehicle ownership")
    def set_ownership(self, data):
        """Select ownership type."""
        ownership = data["Ownership"]
        self.logger.info(f"Setting ownership: {ownership}")
        self.ownership.fill(ownership)
        time.sleep(0.3)

    @allure.step("Click save")
    def click_save(self):
        """Save vehicle information."""
        self.logger.info("Clicking save button")
        self.save_button.click()

    @allure.step("Click coverages link")
    def click_coverages_link(self):
        """Navigate to coverages page."""
        self.logger.info("Navigating to coverages")
        self.tree_coverages_button.click()
