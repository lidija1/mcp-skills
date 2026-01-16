from datetime import timedelta, datetime

from ui.pages.base_page import BasePage


class QuoteRegistration(BasePage):
    def __init__(self, page):
        super().__init__(page)

        self.producer = "//div[text()='Producer']/../../../..//input"
        self.effective_date = "//div[text()='Effective Date']/../../../..//input"
        self.program = "//div[text()='Program']/../../../..//input"
        self.next_button = "//span[text()='Next']"

    def fill_form(self, data):
        self.page.fill(self.producer, data["PRODUCER"])
        self.page.fill(self.program, data["PROGRAM"])

    def set_eff_date(self, data):
        # 1. Take value from dictionary and convert it in int (for every case if excel return string)
        offset_days = int(data.get("EffDateOffset", 0))
        # 2. Get the date
        # Calculate the effective date by shifting today by offset_days (can be negative for past dates).
        # datetime.now() returns the current date/time, timedelta(days=offset_days) represents the day offset,
        # and adding them produces the target date. Then we format it as "MM/DD/YYYY" for the UI input field.
        target_date = datetime.now() + timedelta(days=offset_days)
        formatted_date = target_date.strftime("%m/%d/%Y")

        self.page.fill(self.effective_date, formatted_date)


    def click_next(self):
        self.page.click(self.next_button)