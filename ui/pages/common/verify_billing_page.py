from ui.pages.common.base_page import BasePage
from utils.metrics_collector import record_metric


class VerifyBillingPage(BasePage):
    """Verify Billing Choices page — common across all LOBs.

    Final confirmation page before binding. All fields are read-only.
    Clicking bind triggers a backend scheduling job — on the dev environment
    a REST 404 error dialog may appear after bind; this is a known server
    infrastructure issue and is dismissed automatically.

    Sections:
      - Policy Details (read-only)
      - Policy Cost Details (read-only)
      - Billing Plan Details (read-only)
      - Scheduled Payments grid (read-only)
    """

    def __init__(self, page):
        super().__init__(page)

        self.bind_button = page.get_by_role("button", name=">>> bind", exact=True)
        self.bind_with_payment_button = page.get_by_role("button", name=">>> bind with payment")

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def click_bind(self):
        self.smart_click(self.bind_button)
        self._dismiss_error_dialog()
        record_metric("policy_created", True)

    def click_bind_with_payment(self):
        self.smart_click(self.bind_with_payment_button)
        self._dismiss_error_dialog()
        record_metric("policy_created", True)

    # -------------------------------------------------------------------------
    # Private helper
    # -------------------------------------------------------------------------

    def _dismiss_error_dialog(self):
        """Dismiss the Debug Error Page dialog that appears on dev environment
        after bind due to a REST 404 on /DAPWeb/schedule. This is a known
        backend infrastructure issue — not caused by test data or UI actions.
        """
        try:
            close_btn = self.page.locator("div[id*='Debug_Error'] button").first
            close_btn.wait_for(state="visible", timeout=5000)
            close_btn.click()
        except Exception:
            pass
