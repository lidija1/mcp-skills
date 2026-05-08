from ui.pages.common.base_page import BasePage


class CyberPremiumSummaryPage(BasePage):
    """Premium summary page reached after rating a Cyber quote.

    All fields are read-only. Main action is clicking 'request issue'
    to proceed to the delivery preferences / binding workflow.

    Sections:
      - Quote Details (Filing, Effective Date, Expiration Date, Product, Status)
      - Customer Details (Customer Name, Address, Phone, Email)
      - Agency Details (Agency Name, Agency Number, Address, Producer)
      - Premium Details (Premium, Surcharges, Fees, Taxes, Total Cost, Commission)
    """

    def __init__(self, page):
        super().__init__(page)

        # Read-only premium fields
        self.premium = page.get_by_role("textbox", name="Premium")
        self.total_cost = page.get_by_role("textbox", name="Total Cost")

        # Actions
        self.request_issue_button = page.get_by_role("button", name=">>> request issue")
        self.re_rate_button = page.get_by_role("button", name="re-rate")

    # -------------------------------------------------------------------------
    # Readers
    # -------------------------------------------------------------------------

    def get_premium(self):
        return self.read_summary("Premium")

    def get_total_cost(self):
        return self.read_summary("Total Cost")

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def click_request_issue(self):
        self.smart_click(self.request_issue_button)
        self.wait_for_app_ready()
