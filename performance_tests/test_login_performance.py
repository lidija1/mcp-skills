"""Performance tests for login page functionality."""
import statistics
import time
import pytest
import allure
from ui.pages.common.login_page import LoginPage
from performance_tests.performance_metrics import PerformanceMetrics
from performance_tests.performance_config import PerformanceThresholds


@pytest.mark.performance
class TestLoginPagePerformance:
    """Test suite for login page performance metrics."""

    @pytest.mark.smoke
    def test_login_page_load_time(self, page, performance_metrics, performance_assertions, test_environment):
        """Test that login page loads within acceptable time.

        This test measures:
        - Initial page load time from navigation start to load complete
        - Page load time should be < threshold for the current environment
        """
        login_page = LoginPage(page)

        with allure.step("Navigate to login page and measure load time"):
            login_page.navigate_with_metrics(performance_metrics)

        page_load_time = performance_metrics.metrics.get('page_load_time', 0)
        threshold = PerformanceThresholds.get_threshold(test_environment, 'page_load_time_ms')

        with allure.step(f"Assert page load time {page_load_time:.2f}ms < {threshold:.2f}ms"):
            performance_assertions.assert_page_load_time(page_load_time, threshold)

    def test_navigation_metrics(self, page, performance_metrics, performance_assertions, test_environment):
        """Test navigation phase metrics (DNS, TCP, TTFB).

        Measures:
        - DNS lookup time
        - TCP connection time
        - Time to First Byte (TTFB)
        """
        login_page = LoginPage(page)

        with allure.step("Navigate to login page and capture navigation metrics"):
            login_page.navigate_with_metrics(performance_metrics)

        nav_metrics = performance_metrics.metrics.get('navigation', {})

        with allure.step("Verify DNS lookup time"):
            dns_time = nav_metrics.get('DNS', 0)
            dns_threshold = PerformanceThresholds.get_threshold(test_environment, 'dns_lookup_ms')
            performance_assertions.assert_navigation_metric(dns_time, 'DNS', dns_threshold)

        with allure.step("Verify TCP connection time"):
            tcp_time = nav_metrics.get('TCP', 0)
            tcp_threshold = PerformanceThresholds.get_threshold(test_environment, 'tcp_connection_ms')
            performance_assertions.assert_navigation_metric(tcp_time, 'TCP', tcp_threshold)

        with allure.step("Verify Time to First Byte (TTFB)"):
            ttfb = nav_metrics.get('TTFB', 0)
            ttfb_threshold = PerformanceThresholds.get_threshold(test_environment, 'ttfb_ms')
            performance_assertions.assert_navigation_metric(ttfb, 'TTFB', ttfb_threshold)

    def test_resource_loading_performance(self, page, performance_metrics, performance_assertions, test_environment):
        """Test resource loading performance.

        Measures:
        - Number of resources loaded
        - Total size of all resources
        - Individual resource load times
        """
        login_page = LoginPage(page)

        with allure.step("Navigate to login page and measure resource loading"):
            login_page.navigate_with_metrics(performance_metrics)

        resources = performance_metrics.metrics.get('resources', [])

        with allure.step(f"Verify resource count ({len(resources)} resources)"):
            max_resources = PerformanceThresholds.get_threshold(test_environment, 'max_resources')
            performance_assertions.assert_resource_count(len(resources), int(max_resources))

        with allure.step("Verify total resource size"):
            total_size = sum(r.get('size', 0) for r in resources)
            max_size_kb = PerformanceThresholds.get_threshold(test_environment, 'max_resource_size_kb')
            performance_assertions.assert_total_resource_size(total_size, max_size_kb)

        # Log resource details
        with allure.step("Log resource loading details"):
            resource_summary = f"Resources loaded: {len(resources)}\nTotal size: {total_size / 1024:.2f}KB\n\nDetailed resources:\n"
            for resource in resources[:10]:  # Log first 10 resources
                resource_summary += f"\n- {resource.get('name', 'unknown')}: {resource.get('duration', 0):.2f}ms"
            if len(resources) > 10:
                resource_summary += f"\n... and {len(resources) - 10} more resources"
            allure.attach(resource_summary, name="Resource Loading Summary", attachment_type=allure.attachment_type.TEXT)

    def test_splash_button_click_responsiveness(self, page, performance_metrics, performance_assertions, test_environment):
        """Test splash button click responsiveness.

        Measures:
        - Time to click splash button and load next page
        - Should be responsive (<= splash_button_click_ms threshold)
        """
        login_page = LoginPage(page)

        with allure.step("Navigate to splash page"):
            login_page.navigate_with_metrics(performance_metrics)

        with allure.step("Click splash button and measure responsiveness"):
            login_page.click_splash_button_with_metrics(performance_metrics)

        click_time = performance_metrics.timers.get('splash_button_click', 0)
        if click_time == 0:
            # If timer not found, check the last recorded time
            click_time = list(performance_metrics.metrics.values())[-1] if performance_metrics.metrics else 0

        threshold = PerformanceThresholds.get_threshold(test_environment, 'splash_button_click_ms')
        performance_assertions.assert_navigation_metric(click_time, 'Splash Button Click', threshold)

    def test_form_element_visibility_performance(self, page, performance_metrics, performance_assertions, test_environment):
        """Test form element visibility performance.

        Measures:
        - Time for form elements (partner number field) to become visible
        - Should be visible within element_visibility_ms threshold
        """
        login_page = LoginPage(page)

        with allure.step("Navigate to login page"):
            login_page.navigate_with_metrics(performance_metrics)

        with allure.step("Click splash button"):
            login_page.click_splash_button()

        with allure.step("Measure form element visibility time"):
            login_page.wait_for_login_page_with_metrics(performance_metrics)

        visibility_time = performance_metrics.metrics.get('element_visibility_time', 0)
        threshold = PerformanceThresholds.get_threshold(test_environment, 'form_element_visibility_ms')

        if visibility_time > 0:
            performance_assertions.assert_element_visibility_time(visibility_time, threshold)

    def test_login_form_interaction_performance(self, page, performance_metrics, performance_assertions, test_environment):
        """Test performance of filling login form.

        Measures:
        - Time to fill all form fields
        - Form responsiveness while entering credentials
        """
        login_page = LoginPage(page)

        with allure.step("Navigate to login page"):
            login_page.navigate_with_metrics(performance_metrics)

        with allure.step("Click splash button"):
            login_page.click_splash_button()

        with allure.step("Wait for form to load"):
            login_page.wait_for_login_page()

        with allure.step("Fill credentials and measure form interaction time"):
            login_page.fill_credentials_from_env_with_metrics(performance_metrics)

        fill_time = performance_metrics.timers.get('fill_credentials', 0)
        if fill_time > 0:
            threshold = PerformanceThresholds.get_threshold(test_environment, 'form_element_visibility_ms')
            with allure.step(f"Verify form fill time is reasonable"):
                performance_assertions.assert_navigation_metric(fill_time, 'Form Fill', threshold)

    def test_login_submission_performance(self, page, performance_metrics, performance_assertions, test_environment):
        """Test login button submission performance.

        Measures:
        - Time from clicking login to response
        - Should complete within login_button_click_ms threshold
        """
        login_page = LoginPage(page)

        with allure.step("Navigate to login page"):
            login_page.navigate_with_metrics(performance_metrics)

        with allure.step("Click splash button"):
            login_page.click_splash_button()

        with allure.step("Wait for form to load"):
            login_page.wait_for_login_page()

        with allure.step("Fill credentials"):
            login_page.fill_credentials_from_env()

        with allure.step("Click login button and measure submission time"):
            login_page.click_login_with_metrics(performance_metrics)

        submit_time = performance_metrics.timers.get('login_click', 0)
        threshold = PerformanceThresholds.get_threshold(test_environment, 'login_button_click_ms')

        if submit_time > 0:
            performance_assertions.assert_navigation_metric(submit_time, 'Login Submission', threshold)

    @pytest.mark.stress
    def test_login_page_load_under_repeated_access(self, page, performance_metrics, performance_assertions, test_environment):
        """Test login page performance under repeated access.

        Measures:
        - Consistency of page load times
        - Browser caching effectiveness
        """
        login_page = LoginPage(page)
        load_times = []

        with allure.step("Load login page 3 times and measure load times"):
            for i in range(3):
                with allure.step(f"Load iteration {i + 1}"):
                    perf = PerformanceMetrics(f"login_load_{i+1}")
                    login_page.navigate_with_metrics(perf)
                    load_time = perf.metrics.get('page_load_time', 0)
                    load_times.append(load_time)

                    threshold = PerformanceThresholds.get_threshold(test_environment, 'page_load_time_ms')
                    performance_assertions.assert_page_load_time(load_time, threshold)

        with allure.step("Verify load time consistency"):
            avg_time = sum(load_times) / len(load_times)
            load_time_summary = f"Load times (ms): {[f'{t:.2f}' for t in load_times]}\nAverage: {avg_time:.2f}ms"
            allure.attach(load_time_summary, name="Load Time Consistency", attachment_type=allure.attachment_type.TEXT)

            # Second load should benefit from caching (optional assertion)
            if load_times[1] < load_times[0]:
                allure.step(f"✓ Browser caching effective: Load 2 ({load_times[1]:.2f}ms) < Load 1 ({load_times[0]:.2f}ms)")

    def test_login_to_home_page_load_time(self, browser, request):
        """Measure time from login button click until the home page is ready.

        Runs the full login flow 3 times (fresh context per run) and reports
        the median elapsed time. 'Ready' is defined as the 'quotes' button
        becoming visible on the home dashboard.
        """
        runs = 3
        durations = []

        for i in range(1, runs + 1):
            with allure.step(f"Run {i}/{runs} — full login cycle"):
                ctx = browser.new_context(viewport=None)
                pg = ctx.new_page()
                login_page = LoginPage(pg)

                login_page.navigate()
                login_page.click_splash_button()
                login_page.wait_for_login_page()
                login_page.fill_credentials_from_env()

                # --- start measuring here ---
                t_start = time.perf_counter()
                login_page.click_login()
                pg.get_by_role("button", name="quotes").wait_for(state="visible", timeout=30000)
                elapsed_ms = (time.perf_counter() - t_start) * 1000
                # --- end measuring here ---

                durations.append(elapsed_ms)
                print(f"\n  Run {i}: {elapsed_ms:.0f} ms")

                pg.close()
                ctx.close()

        median_ms = statistics.median(durations)
        summary = (
            f"Run 1 : {durations[0]:.0f} ms\n"
            f"Run 2 : {durations[1]:.0f} ms\n"
            f"Run 3 : {durations[2]:.0f} ms\n"
            f"Median: {median_ms:.0f} ms"
        )
        print(f"\n{'='*40}\nLogin -> Home Page Load Time\n{summary}\n{'='*40}")
        allure.attach(summary, name="Login -> Home Page Load Time (3 runs)", attachment_type=allure.attachment_type.TEXT)

