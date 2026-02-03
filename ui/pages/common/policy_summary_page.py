from ui.pages.common.base_page import BasePage


class PolicySummary(BasePage):
    """Handles the data extraction from summary page."""
    def __init__(self, page):
        super().__init__(page)

    def get_policy_number(self) -> str:
        return self.read_summary("Policy Number")

    def get_program(self) -> str:
        return self.read_summary("Program")

    def get_customer_name(self) -> str:
        return self.read_summary("Customer Name")

    def get_status(self) -> str:
        return self.read_summary("Status")

    def get_payment_method(self) -> str:
        return self.read_summary("Payment Method")

    def get_jurisdiction(self) -> str:
        return self.read_summary("Primary Jurisdiction")

    def get_premium(self) -> str:
        return self.read_summary("Total Policy Premium")

    def get_payment_plan(self) -> str:
        return self.read_summary("Payment Plan")