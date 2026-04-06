"""Performance tests for the New Quote creation workflow."""
import pytest
import allure
from ui.pages.common.performance.new_quote_performance_page import NewQuotePerformancePage as NewQuotePerfPage
from performance_tests.performance_config import PerformanceThresholds


@pytest.mark.performance
@pytest.mark.usefixtures("logged_in_for_new_quote")
class TestNewQuotePerformance:
    """Performance test suite for the New Quote workflow."""

    @pytest.mark.smoke
    def test_quotes_button_click_responsiveness(
        self, page, performance_metrics, performance_assertions, test_environment
    ):
        """Quotes nav button should respond within threshold."""
        quote_page = NewQuotePerfPage(page)

        with allure.step("Click Quotes button and measure response"):
            elapsed = quote_page.click_quotes_button_with_metrics(performance_metrics)

        threshold = PerformanceThresholds.get_threshold(test_environment, 'quotes_button_click_ms')

        with allure.step(f"Assert click time {elapsed:.2f}ms < {threshold:.2f}ms"):
            performance_assertions.assert_navigation_metric(elapsed, 'Quotes Button Click', threshold)

    def test_new_quote_button_click_responsiveness(
        self, page, performance_metrics, performance_assertions, test_environment
    ):
        """New Quote button click should load the form within threshold."""
        quote_page = NewQuotePerfPage(page)

        with allure.step("Navigate to quotes section"):
            quote_page.click_quotes_button_with_metrics(performance_metrics)

        with allure.step("Click New Quote button and measure response"):
            elapsed = quote_page.click_new_quote_button_with_metrics(performance_metrics)

        threshold = PerformanceThresholds.get_threshold(test_environment, 'new_quote_button_click_ms')

        with allure.step(f"Assert click time {elapsed:.2f}ms < {threshold:.2f}ms"):
            performance_assertions.assert_navigation_metric(elapsed, 'New Quote Button Click', threshold)

    def test_new_quote_form_visibility(
        self, page, performance_metrics, performance_assertions, test_environment
    ):
        """New Quote form elements should become visible within threshold."""
        quote_page = NewQuotePerfPage(page)

        with allure.step("Navigate to New Quote form"):
            quote_page.click_quotes_button_with_metrics(performance_metrics)

        with allure.step("Measure form element visibility time"):
            visibility_data = quote_page.wait_for_new_quote_with_metrics(performance_metrics)

        visibility_time = visibility_data.get('element_visibility_time', 0)
        threshold = PerformanceThresholds.get_threshold(test_environment, 'new_quote_form_visibility_ms')

        with allure.step(f"Assert visibility time {visibility_time:.2f}ms < {threshold:.2f}ms"):
            performance_assertions.assert_element_visibility_time(visibility_time, threshold)

    def test_full_new_quote_workflow_performance(
        self, page, performance_metrics, performance_assertions, test_environment
    ):
        """End-to-end new quote workflow should complete within threshold."""
        quote_page = NewQuotePerfPage(page)

        with allure.step("Step 1 — Click Quotes button"):
            quote_page.click_quotes_button_with_metrics(performance_metrics)

        with allure.step("Step 2 — Click New Quote button"):
            quote_page.click_new_quote_button_with_metrics(performance_metrics)

        with allure.step("Step 3 — Select Agent radio"):
            quote_page.click_radio_button_with_metrics(performance_metrics)

        with allure.step("Step 4 — Click Next and wait for Quote Registration page"):
            next_elapsed = quote_page.click_next_and_wait_for_page_with_metrics(performance_metrics)

        # Measures full navigation: Next click → Quote Registration page visible
        threshold = PerformanceThresholds.get_threshold(test_environment, 'next_button_click_ms')
        with allure.step(f"Assert Customer page load time after clicking next  {next_elapsed:.2f}ms < {threshold:.2f}ms"):
            performance_assertions.assert_navigation_metric(next_elapsed, 'Customer page load', threshold)