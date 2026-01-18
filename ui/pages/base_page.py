import re

from playwright.sync_api import Page

class BasePage:
    def __init__(self, page: Page):
        self.page = page

    def wait_visible(self, selector: str, timeout: int = 15000):
        locator = self.page.locator(selector)
        locator.wait_for(state="visible", timeout=timeout)
        return locator

    def wait_clickable(self, selector: str, timeout: int = 15000):
        locator = self.page.locator(selector)
        locator.wait_for(state="attached", timeout=timeout)
        return locator

    def type_text(self, selector: str, value: str, delay: int = 20):
        """Standard fill can be too fast for OneShield, using sequential press."""
        locator = self.wait_visible(selector)
        locator.click()
        locator.fill(value)
        locator.press("Tab")


    def click_element(self, selector: str):
        locator = self.wait_clickable(selector)
        locator.click()

    def answer_question(self, group_name: str, answer: str):
        if not answer:
            return
        # This is th method for radio buttons(i will need to add comments later)
        answer = str(answer).strip()
        group = self.page.get_by_role("radiogroup", name=re.compile(group_name, re.I))
        radio = group.get_by_label(re.compile(f"^{answer}$", re.I))

        radio.dispatch_event("click")


