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
        self.fill_program(data)
        self.fill_producer(data)
        self.set_effective_date(data)
        self.click_next()
        self.wait_for_loader_to_disappear()

    def fill_producer(self, data):
        """Fill producer field."""
        self.smart_fill(self.producer, data["Producer"])

    def fill_program(self, data):
        """Fill program field."""
        self.smart_click(self.program)
        self.smart_click(self.page.get_by_role("option", name=data["Program"], exact=True))
        self.page.expect_response("**/FieldProcessorServlet*")

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
