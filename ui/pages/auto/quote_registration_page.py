from datetime import datetime, timedelta
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
        self.smart_fill(self.producer, data["Producer"])

    def fill_program(self, data):
        """Fill program field.

        Uses click + exact option match instead of smart_fill + Enter.
        Typing 'Homeowner' highlights 'Homeowners Association' first (prefix
        match), so Enter would select the wrong item. exact=True on the option
        role prevents that ambiguity. expect_response waits for the server
        reload triggered by the program selection.
        """
        value = data["Program"]
        self.program.scroll_into_view_if_needed()
        self.program.click()
        with self.page.expect_response("**/FieldProcessorServlet*"):
            self.page.get_by_role("option", name=value, exact=True).click()

    def set_effective_date(self, data):
        """Set effective date with offset from current date."""
        offset_days = int(data.get("EffDateOffset", 0))
        target_date = datetime.now() + timedelta(days=offset_days)
        formatted_date = target_date.strftime("%m/%d/%Y")
        self.smart_fill(self.effective_date, formatted_date)

    def click_next(self):
        """Proceed to next step."""
        self.smart_click(self.next_button)

    def wait_for_loader_to_disappear(self):
        self.spinner_wait("#ajax-sub-pre-loading")
