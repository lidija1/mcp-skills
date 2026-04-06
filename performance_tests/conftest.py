"""Performance test fixtures and configuration."""
import pytest
from playwright.sync_api import expect

from performance_tests.performance_metrics import PerformanceMetrics
from performance_tests.performance_assertions import PerformanceAssertions
from performance_tests.performance_config import PerformanceThresholds
from ui.pages.common.performance.new_quote_performance_page import NewQuotePerformancePage


@pytest.fixture
def performance_metrics(request):
    """Fixture to provide performance metrics collector.

    Yields:
        PerformanceMetrics instance configured for the test
    """
    test_name = request.node.name
    metrics = PerformanceMetrics(test_name)
    yield metrics
    # Attach metrics to Allure report after test
    metrics.attach_metrics_to_allure()


@pytest.fixture
def performance_assertions():
    """Fixture to provide performance assertions helper.

    Returns:
        PerformanceAssertions instance
    """
    return PerformanceAssertions()


@pytest.fixture
def performance_thresholds():
    """Fixture to provide performance thresholds.

    Returns:
        PerformanceThresholds class
    """
    return PerformanceThresholds


@pytest.fixture
def test_environment():
    """Fixture to get current test environment.

    Returns:
        Current Environment
    """
    return PerformanceThresholds.get_current_environment()


@pytest.fixture
def logged_in_for_new_quote(login_page, page):
    """Authenticate and land on the post-login page where Quotes is available."""
    login_page.navigate()
    login_page.click_splash_button()
    login_page.wait_for_login_page()
    login_page.fill_credentials_from_env()
    login_page.click_login()

    quote_page = NewQuotePerformancePage(page)
    expect(quote_page.quotes_button).to_be_visible(timeout=20000)
    return quote_page


