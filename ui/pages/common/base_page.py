import re

import allure
from playwright.sync_api import Page

from utils.logger import setup_logger


class BasePage:
    def __init__(self, page: Page):
        self.page = page
        self.logger = setup_logger(self.__class__.__name__)

    @allure.step("Wait for element '{selector}' to be visible")
    def wait_visible(self, selector: str, timeout: int = 15000):
        self.logger.info(f"Waiting for visibility of: {selector}")
        locator = self.page.locator(selector)
        locator.wait_for(state="visible", timeout=timeout)
        return locator

    @allure.step("Wait for element '{selector}' to be clickable")
    def wait_clickable(self, selector: str, timeout: int = 15000):
        self.logger.info(f"Waiting for clickability of: {selector}")
        locator = self.page.locator(selector)
        locator.wait_for(state="attached", timeout=timeout)
        return locator

    @allure.step("Type text '{value}' into '{selector}'")
    def type_text(self, selector: str, value: str, delay: int = 5):
        self.logger.info(f"Typing '{value}' into '{selector}'")
        locator = self.wait_visible(selector)
        locator.scroll_into_view_if_needed()
        locator.click()
        locator.press("Control+A")
        locator.press("Backspace")
        locator.clear()
        locator.press_sequentially(value, delay=delay)

    def safe_fill(self, locator, value):
        locator.click()
        locator.fill("")
        locator.fill(value)


    @allure.step("Click element '{selector}'")
    def click_element(self, selector: str):
        self.logger.info(f"Clicking element: {selector}")
        locator = self.wait_clickable(selector)
        locator.click()

    @allure.step("Answer question '{group_name}' with '{answer}'")
    def answer_question(self, group_name: str, answer: str):
        if not answer:
            return
        self.logger.info(f"Answering question '{group_name}' with '{answer}'")
        # This is th method for radio buttons(I will need to add comments later)
        answer = str(answer).strip()
        group = self.page.get_by_role("radiogroup", name=re.compile(group_name, re.I))
        radio = group.get_by_label(re.compile(f"^{answer}$", re.I))

        radio.dispatch_event("click")

    def read_summary(self, label_text: str) -> str:
        """
        Reads readonly/display value associated with a label.
        Example use case: Policy Number, Status, Payment Method.
        """
        if not label_text:
            return ""
        self.logger.info(f"Reading display value for label '{label_text}'")
        label_text = str(label_text).strip()
        # use Playwright accessibility mapping (aria-labelledby)
        element = self.page.get_by_label(label_text)
        value = element.inner_text().strip()
        return value


