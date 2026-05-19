import re
import json
import time
from typing import Dict, Any, Union, Tuple

import allure
from playwright.sync_api import Page, Locator

from utils.logger import setup_logger
from playwright.sync_api import TimeoutError as PWTimeout


class BasePage:
    def __init__(self, page: Page):
        self.page = page
        self.logger = setup_logger(self.__class__.__name__)

    # ═══════════════════════════════════════════════════════════════════════════
    # Smart Wrappers with Resilience & Metadata Capture
    # ═══════════════════════════════════════════════════════════════════════════

    def _resolve_target(self, target: Union[str, Locator]) -> Tuple[Locator, str]:
        """Normalize wrapper target to a Locator plus a readable label for logging."""
        if isinstance(target, Locator):
            # For Locator objects, extract a clean label from the internal selector
            try:
                # Playwright Locator has a _selector property we can use
                selector_str = target._selector if hasattr(target, '_selector') else str(target)
                # If it's still the verbose repr, just use a generic label
                if selector_str.startswith('<'):
                    selector_str = 'Locator'
                return target, selector_str
            except:
                return target, 'Locator'
        # For string selectors, use them as-is
        return self.page.locator(target), target

    def _capture_failure_metadata(self, selector: str, locator: Locator, error: Exception) -> Dict[str, Any]:
        """Capture DOM and locator metadata on failure for debugging."""
        metadata = {
            "selector": selector,
            "error": str(error),
            "error_type": type(error).__name__,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        try:
            # Capture element state
            metadata["is_visible"] = locator.is_visible()
            metadata["is_enabled"] = locator.is_enabled()
            metadata["is_editable"] = locator.is_editable()
            metadata["count"] = locator.count()
        except Exception as e:
            metadata["state_check_error"] = str(e)

        try:
            # Capture DOM attributes if element exists
            if locator.count() > 0:
                element = locator.first
                metadata["tag_name"] = element.evaluate("el => el.tagName")
                metadata["class"] = element.get_attribute("class")
                metadata["id"] = element.get_attribute("id")
                metadata["aria_label"] = element.get_attribute("aria-label")
                metadata["disabled"] = element.get_attribute("disabled")
                metadata["readonly"] = element.get_attribute("readonly")
                metadata["type"] = element.get_attribute("type")

                # Capture computed styles
                metadata["display"] = element.evaluate("el => window.getComputedStyle(el).display")
                metadata["visibility"] = element.evaluate("el => window.getComputedStyle(el).visibility")
                metadata["opacity"] = element.evaluate("el => window.getComputedStyle(el).opacity")

                # Capture bounding box
                bbox = element.bounding_box()
                metadata["bounding_box"] = bbox
        except Exception as e:
            metadata["dom_capture_error"] = str(e)

        # Log metadata
        self.logger.error(f"Element interaction failed: {json.dumps(metadata, indent=2)}")

        # Attach to Allure report
        allure.attach(
            json.dumps(metadata, indent=2),
            name=f"Failure_Metadata_{selector}",
            attachment_type=allure.attachment_type.JSON
        )

        return metadata

    def _wait_for_stability(self, locator: Locator, timeout: int = 2000) -> None:
        """Wait for element to be stable (not moving/changing)."""
        try:
            # Playwright's click already waits for actionability, but we can add explicit stability check
            locator.wait_for(state="visible", timeout=timeout)
            # Wait for element to stop moving (check bounding box stability)
            time.sleep(0.1)  # Small delay to ensure DOM has settled
        except Exception as e:
            self.logger.warning(f"Stability wait warning: {str(e)}")

    @allure.step("Clicked on: '{target}'")
    def smart_click(self, target: Union[str, Locator], timeout: int = 15000, max_retries: int = 2) -> None:
        """
        Smart click wrapper with:
        - Visibility check
        - Enabled check
        - Stability wait
        - Retry logic (2 attempts for transient UI conditions)
        - DOM + locator metadata capture on failure

        Args:
            target: CSS selector string or Playwright Locator
            timeout: Maximum wait time in milliseconds
            max_retries: Number of retry attempts (default: 2)
        """
        locator, target_label = self._resolve_target(target)

        for attempt in range(max_retries):
            try:
                self.logger.info(f"Smart click attempt {attempt + 1}/{max_retries}: {target_label}")

                # Step 1: Wait for visibility
                locator.wait_for(state="visible", timeout=timeout)

                # Step 2: Check if enabled (not disabled)
                if not locator.is_enabled():
                    raise AssertionError(f"Element is disabled: {target_label}")

                # Step 3: Wait for stability
                self._wait_for_stability(locator)

                # Step 4: Scroll into view if needed
                locator.scroll_into_view_if_needed()

                # Step 5: Perform click action
                locator.click(timeout=timeout)

                self.logger.info(f"Smart click successful: {target_label}")
                return  # Success - exit

            except Exception as e:
                self.logger.warning(f"Smart click attempt {attempt + 1} failed: {str(e)}")

                # Only retry for transient conditions
                if attempt < max_retries - 1:
                    # Brief wait before retry
                    time.sleep(0.5)
                else:
                    # Final attempt failed - capture metadata
                    metadata = self._capture_failure_metadata(target_label, locator, e)
                    raise AssertionError(
                        f"Smart click failed after {max_retries} attempts: {target_label}\n"
                        f"Last error: {str(e)}\n"
                        f"Metadata: {json.dumps(metadata, indent=2)}"
                    ) from e

    @allure.step("Smart Fill: '{target}' = '{value}'")
    def smart_fill(self, target: Union[str, Locator], value: str, timeout: int = 15000, max_retries: int = 2,
                   clear_first: bool = True, verify_fill: bool = True) -> None:
        """
        Smart fill wrapper with:
        - Visibility check
        - Enabled/Editable check
        - Stability wait
        - Retry logic (2 attempts for transient UI conditions)
        - Optional value verification
        - DOM + locator metadata capture on failure

        Args:
            target: CSS selector string or Playwright Locator
            value: Text to fill
            timeout: Maximum wait time in milliseconds
            max_retries: Number of retry attempts (default: 2)
            clear_first: Clear existing value before filling (default: True)
            verify_fill: Verify the value was filled correctly (default: True)
        """
        locator, target_label = self._resolve_target(target)

        for attempt in range(max_retries):
            try:
                self.logger.info(f"Smart fill attempt {attempt + 1}/{max_retries}: {target_label} = '{value}'")

                # Step 1: Wait for visibility
                locator.wait_for(state="visible", timeout=timeout)

                # Step 2: Check if enabled and editable
                if not locator.is_enabled():
                    raise AssertionError(f"Element is disabled: {target_label}")

                if not locator.is_editable():
                    raise AssertionError(f"Element is not editable: {target_label}")

                # Step 3: Wait for stability
                self._wait_for_stability(locator)

                # Step 4: Scroll into view if needed
                locator.scroll_into_view_if_needed()

                # Step 5: Click to focus
                locator.click(timeout=timeout)

                # Step 6: Clear existing value if requested
                if clear_first:
                    locator.fill("")  # Clear first

                # Step 7: Fill the value
                locator.fill(value, timeout=timeout)

                tag = locator.evaluate("el => el.tagName.toLowerCase()")
                if tag != "textarea":
                    locator.press("Enter")

                # Step 8: Verify fill if requested
                if verify_fill:
                    actual_value = locator.input_value().strip()
                    if actual_value != value.strip():
                        raise AssertionError(
                            f"Fill verification failed: expected '{value}', got '{actual_value}'"
                        )

                self.logger.info(f"Smart fill successful: {target_label} = '{value}'")
                return  # Success - exit

            except Exception as e:
                self.logger.warning(f"Smart fill attempt {attempt + 1} failed: {str(e)}")

                # Only retry for transient conditions
                if attempt < max_retries - 1:
                    # Brief wait before retry
                    time.sleep(0.5)
                else:
                    # Final attempt failed - capture metadata
                    metadata = self._capture_failure_metadata(target_label, locator, e)
                    raise AssertionError(
                        f"Smart fill failed after {max_retries} attempts: {target_label}\n"
                        f"Expected value: '{value}'\n"
                        f"Last error: {str(e)}\n"
                        f"Metadata: {json.dumps(metadata, indent=2)}"
                    ) from e

    @allure.step("Smart Type: '{value}'")
    def smart_type(self, target: Union[str, Locator], value: str, timeout: int = 15000, max_retries: int = 2,
                   delay: int = 50) -> None:
        """
        Smart type wrapper with character-by-character input (useful for fields with JS listeners).

        Args:
            target: CSS selector string or Playwright Locator
            value: Text to type
            timeout: Maximum wait time in milliseconds
            max_retries: Number of retry attempts (default: 2)
            delay: Delay between keystrokes in milliseconds (default: 50ms)
        """
        locator, target_label = self._resolve_target(target)

        for attempt in range(max_retries):
            try:
                self.logger.info(f"Smart type attempt {attempt + 1}/{max_retries}: {target_label} = '{value}'")

                # Step 1: Wait for visibility
                locator.wait_for(state="visible", timeout=timeout)

                # Step 2: Check if enabled and editable
                if not locator.is_enabled():
                    raise AssertionError(f"Element is disabled: {target_label}")

                if not locator.is_editable():
                    raise AssertionError(f"Element is not editable: {target_label}")

                # Step 3: Wait for stability
                self._wait_for_stability(locator)

                # Step 4: Scroll into view if needed
                locator.scroll_into_view_if_needed()

                # Step 5: Click to focus and clear
                locator.click(timeout=timeout)
                locator.press("Control+A")
                locator.press("Backspace")

                # Step 6: Type character by character
                locator.press_sequentially(value, delay=delay)
                locator.press("Enter")

                self.logger.info(f"Smart type successful: {target_label} = '{value}'")
                return  # Success - exit

            except Exception as e:
                self.logger.warning(f"Smart type attempt {attempt + 1} failed: {str(e)}")

                # Only retry for transient conditions
                if attempt < max_retries - 1:
                    # Brief wait before retry
                    time.sleep(0.5)
                else:
                    # Final attempt failed - capture metadata
                    metadata = self._capture_failure_metadata(target_label, locator, e)
                    raise AssertionError(
                        f"Smart type failed after {max_retries} attempts: {target_label}\n"
                        f"Expected value: '{value}'\n"
                        f"Last error: {str(e)}\n"
                        f"Metadata: {json.dumps(metadata, indent=2)}"
                    ) from e

    # ═══════════════════════════════════════════════════════════════════════════
    # Original Helper Methods
    # ═══════════════════════════════════════════════════════════════════════════

    @allure.step("Wait for element '{selector}' to be visible")
    def wait_visible(self, selector: str, timeout: int = 15000):
        self.logger.info(f"Waiting for visibility of: {selector}")
        locator = self.page.locator(selector)
        locator.wait_for(state="visible", timeout=timeout)
        return locator

    @allure.step("Wait for element '{selector}' to be clickable")
    def wait_clickable(self, selector: str, timeout: int = 15000):
        self.logger.info(f"Waiting for clickability of: {selector}")
        locator = self.page.locator(selector)
        locator.wait_for(state="attached", timeout=timeout)
        return locator

    @allure.step("Type text '{value}' into '{selector}'")
    def type_text(self, selector: str, value: str, delay: int = 5):
        self.logger.info(f"Typing '{value}' into '{selector}'")
        locator = self.wait_visible(selector)
        locator.scroll_into_view_if_needed()
        locator.click()
        locator.press("Control+A")
        locator.press("Backspace")
        locator.clear()
        locator.press_sequentially(value, delay=delay)

    def safe_fill(self, locator, value):
        locator.click()
        locator.fill("")
        locator.fill(value)


    @allure.step("Click element '{selector}'")
    def click_element(self, selector: str):
        self.logger.info(f"Clicking element: {selector}")
        locator = self.wait_clickable(selector)
        locator.click()

    @allure.step("Answer question '{group_name}' with '{answer}'")
    def answer_question(self, group_name: str, answer: str):
        if not answer:
            return
        self.logger.info(f"Answering question '{group_name}' with '{answer}'")
        # This is th method for radio buttons(I will need to add comments later)
        answer = str(answer).strip()
        group = self.page.get_by_role("radiogroup", name=re.compile(group_name, re.I))
        radio = group.get_by_label(re.compile(f"^{answer}$", re.I))

        radio.dispatch_event("click")

    def read_summary(self, label_text: str) -> str:
        """
        Reads readonly/display value associated with a label.
        Example use case: Policy Number, Status, Payment Method.
        """
        if not label_text:
            return ""
        self.logger.info(f"Reading display value for label '{label_text}'")
        label_text = str(label_text).strip()
        # use Playwright accessibility mapping (aria-labelledby)
        element = self.page.get_by_label(label_text)
        value = element.inner_text().strip()
        return value

    def spinner_wait(self, selector: str, timeout: int = 60000):
        """Wait for a loading spinner to disappear."""
        self.logger.info(f"Waiting for spinner '{selector}' to disappear")
        try:
            self.page.wait_for_selector(selector, state="hidden", timeout=timeout)
        except PWTimeout:

            raise AssertionError('TEST FAILED: Loading mask is still visible after timeout')
        self.logger.info('Spinner has disappeared')

    def wait_for_app_ready(self, timeout: int = 60000):
        """Wait for common OneShield loading masks to clear."""
        self.spinner_wait("#ajax-sub-pre-loading", timeout=timeout)
        self.spinner_wait("css=.x-mask", timeout=timeout)

    def wait_for_loader_to_disappear(self):
        self.wait_for_app_ready()

    def _click_and_wait(self, locator, wait_for_response=False):
        if wait_for_response:
            self.with_optional_oneshield_response(lambda: self.smart_click(locator))
        else:
            self.smart_click(locator)
        self.wait_for_app_ready()

    def wait_for_oneshield_response(self, timeout: int = 10000, url_parts=None):
        """Wait for a OneShield business response when an action triggers server work."""
        url_parts = url_parts or ()

        def matches(response):
            if response.status >= 400:
                return False
            if url_parts:
                return any(part in response.url for part in url_parts)
            resource_type = response.request.resource_type
            return (
                "oneshield" in response.url.lower()
                and resource_type in {"xhr", "fetch", "document"}
            )

        response = self.page.wait_for_response(matches, timeout=timeout)
        self.logger.info(f"Observed OneShield response: {response.status} {response.url}")
        return response

    def with_optional_oneshield_response(self, action, timeout: int = 10000, url_parts=None):
        """Run an action and observe the backend response when the app emits one."""
        action_error = None
        try:
            with self.page.expect_response(
                lambda response: self._matches_oneshield_response(response, url_parts),
                timeout=timeout,
            ) as response_info:
                try:
                    result = action()
                except Exception as error:
                    action_error = error
                    raise
            response = response_info.value
            self.logger.info(f"Observed OneShield response: {response.status} {response.url}")
            return result
        except PWTimeout:
            if action_error:
                raise action_error
            self.logger.debug("No OneShield response observed within the timeout window.")
            return None

    def _matches_oneshield_response(self, response, url_parts=None):
        if response.status >= 400:
            return False
        if url_parts:
            return any(part in response.url for part in url_parts)
        resource_type = response.request.resource_type
        return (
            "oneshield" in response.url.lower()
            and resource_type in {"xhr", "fetch", "document"}
        )

    def select_extjs_option(
        self,
        locator: Locator,
        value: str,
        wait_for_response: bool = False,
        response_timeout: int = 10000,
        url_parts=None,
    ):
        """Select an ExtJS combobox option by exact visible text."""
        last_error = None

        for _ in range(3):
            try:
                locator.scroll_into_view_if_needed()
                locator.click()

                visible_items_js = (
                    "() => [...document.querySelectorAll('.x-boundlist-item')]"
                    ".some(el => { const r = el.getBoundingClientRect();"
                    " return r.width > 0 && r.height > 0; })"
                )
                try:
                    self.page.wait_for_function(visible_items_js, timeout=3000)
                except Exception:
                    self.page.keyboard.press("ArrowDown")
                    self.page.wait_for_function(visible_items_js, timeout=5000)

                def click_option():
                    return self.page.evaluate(
                        """(text) => {
                            const items = [...document.querySelectorAll('.x-boundlist-item')];
                            const visible = items.filter(el => {
                                const r = el.getBoundingClientRect();
                                const style = window.getComputedStyle(el);
                                return r.width > 0 && r.height > 0
                                    && style.visibility !== 'hidden'
                                    && style.display !== 'none';
                            });
                            const match = visible.find(el => el.textContent.trim() === text);
                            if (match) match.click();
                            else throw new Error('Option not found: ' + text);
                        }""",
                        value
                    )

                if wait_for_response:
                    self.with_optional_oneshield_response(
                        click_option,
                        timeout=response_timeout,
                        url_parts=url_parts,
                    )
                else:
                    click_option()
                return
            except Exception as error:
                last_error = error
                self.page.keyboard.press("Escape")
                self.wait_for_app_ready()
                time.sleep(0.5)
        raise last_error

    def collect_extjs_options(self, locator: Locator, timeout: int = 5000):
        """Return the currently visible ExtJS option texts for a combobox."""
        locator.scroll_into_view_if_needed()
        locator.click()

        visible_items_js = (
            "() => [...document.querySelectorAll('.x-boundlist-item')]"
            ".filter(el => { const r = el.getBoundingClientRect();"
            " const style = window.getComputedStyle(el);"
            " return r.width > 0 && r.height > 0 && style.visibility !== 'hidden' && style.display !== 'none'; })"
            ".map(el => (el.textContent || '').replace(/\\s+/g, ' ').trim())"
            ".filter(Boolean)"
        )

        try:
            self.page.wait_for_function(
                "() => [...document.querySelectorAll('.x-boundlist-item')]"
                ".some(el => { const r = el.getBoundingClientRect();"
                " return r.width > 0 && r.height > 0; })",
                timeout=timeout,
            )
        except Exception:
            self.page.keyboard.press("ArrowDown")
            self.page.wait_for_function(
                "() => [...document.querySelectorAll('.x-boundlist-item')]"
                ".some(el => { const r = el.getBoundingClientRect();"
                " return r.width > 0 && r.height > 0; })",
                timeout=timeout,
            )

        options = self.page.evaluate(visible_items_js)
        self.page.keyboard.press("Escape")
        return options

    def collect_radio_options(self, group_name: str):
        """Return visible radio option labels for a named radiogroup."""
        group = self.page.get_by_role("radiogroup", name=re.compile(group_name, re.I))
        radios = group.get_by_role("radio")
        options = []

        for index in range(radios.count()):
            radio = radios.nth(index)
            if not radio.is_visible():
                continue
            label = (
                radio.get_attribute("aria-label")
                or radio.get_attribute("value")
                or (radio.text_content() or "").strip()
            )
            label = " ".join(label.split())
            if label:
                options.append(label)

        return options

    def collect_visible_role_texts(self, role: str):
        """Return visible text content for all elements matching a Playwright role."""
        locators = self.page.get_by_role(role)
        items = []

        for index in range(locators.count()):
            item = locators.nth(index)
            if not item.is_visible():
                continue
            text = (
                item.get_attribute("aria-label")
                or (item.text_content() or "").strip()
            )
            text = " ".join(text.split())
            if text:
                items.append(text)

        return items


