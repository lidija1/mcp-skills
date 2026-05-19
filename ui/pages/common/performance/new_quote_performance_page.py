import allure

from performance_tests.performance_metrics import PerformanceMetrics
from ui.pages.common.base_page import BasePage


class NewQuotePerformancePage(BasePage):

    def __init__(self, page):
        super().__init__(page)
        self.quotes_button = page.get_by_role('button', name='quotes')
        self.new_quotes_button = page.get_by_role("button", name=">>> new quote")
        self.agent_radio_button = "//span[@osviewid='PAI_304805_OT_63_OI_2_BI_381805_RS']"
        self.next_button = page.get_by_role("button", name=">>> next")
        # First visible element on Create Customer page — used as page-ready signal
        self.customer_search_button = page.get_by_role("button", name=">>> Search")

    @allure.step("Click Quotes button with metrics")
    def click_quotes_button_with_metrics(self, metrics: PerformanceMetrics) -> float:
       metrics.start_timer("quotes_button_click")
       self.smart_click(self.quotes_button)
       elapsed = metrics.stop_timer("quotes_button_click")
       self.logger.info(f"Quotes button clicked in {elapsed:.2f}ms")
       return elapsed

    @allure.step("Click New Quote button with metrics")
    def click_new_quote_button_with_metrics(self, metrics: PerformanceMetrics) -> float:
       metrics.start_timer("new_quote_button_click")
       self.smart_click(self.new_quotes_button)
       elapsed = metrics.stop_timer("new_quote_button_click")
       self.logger.info(f"New Quote button clicked in {elapsed:.2f}ms")
       return elapsed

    @allure.step("Click Agent radio button with metrics")
    def click_radio_button_with_metrics(self, metrics: PerformanceMetrics) -> float:
        metrics.start_timer("agent_radio_button_click")
        self.click_element(self.agent_radio_button)
        elapsed = metrics.stop_timer("agent_radio_button_click")
        self.logger.info(f"Agent radio button clicked in {elapsed:.2f}ms")
        return elapsed

    @allure.step("Click Next button with metrics")
    def click_next_button_with_metrics(self, metrics: PerformanceMetrics) -> float:
        metrics.start_timer("next_button_click")
        self.smart_click(self.next_button)
        elapsed = metrics.stop_timer("next_button_click")
        self.logger.info(f"Next button clicked in {elapsed:.2f}ms")
        return elapsed

    @allure.step("Wait for new quote form to be visible with metrics")
    def wait_for_new_quote_with_metrics(self, metrics: PerformanceMetrics, timeout_ms: int = 15000) -> dict:
        visibility_metrics = metrics.measure_element_visibility(
            self.page,
            self.new_quotes_button,
            timeout_ms = timeout_ms
        )
        self.logger.info(
            f"New quote is visible in "
            f"{visibility_metrics.get('element_visibility_time', 0):.2f}ms"
        )
        return visibility_metrics

    @allure.step("Click Next and wait for Create Customer page to load (with metrics)")
    def click_next_and_wait_for_page_with_metrics(
        self, metrics: PerformanceMetrics, timeout_ms: int = 30000
    ) -> float:
        """Measure the full transition time: Next button click → Create Customer page ready.

        Timer starts before the click and stops only when the Search button
        on the Customer page becomes visible — capturing true navigation time.

        Args:
            metrics: PerformanceMetrics instance to collect data
            timeout_ms: Max time to wait for the next page (default 30s)

        Returns:
            Elapsed time in milliseconds
        """
        self.logger.info("Clicking Next and waiting for Create Customer page...")
        metrics.start_timer("next_to_page_load")
        self.next_button.click()
        self.customer_search_button.wait_for(state="visible", timeout=timeout_ms)
        elapsed = metrics.stop_timer("next_to_page_load")
        self.logger.info(f"Create Customer page ready in {elapsed:.2f}ms")
        return elapsed
