import os
import allure
from playwright.sync_api import expect

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
        self.smart_click(self.employee_portal)

    def wait_for_login_page(self):
        """Wait for the login page to be ready."""
        self.logger.info("Waiting for login page to be ready")
        expect(self.partner_num).to_be_visible(timeout=10000)  # Wait for partner number field
        self.logger.info("Login page is ready")

    @allure.step("Fill credentials from Environment Variables")
    def fill_credentials_from_env(self):
        """Fill login credentials from environment variables."""


        partner = os.getenv('PARTNER_NUM', 'default_val')
        user = os.getenv('USERNAMEE', 'default_val')

        self.logger.info(f"Filling credentials for Partner: {partner}, User: {user}")
        self.smart_fill(self.partner_num, partner)
        self.smart_fill(self.username_field, user)
        self.smart_fill(self.password_field, os.getenv('PASSWORD', 'default_val'))

        self.page.wait_for_timeout(500)

    @allure.step("Submit login")
    def click_login(self):
        """Click the login button."""
        self.logger.info("Clicking login button")
        self.smart_click(self.login_btn)
