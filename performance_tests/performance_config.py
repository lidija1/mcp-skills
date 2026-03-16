"""Performance test configuration and thresholds."""
import os
from enum import Enum


class Environment(Enum):
    """Environment types with different performance thresholds."""
    DEV = "dev"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class PerformanceThresholds:
    """Performance thresholds for different metrics and environments."""

    # Default thresholds (can be overridden per environment)
    THRESHOLDS = {
        Environment.DEV: {
            'page_load_time_ms': 5000,           # 5 seconds
            'splash_button_click_ms': 2000,      # 2 seconds
            'form_element_visibility_ms': 2000,  # 2 seconds
            'login_button_click_ms': 3000,       # 3 seconds
            'dns_lookup_ms': 1000,               # 1 second
            'tcp_connection_ms': 2000,           # 2 seconds
            'ttfb_ms': 2000,                     # 2 seconds (Time To First Byte)
            'max_resources': 100,                # Maximum number of resources
            'max_resource_size_kb': 5000,        # Maximum total resource size in KB
        },

        Environment.TESTING: {
            'page_load_time_ms': 7000, # 7 seconds (sllower because of network and backend on testing environment)
            'splash_button_click_ms': 3000,  # 3 seconds
            'form_element_visibility_ms': 3000,  # 3 seconds
            'login_button_click_ms': 4500, # 4.5 seconds (authentification often takes more time on testing environment)
            'dns_lookup_ms': 1500,  # 1.5 seconds (DNS lookup can be slower on testing environment)
            'tcp_connection_ms': 2500,  # 2.5 seconds (TCP connection can be slower on testing environment)
            'ttfb_ms': 3000,  # 3 seconds (Backend is usually slower on testing environment, so we allow more time for TTFB)
            'max_resources': 150, # We alow more resources on testing environment because of additional monitoring and debugging tools that can be loaded
            'max_resource_size_kb': 8000,  # 8 MB (Dubug logs and monitoring scripts can increase total resource size on testing environment, so we allow more)
        },

        Environment.STAGING: {
            'page_load_time_ms': 3000,           # 3 seconds
            'splash_button_click_ms': 1500,      # 1.5 seconds
            'form_element_visibility_ms': 1500,  # 1.5 seconds
            'login_button_click_ms': 2500,       # 2.5 seconds
            'dns_lookup_ms': 800,                # 0.8 seconds
            'tcp_connection_ms': 1500,           # 1.5 seconds
            'ttfb_ms': 1500,                     # 1.5 seconds
            'max_resources': 80,
            'max_resource_size_kb': 4000,
        },
        Environment.PRODUCTION: {
            'page_load_time_ms': 2000,           # 2 seconds
            'splash_button_click_ms': 1000,      # 1 second
            'form_element_visibility_ms': 1000,  # 1 second
            'login_button_click_ms': 2000,       # 2 seconds
            'dns_lookup_ms': 500,                # 0.5 seconds
            'tcp_connection_ms': 1000,           # 1 second
            'ttfb_ms': 1000,                     # 1 second
            'max_resources': 60,
            'max_resource_size_kb': 3000,
        },
    }

    @classmethod
    def get_threshold(cls, environment: Environment, metric: str) -> float:
        """Get threshold for a specific metric in an environment.

        Args:
            environment: Target environment
            metric: Metric name (e.g., 'page_load_time_ms')

        Returns:
            Threshold value
        """
        return cls.THRESHOLDS.get(environment, {}).get(metric, float('inf'))

    @classmethod
    def get_all_thresholds(cls, environment: Environment) -> dict:
        """Get all thresholds for an environment.

        Args:
            environment: Target environment

        Returns:
            Dictionary with all thresholds
        """
        return cls.THRESHOLDS.get(environment, {})

    @classmethod
    def get_current_environment(cls) -> Environment:
        """Get current environment from environment variables.

        Returns:
            Current environment (defaults to DEV if not specified)
        """
        env = os.getenv('TEST_ENV', 'testing').lower()
        try:
            return Environment(env)
        except ValueError:
            return Environment.DEV


# URL configuration
TEST_URLs = {
    Environment.TESTING: "https://inforce.oneshield.com/splash.html",
    # Environment.DEV: "https://inforcedev.oneshield.com/splash.html",
    # Environment.PRODUCTION: "https://inforce.oneshield.com/splash.html",
}


def get_test_url(environment: Environment) -> str:
    """Get test URL for an environment.

    Args:
        environment: Target environment

    Returns:
        Test URL
    """
    return TEST_URLs.get(environment, TEST_URLs[Environment.DEV])

