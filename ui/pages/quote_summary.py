
from ui.pages.base_page import BasePage


class QuoteSummary(BasePage):
    def __init__(self, page):
        super().__init__(page)

        self.billing = "//div[text()='Billing Method']/../../../..//input"
        self.save_button = "//span[text()='save changes']"
        self.next_red_button = "//span[text()='next red']"


    def set_billing(self, data):
        self.page.fill(self.billing, data['BILLING METHOD'])

    def misleading_radio(self, data: dict):
        self.answer_question("Has anyone knowingly provided material, false, or misleading information ", data["FALSE INFO"])

    def damage_radio(self, data):
        self.answer_question("Does any vehicle have any existing damage?", data["DAMAGE INFO"])

    def click_save(self):
        self.click_element(self.save_button)

    def click_next_red(self):
        self.click_element(self.next_red_button)

