import os
import allure
from playwright.sync_api import expect

from ui.pages.common.base_page import BasePage
from utils.performance_metrics import PerformanceMetrics


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

    # ========================================================================
    # Performance Testing Methods
    # ========================================================================

    @allure.step("Navigate with performance metrics")
    def navigate_with_metrics(self, metrics: PerformanceMetrics, url=None):
        """Navigate to the login page and measure performance.

        Args:
            metrics: PerformanceMetrics instance to collect data
            url: Target URL (optional)
        """
        target = url or 'https://inforcedev.oneshield.com/splash.html'
        self.logger.info(f"Navigating to: {target} (with metrics)")

        metrics.start_timer("navigation")
        self.page.goto(target)
        elapsed = metrics.stop_timer("navigation")

        self.logger.info(f"Navigation completed in {elapsed:.2f}ms")
        metrics.measure_page_load_time(self.page)
        metrics.measure_navigation(self.page)
        metrics.measure_resource_loading(self.page)

    @allure.step("Click splash button with performance metrics")
    def click_splash_button_with_metrics(self, metrics: PerformanceMetrics):
        """Click splash button and measure performance.

        Args:
            metrics: PerformanceMetrics instance to collect data
        """
        self.logger.info("Clicking splash screen button (with metrics)")

        metrics.start_timer("splash_button_click")
        self.click_element(self.employee_portal)
        elapsed = metrics.stop_timer("splash_button_click")

        self.logger.info(f"Splash button click completed in {elapsed:.2f}ms")

    @allure.step("Wait for login page with performance metrics")
    def wait_for_login_page_with_metrics(self, metrics: PerformanceMetrics, timeout_ms: int = 10000):
        """Wait for login page to be ready and measure element visibility.

        Args:
            metrics: PerformanceMetrics instance to collect data
            timeout_ms: Timeout in milliseconds
        """
        self.logger.info("Waiting for login page to be ready (with metrics)")

        visibility_metrics = metrics.measure_element_visibility(
            self.page,
            self.partner_num,
            timeout_ms=timeout_ms
        )
        self.logger.info(f"Partner number field visible in {visibility_metrics.get('element_visibility_time', 0):.2f}ms")

    @allure.step("Fill credentials with performance metrics")
    def fill_credentials_from_env_with_metrics(self, metrics: PerformanceMetrics):
        """Fill login credentials from environment variables and measure performance.

        Args:
            metrics: PerformanceMetrics instance to collect data
        """
        partner = os.getenv('PARTNER_NUM', 'default_val')
        user = os.getenv('USERNAMEE', 'default_val')

        self.logger.info(f"Filling credentials for Partner: {partner}, User: {user} (with metrics)")

        metrics.start_timer("fill_credentials")
        self.partner_num.fill(partner)
        self.username_field.fill(user)
        self.password_field.fill(os.getenv('PASSWORD', 'default_val'))
        self.page.wait_for_timeout(500)
        elapsed = metrics.stop_timer("fill_credentials")

        self.logger.info(f"Credentials filled in {elapsed:.2f}ms")

    @allure.step("Submit login with performance metrics")
    def click_login_with_metrics(self, metrics: PerformanceMetrics):
        """Click login button and measure performance.

        Args:
            metrics: PerformanceMetrics instance to collect data
        """
        self.logger.info("Clicking login button (with metrics)")

        metrics.start_timer("login_click")
        self.login_btn.click()
        elapsed = metrics.stop_timer("login_click")

        self.logger.info(f"Login click completed in {elapsed:.2f}ms")
