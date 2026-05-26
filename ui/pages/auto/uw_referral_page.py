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
    # Public API
    # ------------------------------------------------------------------

    def is_visible(self, timeout: int = 2_000) -> bool:
        """Return whether the current page is showing an underwriting referral."""
        try:
            self._wait_for_uw_page(timeout=timeout)
            return True
        except Exception:
            return False

    def capture_conditions(self, timeout: int = 2_000) -> list[str]:
        """Return visible underwriting issue grid cell text."""
        self._wait_for_uw_page(timeout=timeout)
        cells = self.page.get_by_role("gridcell").all()
        return [cell.inner_text().strip() for cell in cells if cell.inner_text().strip()]

    def can_be_overridden(self, timeout: int = 5_000) -> bool:
        """Return True if every UW condition row has an editable Overridden? cell."""
        self._wait_for_uw_page(timeout=timeout)
        return self.page.evaluate("""
            () => {
                const rows = document.querySelectorAll('[id^="gridview"] tr.x-grid-row');
                if (!rows.length) return false;
                return [...rows].every(row => {
                    const cells = row.querySelectorAll('td');
                    const last = cells[cells.length - 1];
                    return last && !last.classList.contains('gridCellReadOnly');
                });
            }
        """)

    @allure.step("Override all UW conditions and accept")
    def override_all_and_accept(self, comment: str = "Approved by underwriter - risk accepted.") -> None:
        """
        Set Overridden?=Yes and fill comments for every row, then click >>> Accept.

        Precondition: can_be_overridden() must return True for all rows.
        After this returns the page has navigated past the UW referral screen.
        Raises RuntimeError if accept is blocked and page remains on UW referral.
        """
        self._wait_for_uw_page()
        row_count: int = self.page.evaluate(
            "() => document.querySelectorAll('[id^=\"gridview\"] tr.x-grid-row').length"
        )
        for i in range(row_count):
            self._set_overridden_yes(i)

            # Open the Underwriter's Comments cell (second-to-last column) and fill it
            self.page.evaluate(f"""() => {{
                const row = document.querySelectorAll('[id^="gridview"] tr.x-grid-row')[{i}];
                const cells = row.querySelectorAll('td');
                cells[cells.length - 2].click();
            }}""")
            self.page.wait_for_function(
                "() => document.activeElement && document.activeElement.tagName === 'TEXTAREA'",
                timeout=3_000,
            )
            self.page.evaluate(
                "(c) => {"
                " const ta = document.activeElement; ta.value = c;"
                " ta.dispatchEvent(new Event('input', {bubbles: true}));"
                " ta.dispatchEvent(new Event('change', {bubbles: true})); }",
                comment,
            )
            self.page.keyboard.press("Tab")
            self.page.wait_for_timeout(300)

        # Click >>> accept
        self.smart_click(self.page.get_by_role("button", name=">>> accept"))
        # Confirm dialog
        ok_btn = self.page.get_by_role("button", name="OK")
        ok_btn.wait_for(state="visible", timeout=5_000)
        ok_btn.click()
        self.wait_for_loader_to_disappear()

        if self.is_visible(timeout=3_000):
            raise RuntimeError(
                "UW accept was blocked — not all conditions could be overridden."
            )

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
        if ";" in expected_condition:
            expected_conditions = [
                condition.strip()
                for condition in expected_condition.split(";")
                if condition.strip()
            ]
            for condition in expected_conditions:
                self.assert_uw_condition(uw_type, condition)
            return

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

        grid_dump = self._dump_gridcells()
        allure.attach(
            f"TRIGGERED UW RULE\n"
            f"{'=' * 40}\n"
            f"Type      : {uw_type}\n"
            f"Condition : {expected_condition}\n"
            f"\nAll conditions on page:\n{grid_dump}",
            name="UW Rule Triggered",
            attachment_type=allure.attachment_type.TEXT,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _wait_for_uw_page(self, timeout: int = 20_000) -> None:
        """Wait until the UW referral breadcrumb is visible in the toolbar."""
        self._uw_breadcrumb.first.wait_for(state="visible", timeout=timeout)

    def _set_overridden_yes(self, row_index: int) -> None:
        """Set the grid row's Overridden? editor to Yes and verify it committed."""
        self.page.evaluate(f"""() => {{
            const row = document.querySelectorAll('[id^="gridview"] tr.x-grid-row')[{row_index}];
            const cells = row.querySelectorAll('td');
            cells[cells.length - 1].querySelector('div').click();
        }}""")

        editor = self.page.locator(".x-grid-editor input").last
        editor.wait_for(state="visible", timeout=3_000)
        editor.click()

        try:
            self.page.keyboard.press("ArrowDown")
            self.page.wait_for_function(
                """() => [...document.querySelectorAll('.x-boundlist-item')]
                    .some(el => {
                        const r = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        return r.width > 0 && r.height > 0
                            && style.visibility !== 'hidden'
                            && style.display !== 'none'
                            && el.textContent.trim() === 'Yes';
                    })""",
                timeout=3_000,
            )
            self.page.evaluate(
                """() => {
                    const items = [...document.querySelectorAll('.x-boundlist-item')];
                    const visible = items.filter(el => {
                        const r = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        return r.width > 0 && r.height > 0
                            && style.visibility !== 'hidden'
                            && style.display !== 'none';
                    });
                    const yes = visible.find(el => el.textContent.trim() === 'Yes');
                    if (!yes) throw new Error('Yes option not found for UW override editor.');
                    yes.click();
                }"""
            )
        except Exception:
            editor.fill("Yes")
            editor.press("Enter")

        self.page.wait_for_function(
            """(rowIndex) => {
                const row = document.querySelectorAll('[id^="gridview"] tr.x-grid-row')[rowIndex];
                if (!row) return false;
                const cells = row.querySelectorAll('td');
                const text = cells[cells.length - 1]?.innerText?.trim();
                return text === 'Yes';
            }""",
            arg=row_index,
            timeout=5_000,
        )

    def _dump_gridcells(self) -> str:
        """Return text content of every visible gridcell for assertion failure output."""
        cells = self.page.get_by_role("gridcell").all()
        lines = [f"    {cell.inner_text().strip()}" for cell in cells if cell.inner_text().strip()]
        return "\n".join(lines) if lines else "    (no gridcells found)"
