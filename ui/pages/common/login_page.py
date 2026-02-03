import os
import allure
from ui.pages.common.base_page import BasePage


class LoginPage(BasePage):
    """Handles user authentication and login functionality."""
    
    def __init__(self, page):
        super().__init__(page)
        # Locators
        self.employee_portal = '#employeePortal'
        self.partner_num = page.get_by_role("textbox", name="PARTNER NUMBER*")
        self.username_field = page.get_by_role("textbox", name="USERNAME*")
        self.password_field = page.get_by_role("textbox", name="PASSWORD*")
        self.login_btn = page.get_by_role("button", name="login")

    @allure.step("Navigate to URL: {url}")
    def navigate(self, url=None):
        """Navigate to the login page."""
        target = url or 'https://inforcedev.oneshield.com/splash.html'
        self.logger.info(f"Navigating to: {target}")
        self.page.goto(target)

    @allure.step("Click splash button")
    def click_splash_button(self):
        """Click the employee portal button on splash screen."""
        self.logger.info("Clicking splash screen button")
        self.click_element(self.employee_portal)

    @allure.step("Fill credentials from Environment Variables")
    def fill_credentials_from_env(self):
        """Fill login credentials from environment variables."""
        # OneShield often needs a small pause after splash
        self.logger.info("Starting to fill credentials")
        self.page.wait_for_timeout(4000)
        
        partner = os.getenv('PARTNER_NUM', 'default_val')
        user = os.getenv('USERNAMEE', 'default_val')
        
        self.logger.info(f"Filling credentials for Partner: {partner}, User: {user}")
        self.partner_num.fill(partner)
        self.username_field.fill(user)
        self.password_field.fill(os.getenv('PASSWORD', 'default_val'))
        
        self.page.wait_for_timeout(500)

    @allure.step("Submit login")
    def click_login(self):
        """Click the login button."""
        self.logger.info("Clicking login button")
        self.login_btn.click()
