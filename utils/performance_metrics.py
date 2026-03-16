"""Performance metrics collector for Playwright tests."""
import time
import json
import allure
from datetime import datetime
from typing import Dict, List, Optional
from utils.logger import setup_logger


class PerformanceMetrics:
    """Collects and manages performance metrics during test execution."""

    def __init__(self, test_name: str = ""):
        """Initialize the performance metrics collector.

        Args:
            test_name: Name of the test for logging purposes
        """
        self.logger = setup_logger("PerformanceMetrics")
        self.test_name = test_name
        self.metrics: Dict = {}
        self.timers: Dict = {}
        self.start_time = None

    def start_timer(self, name: str) -> None:
        """Start a named timer.

        Args:
            name: Name of the timer
        """
        self.timers[name] = time.time()
        self.logger.info(f"Timer '{name}' started")

    def stop_timer(self, name: str) -> float:
        """Stop a named timer and return elapsed time in milliseconds.

        Args:
            name: Name of the timer

        Returns:
            Elapsed time in milliseconds
        """
        if name not in self.timers:
            self.logger.warning(f"Timer '{name}' was not started")
            return 0

        elapsed = (time.time() - self.timers[name]) * 1000
        self.timers[name] = elapsed  # Store elapsed ms so callers can read it back
        self.logger.info(f"Timer '{name}' stopped: {elapsed:.2f}ms")
        return elapsed

    def measure_navigation(self, page) -> Dict[str, float]:
        """Measure page navigation metrics.

        Args:
            page: Playwright page object

        Returns:
            Dictionary with navigation metrics
        """
        try:
            # Get navigation timing from page
            timing = page.evaluate("""
                () => {
                    const perf = window.performance.timing;
                    const perfData = {
                        'DNS': perf.domainLookupEnd - perf.domainLookupStart,
                        'TCP': perf.connectEnd - perf.connectStart,
                        'TTFB': perf.responseStart - perf.requestStart,
                        'Download': perf.responseEnd - perf.responseStart,
                        'DOM_Processing': perf.domComplete - perf.domLoading,
                        'DOM_Content_Loaded': perf.domContentLoadedEventEnd - perf.navigationStart,
                        'Page_Load': perf.loadEventEnd - perf.navigationStart,
                    };
                    return perfData;
                }
            """)

            self.metrics['navigation'] = timing
            self.logger.info(f"Navigation metrics: {timing}")
            return timing
        except Exception as e:
            self.logger.error(f"Failed to measure navigation metrics: {str(e)}")
            return {}

    def measure_resource_loading(self, page) -> List[Dict]:
        """Measure resource loading times.

        Args:
            page: Playwright page object

        Returns:
            List of resource timing data
        """
        try:
            resources = page.evaluate("""
                () => {
                    const resources = window.performance.getEntriesByType('resource');
                    return resources.map(resource => ({
                        'name': resource.name,
                        'duration': resource.duration,
                        'size': resource.transferSize || 0,
                        'type': resource.initiatorType
                    }));
                }
            """)

            self.metrics['resources'] = resources
            self.logger.info(f"Resource loading: {len(resources)} resources")
            return resources
        except Exception as e:
            self.logger.error(f"Failed to measure resource loading: {str(e)}")
            return []

    def measure_element_visibility(self, page, locator, timeout_ms: int = 10000) -> Dict[str, float]:
        """Measure time to element visibility.

        Args:
            page: Playwright page object
            locator: Element locator
            timeout_ms: Timeout in milliseconds

        Returns:
            Dictionary with visibility metrics
        """
        start = time.time()
        try:
            locator.wait_for(timeout=timeout_ms)
            elapsed = (time.time() - start) * 1000
            self.logger.info(f"Element visible in {elapsed:.2f}ms")
            return {'element_visibility_time': elapsed}
        except Exception as e:
            self.logger.error(f"Element not visible within timeout: {str(e)}")
            return {'element_visibility_time': timeout_ms}

    def measure_page_load_time(self, page) -> float:
        """Measure complete page load time.

        Args:
            page: Playwright page object

        Returns:
            Page load time in milliseconds
        """
        try:
            load_time = page.evaluate("""
                () => window.performance.timing.loadEventEnd - window.performance.timing.navigationStart
            """)
            self.logger.info(f"Page load time: {load_time}ms")
            self.metrics['page_load_time'] = load_time
            return load_time
        except Exception as e:
            self.logger.error(f"Failed to measure page load time: {str(e)}")
            return 0

    def get_metrics_summary(self) -> Dict:
        """Get a summary of all collected metrics.

        Returns:
            Dictionary with metrics summary
        """
        return {
            'test_name': self.test_name,
            'timestamp': datetime.now().isoformat(),
            'metrics': self.metrics
        }

    def attach_metrics_to_allure(self) -> None:
        """Attach performance metrics to Allure report."""
        summary = self.get_metrics_summary()
        allure.attach(
            json.dumps(summary, indent=2),
            name="Performance Metrics",
            attachment_type=allure.attachment_type.JSON
        )
        self.logger.info("Metrics attached to Allure report")

    def log_metrics_to_file(self, filepath: str) -> None:
        """Log metrics to a JSON file.

        Args:
            filepath: Path to save the metrics
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(self.get_metrics_summary(), f, indent=2)
            self.logger.info(f"Metrics saved to {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to save metrics to file: {str(e)}")

