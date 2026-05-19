import pytest
import allure
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from utils.logger import setup_logger
from utils.api_flow_recorder import ApiFlowRecorder

load_dotenv()


# -------------------------
# Session configuration for parallel test support
# -------------------------
def pytest_configure(config):
    """Initialize session storage for test results (supports parallel execution)."""
    # Use config object to store results - this survives parallel worker processes
    config.test_results = []
    config.addinivalue_line("markers", "parallel: mark test as able to run in parallel")


def pytest_collection_finish(session):
    """Log the number of tests collected."""
    total_items = len(session.items)
    print(f"\n[PYTEST COLLECTION] Total tests collected: {total_items}")


# -------------------------
# Register plugins and fixtures with pytest
# -------------------------
# Using string-based plugin registration ensures pytest properly discovers and registers all fixtures
pytest_plugins = [
    "ui.fixtures",
    "ui.steps.common.auth_steps",
    "ui.steps.common.login_validation_steps",
    "ui.steps.common.data_steps",
    "ui.steps.common.field_steps",
    "ui.steps.auto.auto_workflow_steps",
    "ui.steps.homeowner_steps",
    "ui.steps.common.customer_validation_steps",
    "ui.steps.cyber_steps",
    "ui.steps.wc_steps",
    "ui.steps.general_liability_steps",
]


# -------------------------
# Register custom command-line options
# -------------------------# -------------------------
def pytest_addoption(parser):
    parser.addoption(
        "--browser",
        action="store",
        default="chromium",
        help="Specify the browser to use: chromium, firefox, webkit, chrome, or msedge"
    )
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Run tests in headed mode (show browser window)"
    )
    parser.addoption(
        "--slow-mo",
        action="store",
        default=0,
        type=int,
        help="Slow down operations by specified milliseconds"
    )
    parser.addoption(
        "--pw-trace",
        action="store",
        default="off",
        choices=["off", "on"],
        help="Playwright tracing mode: off or on"
    )
    parser.addoption(
        "--api-flow-map",
        action="store",
        default=None,
        help="Write captured page-to-API flow traffic to the given JSON path"
    )
    parser.addoption(
        "--api-flow-include-static",
        action="store_true",
        default=False,
        help="Include static browser resources in --api-flow-map output"
    )

# -------------------------
# Logger
# -------------------------
@pytest.fixture(scope="session")
def log():
    return setup_logger("PlaywrightTest")

# -------------------------
# Browser name fixture
# -------------------------
@pytest.fixture(scope="session")
def browser_name(request):
    browser = request.config.getoption("--browser", default="chromium")
    valid_browsers = ["chromium", "firefox", "webkit", "chrome", "msedge"]

    # if isinstance(browser, list):
    #     if len(browser) > 0 and browser[0] in valid_browsers:
    #         return browser[0]
    #     else:
    #         pytest.fail(f"Invalid browser specified in list: {browser}")

    if browser not in valid_browsers:
        pytest.fail(f"Invalid browser specified: {browser}. Valid options are: {valid_browsers}")

    return browser if browser else "chromium"


# -------------------------
# Playwright instance
# -------------------------
@pytest.fixture(scope="session")
def playwright():
    with sync_playwright() as p:
        yield p

# -------------------------
# Browser instance (per session)
# -------------------------
@pytest.fixture(scope="session")
def browser(playwright, browser_name, request):
    # Chrome and Edge are Chromium channels, not separate engines
    channel_map = {
        "chrome": "chrome",
        "msedge": "msedge",
    }

    if browser_name in channel_map:
        browser_type = playwright.chromium
        channel = channel_map[browser_name]
    else:
        browser_type = {
            "chromium": playwright.chromium,
            "firefox": playwright.firefox,
            "webkit": playwright.webkit,
        }.get(browser_name)
        channel = None

    if not browser_type:
        raise ValueError(f"Unsupported browser: {browser_name}")

    # Get headed and slow_mo options from command line
    headed = request.config.getoption("--headed")
    slow_mo = request.config.getoption("--slow-mo")

    launch_args = {"headless": not headed, "slow_mo": slow_mo}
    if channel:
        launch_args["channel"] = channel

    browser = browser_type.launch(**launch_args)

    yield browser
    browser.close()

# -------------------------
# Context (per test)
# -------------------------
@pytest.fixture(scope="function")
def context(browser, request):
    context = browser.new_context(
        viewport=None  # full screen
    )

    trace_mode = request.config.getoption("--pw-trace")
    if trace_mode != "off":
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

    yield context

    if trace_mode != "off":
        traces_dir = Path("reports") / "traces"
        traces_dir.mkdir(parents=True, exist_ok=True)
        test_name = request.node.nodeid.replace("::", "__").replace("/", "_").replace("\\", "_")
        trace_path = traces_dir / f"{test_name}.zip"
        context.tracing.stop(path=str(trace_path))

    context.close()

# -------------------------
# Page (per test)
# -------------------------
@pytest.fixture(scope="function")
def page(context):
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture(scope="function")
def api_flow_recorder(page, request):
    """Opt-in network recorder for mapping UI flow pages to backend calls."""
    recorder = ApiFlowRecorder(
        page=page,
        output_path=request.config.getoption("--api-flow-map"),
        enabled=bool(request.config.getoption("--api-flow-map")),
        include_static=request.config.getoption("--api-flow-include-static"),
    )
    recorder.start()
    yield recorder
    output_path = recorder.finish()
    if output_path:
        print(f"\n[API FLOW MAP] Wrote network capture to {output_path}")

# -------------------------
# Test data passthrough
# -------------------------
@pytest.fixture
def data(test_data):
    return test_data

# -------------------------
# Session finish hook
# -------------------------

# def pytest_sessionfinish():
#     """
#     This method is executed automatically at the end of the tests.
#     """
#     print("\n" + "=" * 30)
#     print("Generating business report...")
#
#     try:
#         # Calling the function to generate the trend chart
#         generate_trend_chart("policy_summary/policy_reports.csv")
#         print("Graph is generated successfully!")
#     except Exception as e:
#         print(f"Error generating graph: {e}")
#
#     print("=" * 30)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook to capture screenshot on failure and attach it to Allure report.
    Everytime when test outcome is not passed, take screenshot and attach to Allure report.
    """
    outcome = yield
    report = outcome.get_result()

    # Capture screenshot if test failed (report.failed = True means test did not pass)
    # Skip screenshot for API tests (marked with @pytest.mark.api)
    if report.when == "call" and report.failed:
        # Check if test is marked as API test
        is_api_test = any(mark.name == 'api' for mark in item.iter_markers())

        if is_api_test:
            # Skip screenshot for API tests
            return

        page = None

        # Try to get the page fixture from funcargs
        # First, check if 'page' is directly available in funcargs (common for UI tests)
        # Funcargs is a dictionary of fixture values that are available for the test function.
        # If 'page' is one of the fixtures used in the test, it will be present in funcargs.
        if hasattr(item, 'funcargs') and 'page' in item.funcargs:
            page = item.funcargs.get("page")

        # If not found in funcargs, try to get it from the fixture request
        # Some tests might not use 'page' directly as a fixture but might have it available through the request object.
        if not page and hasattr(item, '_request'):
            try:
                page = item._request.getfixturevalue("page")
            except Exception:
                pass

        # Capture and attach screenshot if page is available
        if page:
            try:
                # Take screenshot as bytes (no need to save to file)
                screenshot_bytes = page.screenshot(full_page=True)

                # Attach screenshot directly from bytes in Allure report
                allure.attach(
                    screenshot_bytes,
                    name=f"Failure_{item.name}",
                    attachment_type=allure.attachment_type.PNG
                )
                print(f"\n Screenshot captured for failed test: {item.name}")
            except Exception as e:
                print(f"\n Failed to capture screenshot for {item.name}: {str(e)}")
