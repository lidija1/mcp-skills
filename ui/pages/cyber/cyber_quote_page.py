from ui.pages.common.base_page import BasePage


class CyberQuotePage(BasePage):
    """Cyber insurance LOB quote details page.

    Covers all sections visible on the Cyber quote details tab:
      - Basic Policy Information
      - Business Details
      - Policy Coverages
      - Optional Coverages
      - Common Eligibility
    """

    def __init__(self, page):
        super().__init__(page)

        # Basic Policy Information
        self.billing_method = page.get_by_role("combobox", name="Billing Method*")

        # Business Details
        self.business_start_date = page.get_by_role("textbox", name="Business Start Date*")
        self.total_employees = page.get_by_role("textbox", name="Total Number of Employees*")
        self.nature_of_business = page.get_by_role("combobox", name="Nature of Business*")
        self.pct_online_sales = page.get_by_role("textbox", name="Percentage Annual Online Sales*")

        # Policy Coverages
        self.aggregate_limit = page.get_by_role("combobox", name="Aggregate Limit*")
        self.per_claim_limit = page.get_by_role("combobox", name="Per Claim Limit*")
        self.per_claim_deductible = page.get_by_role("combobox", name="Per Claim Deductible*")

        # Optional Coverages
        self.business_interruption = page.get_by_role("textbox", name="Business Interruption")
        self.cyber_extortion = page.get_by_role("textbox", name="Cyber Extortion")

        # Common Eligibility
        self.cyber_training = page.get_by_role(
            "combobox",
            name="Does the company conduct cyber security training for its employees?*"
        )
        self.situations_last_3_years = page.get_by_role(
            "combobox",
            name="Has the Company experienced any of the following situations within the last three years?*"
        )
        self.cyber_regulations = page.get_by_role(
            "combobox",
            name="Does the company have cyber security regulations in place as per the jurisdictional guidelines?*"
        )

        # Actions
        self.save_button = page.get_by_role("button", name="save changes")
        self.rate_quote_button = page.get_by_role("button", name=">>> rate quote")

    # -------------------------------------------------------------------------
    # Main workflow method
    # -------------------------------------------------------------------------

    def fill_cyber_quote_details(self, data):
        self.set_billing_method(data)
        self.set_business_start_date(data)
        self.set_total_employees(data)
        self.set_nature_of_business(data)
        self.set_pct_online_sales(data)
        self.set_aggregate_limit(data)
        self.set_per_claim_limit(data)
        self.set_per_claim_deductible(data)
        self.set_cyber_training(data)
        self.set_situations_last_3_years(data)
        self.set_cyber_regulations(data)
        self.click_save()

    # -------------------------------------------------------------------------
    # Field setters
    # -------------------------------------------------------------------------

    def set_billing_method(self, data):
        self._open_and_select(self.billing_method, data["BillingMethod"])

    def set_business_start_date(self, data):
        # Field accepts 4-digit year only (e.g. "2010")
        self.smart_fill(self.business_start_date, data["BusinessStartDate"])

    def set_total_employees(self, data):
        self.smart_fill(self.total_employees, data["TotalEmployees"])

    def set_nature_of_business(self, data):
        self._open_and_select(self.nature_of_business, data["NatureOfBusiness"])

    def set_pct_online_sales(self, data):
        self.smart_fill(self.pct_online_sales, data["PctOnlineSales"])

    def set_aggregate_limit(self, data):
        self._open_and_select(self.aggregate_limit, data["AggregateLimit"])

    def set_per_claim_limit(self, data):
        self._open_and_select(self.per_claim_limit, data["PerClaimLimit"])

    def set_per_claim_deductible(self, data):
        self._open_and_select(self.per_claim_deductible, data["PerClaimDeductible"])

    def set_cyber_training(self, data):
        self._open_and_select(self.cyber_training, data["CyberTraining"])

    def set_situations_last_3_years(self, data):
        self._open_and_select(self.situations_last_3_years, data["SituationsLast3Years"])

    def set_cyber_regulations(self, data):
        self._open_and_select(self.cyber_regulations, data["CyberRegulations"])

    def click_save(self):
        self.smart_click(self.save_button)
        self.wait_for_app_ready()

    def click_rate_quote(self):
        self.smart_click(self.rate_quote_button)
        self.wait_for_app_ready()

    # -------------------------------------------------------------------------
    # Private helper: open dropdown and select by visible text using JS click.
    # ExtJS tooltips intercept pointer events, so we bypass by clicking the
    # underlying DOM element directly once the dropdown list is visible.
    # -------------------------------------------------------------------------

    def _open_and_select(self, locator, value):
        """Open an ExtJS combobox and select an option by its visible text.

        Uses JS to click the matching .x-boundlist-item because tooltips
        frequently intercept Playwright pointer events on this application.
        """
        locator.scroll_into_view_if_needed()
        locator.click()
        # Wait until at least one boundlist item has non-zero dimensions
        # (bounding box check avoids false matches from stale hidden items)
        _VISIBLE_ITEMS_JS = (
            "() => [...document.querySelectorAll('.x-boundlist-item')]"
            ".some(el => { const r = el.getBoundingClientRect();"
            " return r.width > 0 && r.height > 0; })"
        )
        try:
            self.page.wait_for_function(_VISIBLE_ITEMS_JS, timeout=3000)
        except Exception:
            self.page.keyboard.press("ArrowDown")
            self.page.wait_for_function(_VISIBLE_ITEMS_JS, timeout=5000)

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
