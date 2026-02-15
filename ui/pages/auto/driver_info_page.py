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
        self.set_gender(data)
        self.set_marital_status(data)
        self.set_driver_status(data)
        self.set_employment_category(data)
        self.set_occupation(data)
        self.set_license_status(data)
        self.set_sr22_required(data)
        self.set_save_button()
        self.click_vehicle_info_link()

    def set_gender(self, data):
        """Set gender field."""
        self.gender.fill(data["Gender"])

    def set_marital_status(self, data):
        """Set marital status field."""
        self.marital_status.fill(data["MaritalStatus"])

    def set_driver_status(self, data):
        """Set driver status field."""
        self.driver_status.fill(data["DriverStatus"])

    def set_employment_category(self, data):
        """Set employment category field."""
        self.employment.fill(data["EmploymentCategory"])

    def set_occupation(self, data):
        """Set occupation field."""
        self.occupation.fill(data["Occupation"])

    def set_license_status(self, data):
        """Set license status field."""
        self.licence.fill(data["LicenseStatus"])

    def set_sr22_required(self, data):
        """Answer SR22 required question."""
        self.answer_question("Certificate of Insurance Required?", data["SR22"])

    def set_save_button(self):
        """Click save button."""
        self.save_button.click()

    def click_vehicle_info_link(self):
        """Navigate to vehicle information page."""
        self.tree_vehicle_info.click()
