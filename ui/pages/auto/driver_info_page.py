from ui.pages.common.base_page import BasePage


class DriverInfoPage(BasePage):
    """Handles driver information for auto insurance quotes."""
    
    def __init__(self, page):
        super().__init__(page)
        self.gender = page.get_by_role("combobox", name="Gender*")
        self.marital_status = page.get_by_role("combobox", name="Marital Status*")
        self.driver_status = page.get_by_role("combobox", name="Driver Status*")
        self.employment = page.get_by_role("combobox", name="Employment Category")
        self.occupation = page.get_by_role("combobox", name="Occupation")
        self.licence = page.get_by_role("combobox", name="License Status*")
        self.save_button = page.get_by_role("button", name="save changes")
        self.tree_vehicle_info = page.get_by_role("link", name="Vehicle_1")

    def fill_driver_info(self, data):
        """Fill driver information form."""
        self.gender.fill(data["Gender"])
        self.marital_status.fill(data["MaritalStatus"])
        self.driver_status.fill(data["DriverStatus"])
        self.employment.fill(data["EmploymentCategory"])
        self.occupation.fill(data["Occupation"])
        self.licence.fill(data["LicenseStatus"])
        self.answer_question("Certificate of Insurance Required?", data["SR22"])
        self.save_button.click()

    def click_vehicle_info_link(self):
        """Navigate to vehicle information page."""
        self.tree_vehicle_info.click()
