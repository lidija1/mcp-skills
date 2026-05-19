from ui.pages.common.base_page import BasePage


class GeneralLiabilityRiskAddressPage(BasePage):
    """General Liability risk-address gate."""

    def __init__(self, page):
        super().__init__(page)
        self.general_liability_option = page.get_by_role("option", name="General Liability")

    def risk_address_steps(self, data):
        self.ensure_general_liability_selected()
        self.wait_for_loader_to_disappear()

    def ensure_general_liability_selected(self):
        try:
            if self.general_liability_option.count() > 0:
                self.smart_click(self.general_liability_option)
                self.wait_for_loader_to_disappear()
        except Exception:
            self.logger.debug("General Liability option was not visible; continuing with the existing selection.")


