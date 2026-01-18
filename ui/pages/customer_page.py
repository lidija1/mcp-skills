from ui.pages.base_page import BasePage
from utils.email_util import process_email


class CustomerPage(BasePage):
    def __init__(self, page):
        super().__init__(page)
        self.customer_type = "//div[text()='Customer Type']/../../../..//input[@value='Individual']"
        self.first_name = "//input[@osviewid='PAI_1086048_OT_3380946_OI_1_BI_1129948_CI_16118048']"
        self.last_name = "//input[@osviewid='PAI_1086048_OT_3380946_OI_1_BI_1129948_CI_16118248']"
        self.dob = "//div[text()='Date of Birth']/../../../..//input"
        self.email = "//div[text()='Email']/../../../..//input"
        self.phone_number = "//div[text()='Phone']/../../../..//input"
        self.zip_code = "//div[text()='ZIP Code']/../../../..//input"
        self.address = "//div[text()='Address Line 1']/../../../..//input"
        self.search_button = "//span[text()='>>> Search']"
        self.create_new_customer_button = "//span[text()='>>> Create A New Customer']"
        self.next_button = "//span[text()='   >>> next']"
        self.skip_button = "//span[text()='>>> skip']"

    def fill_customer_form(self, data):
        self.page.fill(self.first_name, data["FIRSTNAME"])
        self.page.fill(self.last_name, data["LASTNAME"])
        self.page.fill(self.dob, data["DOB"])

        self.page.fill(self.phone_number, str(data["PHONENUM"]))
        self.page.fill(self.zip_code, str(data["ZIP"]))
        self.page.fill(self.address, data["ADDRESS"])

    def enter_email(self, data):
        email_from_excel = data.get("EMAIL")
        processed_email = process_email(email_from_excel)
        self.page.fill(self.email, processed_email)

    def click_search(self):
        self.click_element(self.search_button)

    def click_create_new_customer(self):
        self.click_element(self.create_new_customer_button)

    def click_next(self):
        self.click_element(self.next_button)

    def click_skip(self):
        self.click_element(self.skip_button)


