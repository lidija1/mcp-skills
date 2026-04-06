from ui.pages.common.base_page import BasePage


class BillingPlanPage(BasePage):
    """Billing Plan page — common across all LOBs.

    Appears after delivery preferences. Requires selecting a payment plan
    before saving and proceeding to verify billing choices.

    Sections:
      - Policy Details (read-only)
      - Policy Cost Details (read-only)
      - Bill Plan Details (Billing Plan Name, Default Name checkbox)
      - Payment Method (radio: same method / different down payment)
      - Payment Frequency (Payer Currency, Payment Plan*)
      - Scheduled Payments grid (auto-populated after plan selection)
    """

    def __init__(self, page):
        super().__init__(page)

        self.payment_plan = page.get_by_role("combobox", name="Payment Plan*")
        self.save_button = page.get_by_role("button", name="Save Changes")
        self.next_button = page.get_by_role("button", name=">>> next")

    # -------------------------------------------------------------------------
    # Main workflow method
    # -------------------------------------------------------------------------

    def complete_billing_plan(self, data):
        self.set_payment_plan(data)
        self.click_save()
        self.click_next()

    # -------------------------------------------------------------------------
    # Field setters
    # -------------------------------------------------------------------------

    def set_payment_plan(self, data):
        self._open_and_select(self.payment_plan, data["PaymentPlan"])

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def click_save(self):
        self.smart_click(self.save_button)
        self.spinner_wait("css=.x-mask")

    def click_next(self):
        self.smart_click(self.next_button)
        self.spinner_wait("css=.x-mask")

    # -------------------------------------------------------------------------
    # Private helper — same ExtJS tooltip workaround as CyberQuotePage
    # -------------------------------------------------------------------------

    def _open_and_select(self, locator, value):
        locator.click()
        try:
            self.page.wait_for_selector(".x-boundlist-item:visible", timeout=3000)
        except Exception:
            self.page.keyboard.press("ArrowDown")
            self.page.wait_for_selector(".x-boundlist-item", timeout=5000)

        self.page.evaluate(
            """(text) => {
                const items = [...document.querySelectorAll('.x-boundlist-item')];
                const visible = items.filter(el => {
                    const r = el.getBoundingClientRect();
                    return r.width > 0 && r.height > 0;
                });
                const match = visible.find(el => el.textContent.trim() === text);
                if (match) match.click();
                else throw new Error('Option not found: ' + text);
            }""",
            value
        )
