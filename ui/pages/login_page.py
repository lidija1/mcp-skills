import os
from ui.pages.base_page import BasePage

class LoginPage(BasePage):
    def __init__(self, page):
        super().__init__(page)
        # Locators from your JS example
        self.employee_portal = '#employeePortal' # Proveri da li je ID isti
        self.partner_num_field = "//div[text()='PARTNER NUMBER']/../../../..//input"
        self.username_field = "//div[text()='USERNAME']/../../../..//input"
        self.password_field = "//div[text()='PASSWORD']/../../../..//input"
        self.login_btn = "//span[contains(@class, 'x-btn-inner') and text()='login']"

    def navigate(self, url=None):
        target = url or 'https://inforcedev.oneshield.com/splash.html'
        self.page.goto(target)

    def click_splash_button(self):
        self.click_element(self.employee_portal)

    def fill_credentials_from_env(self):
        # OneShield often needs a small pause after splash
        self.page.wait_for_timeout(4000)

        self.type_text(self.partner_num_field, os.getenv('PARTNER_NUM', 'default_val'))
        self.type_text(self.username_field, os.getenv('USERNAMEE', 'default_val'))
        self.type_text(self.password_field, os.getenv('PASSWORD', 'default_val'))

        self.page.wait_for_timeout(500)

    def click_login(self):
        self.click_element(self.login_btn)
