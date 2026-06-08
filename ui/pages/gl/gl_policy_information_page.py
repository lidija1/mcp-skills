from ui.pages.common.base_page import BasePage


class GeneralLiabilityBasicPolicyInformationPage(BasePage):
    """General Liability basic policy information page."""

    def __init__(self, page):
        super().__init__(page)

        self.billing_method = page.get_by_role("combobox", name="Billing Method*")
        self.audit_frequency = page.get_by_role("combobox", name="Audit Frequency*")
        self.loss_history = page.get_by_role("combobox", name="Have there been any losses in")
        self.policy_info_save_button = page.get_by_role("button", name="save changes")

    def basic_policy_information_steps(self, data):
        self.set_billing_method(data)
        self.set_audit_frequency(data)
        self.set_loss_history(data)
        self.click_policy_info_save()

    def inventory_dropdown_options(self):
        return {
            "BillingMethod": self.collect_extjs_options(self.billing_method),
            "AuditFrequency": self.collect_extjs_options(self.audit_frequency),
            "LossHistory": self.collect_extjs_options(self.loss_history),
        }

    def inventory_and_fill(self, data):
        options = self.inventory_dropdown_options()
        self.set_billing_method(data)
        self.set_audit_frequency(data)
        self.set_loss_history(data)
        self.click_policy_info_save()
        return options

    def set_billing_method(self, data):
        self.select_extjs_option(self.billing_method, data["BillingMethod"])
        self.wait_for_loader_to_disappear()

    def set_audit_frequency(self, data):
        self.select_extjs_option(self.audit_frequency, data["AuditFrequency"])
        self.wait_for_loader_to_disappear()

    def set_loss_history(self, data):
        self.select_extjs_option(self.loss_history, data["LossHistory"])
        self.wait_for_loader_to_disappear()

    def click_policy_info_save(self):
        self._click_and_wait(self.policy_info_save_button, wait_for_response=True)

