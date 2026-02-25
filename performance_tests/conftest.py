"""Performance test fixtures and configuration."""
import pytest
from utils.performance_metrics import PerformanceMetrics
from utils.performance_assertions import PerformanceAssertions
from performance_tests.performance_config import PerformanceThresholds, Environment


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

