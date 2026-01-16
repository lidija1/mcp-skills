from playwright.sync_api import Page

class BasePage:
    def __init__(self, page: Page):
        self.page = page

    def wait_visible(self, selector: str, timeout: int = 15000):
        locator = self.page.locator(selector)
        locator.wait_for(state="visible", timeout=timeout)
        return locator

    def type_text(self, selector: str, value: str, delay: int = 20):
        """Standard fill can be too fast for OneShield, using sequential press."""
        locator = self.wait_visible(selector)
        locator.click()
        locator.fill(value)

    def click_element(self, selector: str):
        locator = self.wait_visible(selector)
        locator.click()
