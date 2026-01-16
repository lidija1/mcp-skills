from ui.pages.base_page import BasePage

class newQuote(BasePage):
    def __init__(self, page):
        super().__init__(page)

        self.quotes_button = "//span[text()='quotes']"
        self.new_quotes_button = "//span[text()='>>> new quote']"
        self.agent_radio_buton = "//span[@osviewid='PAI_304805_OT_63_OI_2_BI_381805_RS']"
        self.next_button = "//span[text()='>>> next']"

    def click_quotes_button(self):
        self.click_element(self.quotes_button)

    def click_new_quote_button(self):
        self.click_element(self.new_quotes_button)

    def click_agent_radio_button(self):
        self.click_element(self.agent_radio_buton)

    def click_next_button(self):
        self.click_element(self.next_button)



