"""Underwriting Referral page object for Personal Auto."""
import allure

from ui.pages.common.base_page import BasePage


class UWReferralPage(BasePage):
    """
    Represents the Underwriting Referral page reached after a UW rule fires.

    The page contains an "underwriting issues" grid with one row per triggered
    rule.  Each row has columns: Asset | Condition | Type | Comments | Overridden?

    Page indicator: breadcrumb changes to "quote | underwriting referral | underwriter"
    when the redirect occurs.

    This page object:
      - Waits for the UW referral page breadcrumb to become visible.
      - Asserts that a specific condition keyword and rule type are present in
        the underwriting issues grid.
    """

    def __init__(self, page):
        super().__init__(page)
        # "Underwriting Issues" grid header is present on all UW pages
        # (both the "UNDERWRITING REFERRAL" breadcrumb path and the "HOMEOWNERS INTERNAL" path).
        self._uw_breadcrumb = page.locator("text=underwriting referral").or_(
            page.locator("text=Underwriting Issues")
        )

    # ------------------------------------------------------------------
    # Public assertion API
    # ------------------------------------------------------------------

    @allure.step("Assert UW condition: type='{uw_type}', condition contains='{expected_condition}'")
    def assert_uw_condition(self, uw_type: str, expected_condition: str) -> None:
        """
        Assert that the UW referral page is visible and the underwriting issues
        grid contains a row where:
          - The Condition column contains `expected_condition` (case-sensitive substring).
          - The Type column text matches `uw_type` (e.g. 'Hard-Stop', 'Underwriting').

        Raises:
            AssertionError: with a dump of all gridcell texts for debugging.
        """
        self._wait_for_uw_page()

        condition_cell = self.page.get_by_role("gridcell").filter(has_text=expected_condition)
        assert condition_cell.count() > 0, (
            f"UW condition not found.\n"
            f"  Expected condition : '{expected_condition}'\n"
            f"  Gridcells visible  :\n{self._dump_gridcells()}"
        )

        type_cell = self.page.get_by_role("gridcell").filter(has_text=uw_type)
        assert type_cell.count() > 0, (
            f"UW type not found.\n"
            f"  Expected type      : '{uw_type}'\n"
            f"  Gridcells visible  :\n{self._dump_gridcells()}"
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _wait_for_uw_page(self, timeout: int = 20_000) -> None:
        """Wait until the UW referral breadcrumb is visible in the toolbar."""
        self._uw_breadcrumb.first.wait_for(state="visible", timeout=timeout)

    def _dump_gridcells(self) -> str:
        """Return text content of every visible gridcell for assertion failure output."""
        cells = self.page.get_by_role("gridcell").all()
        lines = [f"    {cell.inner_text().strip()}" for cell in cells if cell.inner_text().strip()]
        return "\n".join(lines) if lines else "    (no gridcells found)"
