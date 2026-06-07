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

        self.payer_currency = page.get_by_role("combobox", name="Payer Currency")
        self.payment_plan = page.get_by_role("combobox", name="Payment Plan*")
        self.save_button = page.get_by_role("button", name="Save Changes")
        self.next_button = page.get_by_role("button", name=">>> next")

    # -------------------------------------------------------------------------
    # Main workflow method
    # -------------------------------------------------------------------------

    def complete_billing_plan(self, data):
        self.set_payer_currency(data)
        self.set_payment_plan(data)
        self.click_save()
        self.click_next()

    def inventory_dropdown_options(self):
        return {
            "PayerCurrency": self.collect_extjs_options(self.payer_currency),
            "PaymentPlan": self.collect_extjs_options(self.payment_plan),
        }

    def inventory_and_fill(self, data):
        options = {}
        options["PayerCurrency"] = self.collect_extjs_options(self.payer_currency)
        self.set_payer_currency(data)
        options["PaymentPlan"] = self.collect_extjs_options(self.payment_plan)
        self.set_payment_plan(data)
        self.click_save()
        self.click_next()
        return options

    # -------------------------------------------------------------------------
    # Field setters
    # -------------------------------------------------------------------------

    def set_payer_currency(self, data):
        payer_currency = data.get("PayerCurrency")
        if not payer_currency:
            return
        if self.payer_currency.count() == 0:
            return
        self._open_and_select(self.payer_currency, payer_currency)

    def set_payment_plan(self, data):
        self._open_and_select(self.payment_plan, data["PaymentPlan"])

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def click_save(self):
        self.with_optional_oneshield_response(lambda: self.smart_click(self.save_button))
        self.wait_for_app_ready()

    def click_next(self):
        self.with_optional_oneshield_response(lambda: self.smart_click(self.next_button))
        self.wait_for_app_ready()

    # -------------------------------------------------------------------------
    # Private helper for ExtJS dropdowns whose tooltips intercept pointer events.
    # -------------------------------------------------------------------------

    def _open_and_select(self, locator, value):
        self.select_extjs_option(locator, value)
