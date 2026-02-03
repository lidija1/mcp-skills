from ui.pages.common.base_page import BasePage


class NewQuotePage(BasePage):
    """Handles the new quote creation workflow."""
    
    def __init__(self, page):
        super().__init__(page)
        self.quotes_button = page.get_by_role('button', name='quotes')
        self.new_quotes_button = page.get_by_role("button", name=">>> new quote")
        self.agent_radio_button = "//span[@osviewid='PAI_304805_OT_63_OI_2_BI_381805_RS']"
        self.next_button = page.get_by_role("button", name=">>> next")

    def click_quotes_button(self):
        """Navigate to quotes section."""
        self.quotes_button.click()

    def click_new_quote_button(self):
        """Initiate new quote creation."""
        self.new_quotes_button.click()

    def click_agent_radio_button(self):
        """Select agent option."""
        self.click_element(self.agent_radio_button)

    def click_next_button(self):
        """Proceed to next step."""
        self.next_button.click()
