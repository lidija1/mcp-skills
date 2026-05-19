from ui.pages.common.base_page import BasePage


class DeliveryPreferencesPage(BasePage):
    """Delivery Preferences page — common across all LOBs.

    Appears after 'request issue' is clicked on the premium summary.
    Pre-filled with customer address from the quote. Main action is
    clicking next to proceed to the billing plan.

    Sections:
      - Policy Details (Product, Effective Date, Expiration Date)
      - Customer Details (Customer Name, Address, Billing Address, Email, Phone)
      - Document Delivery Preference grid (Customer, Document Type, Mode, Address)
      - Customer Primary Email
    """

    def __init__(self, page):
        super().__init__(page)

        self.next_button = page.get_by_role("button", name=">>> next")
        self.save_button = page.get_by_role("button", name="Save Changes")

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def click_next(self):
        self.smart_click(self.next_button)
        self.wait_for_app_ready()
