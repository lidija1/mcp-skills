from datetime import datetime, timedelta
import time

from ui.pages.common.base_page import BasePage


class QuoteRegistrationPage(BasePage):
    """Handles quote registration details."""
    
    def __init__(self, page):
        super().__init__(page)
        self.producer = page.get_by_role("combobox", name="Producer*")
        self.effective_date = page.get_by_role("combobox", name="Effective Date*")
        self.program = page.get_by_role("combobox", name="Program*")
        self.next_button = page.get_by_role("button", name="Next")

    def quote_registration_steps(self, data):
        """Perform quote registration steps."""
        self.fill_producer(data)
        self.fill_program(data)
        self.set_effective_date(data)
        self.click_next()
        self.wait_for_loader_to_disappear()

    def fill_producer(self, data):
        """Fill producer field."""
        self._open_and_select(self.producer, data["Producer"])
        self.wait_for_loader_to_disappear()

    def fill_program(self, data):
        """Fill program field.

        Uses visible ExtJS option matching instead of smart_fill + Enter.
        Typing 'Homeowner' highlights 'Homeowners Association' first (prefix
        match), so Enter would select the wrong item. Exact visible-text
        matching prevents that ambiguity.
        """
        self._open_and_select(self.program, data["Program"])
        self.wait_for_loader_to_disappear()

    def set_effective_date(self, data):
        """Set effective date with offset from current date."""
        offset_days = int(data.get("EffDateOffset", 0))
        target_date = datetime.now() + timedelta(days=offset_days)
        formatted_date = target_date.strftime("%m/%d/%Y")
        self.smart_fill(self.effective_date, formatted_date)

    def click_next(self):
        """Proceed to next step."""
        self.smart_click(self.next_button)

    def _open_and_select(self, locator, value):
        last_error = None
        for _ in range(3):
            try:
                self.select_extjs_option(locator, value)
                return
            except Exception as error:
                last_error = error
                self.page.keyboard.press("Escape")
                self.wait_for_loader_to_disappear()
                time.sleep(0.5)
        raise last_error
