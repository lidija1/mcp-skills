import re
from ui.pages.common.base_page import BasePage


class QuoteSummaryPage(BasePage):
    """Handles quote summary information for auto insurance."""
    
    def __init__(self, page):
        super().__init__(page)
        self.quote_name = page.get_by_role("textbox", name="Quote Name")
        self.term = page.get_by_role("combobox", name="Term*", exact=True)
        self.effective_date = page.get_by_role(
            "combobox", name="Effective Date*", exact=True
        )
        self.expiration_date = page.get_by_role(
            "combobox", name="Expiration Date*", exact=True
        )
        self.net_of_commission = page.get_by_role(
            "combobox", name="Net of commission"
        )
        self.commission_basis = page.get_by_role(
            "combobox", name="Commission Basis"
        )
        self.billing = page.get_by_role("combobox", name="Billing Method*")
        self.prior_carrier = page.get_by_role(
            "combobox", name="Current/ Prior carrier"
        )
        self.prior_policy_term = page.get_by_role(
            "combobox", name="Term", exact=True
        )
        self.prior_policy_expiration_date = page.get_by_role(
            "combobox", name="Expiration Date", exact=True
        )
        self.prior_policy_premium = page.get_by_role(
            "textbox", name="Premium", exact=True
        )
        self.save_button = page.get_by_role("button", name="save changes")

    def summary_steps(self, data):
        """Perform quote summary steps."""
        self.fill_optional_quote_fields(data)
        self.set_billing(data)
        self.wait_for_loader_to_disappear()
        self.set_misleading_info(data)
        self.set_damage_info(data)
        self.click_save()
        self.click_driver_info_link(data)

    def fill_optional_quote_fields(self, data):
        """Fill configured optional quote and prior-policy fields."""
        self._set_optional_text(self.quote_name, data.get("QuoteName"))
        self._set_optional_combo(
            self.net_of_commission,
            data.get("NetOfCommission"),
        )
        self._set_optional_combo(
            self.commission_basis,
            data.get("CommissionBasis"),
        )
        self._set_optional_combo(self.prior_carrier, data.get("PriorCarrier"))
        self._set_optional_combo(
            self.prior_policy_term,
            data.get("PriorPolicyTerm"),
        )
        self._set_optional_text(
            self.prior_policy_expiration_date,
            data.get("PriorPolicyExpirationDate"),
        )
        self._set_optional_text(
            self.prior_policy_premium,
            data.get("PriorPolicyPremium"),
        )

    def _set_optional_combo(self, locator, value):
        if not value:
            return
        try:
            locator.first.wait_for(state="visible", timeout=2_000)
        except Exception:
            self.logger.info("Configured optional quote combobox is not visible; skipping.")
            return
        expected = str(value).strip()
        if locator.first.input_value().strip() == expected:
            return
        self.select_extjs_option(locator.first, expected)
        self.wait_for_app_ready()

    def _set_optional_text(self, locator, value):
        if not value:
            return
        try:
            locator.first.wait_for(state="visible", timeout=2_000)
        except Exception:
            self.logger.info("Configured optional quote field is not visible; skipping.")
            return
        self.smart_fill(locator.first, str(value))

    def set_billing(self, data):
        """Set billing method."""
        self.smart_fill(self.billing, data['BillingMethod'])

    def set_misleading_info(self, data):
        """Answer question about false/misleading information."""
        self.answer_question(
            "Has anyone knowingly provided material, false, or misleading information ",
            data["FalseInfo"]
        )

    def set_damage_info(self, data):
        """Answer question about existing vehicle damage, and describe it if required."""
        self.answer_question(
            "Does any vehicle have any existing damage?",
            data["DamageInfo"]
        )
        if data["DamageInfo"] == "Yes":
            describe_field = self.page.get_by_role("textbox", name="Describe Damage")
            self.smart_fill(describe_field, data.get("DescribeDamage", "Pre-existing damage noted"))

    def summary_steps_save_only(self, data):
        """
        Quote summary steps for UW hard-stop scenarios.

        Fills billing method and plan-eligibility flags then saves.
        Does NOT attempt to navigate to the driver info page, because a
        Hard-Stop UW rule redirects the page to the UW referral screen
        immediately after save — the driver link is never rendered.
        """
        self.fill_optional_quote_fields(data)
        self.set_billing(data)
        self.wait_for_loader_to_disappear()
        self.set_misleading_info(data)
        self.set_damage_info(data)
        self.click_save()

    def click_save(self):
        """Save changes."""
        self.smart_click(self.save_button)

    def click_driver_info_link(self, data):
        """Navigate to driver information page."""
        first_name = data["FirstName"]
        driver_info_link = self.page.get_by_role("link", name=re.compile(first_name, re.IGNORECASE))
        self.smart_click(driver_info_link)
