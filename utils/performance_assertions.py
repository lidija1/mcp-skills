"""Performance assertions and validation utilities."""
import allure
from typing import Dict, Optional
from utils.logger import setup_logger


class PerformanceAssertions:
    """Assertions for performance metrics."""

    def __init__(self):
        """Initialize performance assertions helper."""
        self.logger = setup_logger("PerformanceAssertions")

    def assert_page_load_time(self, actual_time: float, threshold_ms: float) -> bool:
        """Assert page load time is within threshold.

        Args:
            actual_time: Actual load time in milliseconds
            threshold_ms: Threshold in milliseconds

        Returns:
            True if assertion passes

        Raises:
            AssertionError if assertion fails
        """
        with allure.step(f"Assert page load time {actual_time:.2f}ms < {threshold_ms:.2f}ms"):
            if actual_time > threshold_ms:
                error_msg = f"Page load time {actual_time:.2f}ms exceeds threshold {threshold_ms:.2f}ms"
                self.logger.error(error_msg)
                allure.attach(
                    f"Expected: < {threshold_ms:.2f}ms\nActual: {actual_time:.2f}ms\nDifference: {actual_time - threshold_ms:.2f}ms",
                    name="Load Time Assertion Failed",
                    attachment_type=allure.attachment_type.TEXT
                )
                raise AssertionError(error_msg)

            self.logger.info(f"✓ Page load time assertion passed: {actual_time:.2f}ms < {threshold_ms:.2f}ms")
            return True

    def assert_element_visibility_time(self, actual_time: float, threshold_ms: float) -> bool:
        """Assert element visibility time is within threshold.

        Args:
            actual_time: Actual visibility time in milliseconds
            threshold_ms: Threshold in milliseconds

        Returns:
            True if assertion passes
        """
        with allure.step(f"Assert element visibility {actual_time:.2f}ms < {threshold_ms:.2f}ms"):
            if actual_time > threshold_ms:
                error_msg = f"Element visibility time {actual_time:.2f}ms exceeds threshold {threshold_ms:.2f}ms"
                self.logger.error(error_msg)
                allure.attach(
                    f"Expected: < {threshold_ms:.2f}ms\nActual: {actual_time:.2f}ms",
                    name="Visibility Time Assertion Failed",
                    attachment_type=allure.attachment_type.TEXT
                )
                raise AssertionError(error_msg)

            self.logger.info(f"✓ Element visibility assertion passed: {actual_time:.2f}ms < {threshold_ms:.2f}ms")
            return True

    def assert_navigation_metric(self, metric_value: float, metric_name: str, threshold_ms: float) -> bool:
        """Assert navigation metric is within threshold.

        Args:
            metric_value: Metric value in milliseconds
            metric_name: Name of the metric (e.g., 'DNS', 'TCP', 'TTFB')
            threshold_ms: Threshold in milliseconds

        Returns:
            True if assertion passes
        """
        with allure.step(f"Assert {metric_name} {metric_value:.2f}ms < {threshold_ms:.2f}ms"):
            if metric_value > threshold_ms:
                error_msg = f"{metric_name} metric {metric_value:.2f}ms exceeds threshold {threshold_ms:.2f}ms"
                self.logger.error(error_msg)
                raise AssertionError(error_msg)

            self.logger.info(f"✓ {metric_name} assertion passed: {metric_value:.2f}ms < {threshold_ms:.2f}ms")
            return True

    def assert_resource_count(self, actual_count: int, max_count: int) -> bool:
        """Assert number of resources is within limit.

        Args:
            actual_count: Actual number of resources
            max_count: Maximum allowed number of resources

        Returns:
            True if assertion passes
        """
        with allure.step(f"Assert resource count {actual_count} <= {max_count}"):
            if actual_count > max_count:
                error_msg = f"Resource count {actual_count} exceeds limit {max_count}"
                self.logger.error(error_msg)
                raise AssertionError(error_msg)

            self.logger.info(f"✓ Resource count assertion passed: {actual_count} <= {max_count}")
            return True

    def assert_total_resource_size(self, actual_size: float, max_size_kb: float) -> bool:
        """Assert total resource size is within limit.

        Args:
            actual_size: Actual total size in bytes
            max_size_kb: Maximum allowed size in kilobytes

        Returns:
            True if assertion passes
        """
        actual_kb = actual_size / 1024
        with allure.step(f"Assert total resource size {actual_kb:.2f}KB <= {max_size_kb:.2f}KB"):
            if actual_kb > max_size_kb:
                error_msg = f"Total resource size {actual_kb:.2f}KB exceeds limit {max_size_kb:.2f}KB"
                self.logger.error(error_msg)
                raise AssertionError(error_msg)

            self.logger.info(f"✓ Resource size assertion passed: {actual_kb:.2f}KB <= {max_size_kb:.2f}KB")
            return True

