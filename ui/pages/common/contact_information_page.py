import re

from ui.pages.common.base_page import BasePage


class ContactInformationPage(BasePage):
    """Handles the post-UW Contact Information page."""

    def __init__(self, page):
        super().__init__(page)
        self.page_indicator = page.locator("text=Contact Information").or_(
            page.locator("text=Contact Permission")
        )
        self.contact_permission = page.get_by_role(
            "combobox",
            name=re.compile(r"contact.*permission", re.I),
        )
        self.email_option = page.get_by_label(re.compile(r"^email$", re.I))
        self.save_button = page.get_by_role("button", name=re.compile(r"^Save Changes$|^Save$", re.I))
        self.next_button = page.get_by_role("button", name=re.compile(r">>>\s*next", re.I))

    def is_visible(self, timeout: int = 3_000) -> bool:
        """Return whether the Contact Information page is currently visible."""
        try:
            self.page_indicator.first.wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return False

    def complete_email_permission_if_visible(self, timeout: int = 3_000) -> bool:
        """Select Email contact permission, save, and continue if this page is visible."""
        if not self.is_visible(timeout=timeout):
            return False

        self.select_contact_permission("Email")
        self.click_save()
        self.click_next()
        return True

    def select_contact_permission(self, value: str = "Email") -> None:
        """Set Contact Permission to the requested value."""
        if self.contact_permission.count() > 0:
            self.select_extjs_option(self.contact_permission.first, value)
            self.wait_for_app_ready()
            return

        if self.email_option.count() > 0:
            self.smart_click(self.email_option.first)
            self.wait_for_app_ready()
            return

        raise RuntimeError("Contact Permission control was not found on Contact Information page.")

    def click_save(self) -> None:
        self.with_optional_oneshield_response(lambda: self.smart_click(self.save_button.first))
        self.wait_for_app_ready()

    def click_next(self) -> None:
        self.with_optional_oneshield_response(lambda: self.smart_click(self.next_button.first))
        self.wait_for_app_ready()
