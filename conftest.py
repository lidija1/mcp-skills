import pytest
import allure
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from utils.logger import setup_logger
from utils.policy_reporter import generate_trend_chart

load_dotenv()


def pytest_addoption(parser):
    parser.addoption(
        "--browser",
        action="store",
        default="chromium",
        choices=["chromium", "firefox", "webkit", "chrome", "msedge"],
        help="Browser to use for tests: chromium, firefox, webkit, chrome, msedge",
    )

# Plugin list for fixtures and step definitions
pytest_plugins = [
    "fixtures.ui_fixtures",
    "ui.steps.auth_steps",
    "ui.steps.data_steps",
    "ui.steps.auto_workflow_steps",
    "ui.steps.customer_validation_steps",
    ]

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
    return request.config.getoption("--browser")


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
def browser(playwright, browser_name):
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

    launch_args = {"headless": True, "slow_mo": 100}
    if channel:
        launch_args["channel"] = channel

    browser = browser_type.launch(**launch_args)

    yield browser
    browser.close()

# -------------------------
# Context (per test)
# -------------------------
@pytest.fixture(scope="function")
def context(browser):
    context = browser.new_context(
        viewport=None  # full screen
    )
    yield context
    context.close()

# -------------------------
# Page (per test)
# -------------------------
@pytest.fixture(scope="function")
def page(context):
    page = context.new_page()
    yield page
    page.close()

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
                print(f"\n📸 Screenshot captured for failed test: {item.name}")
            except Exception as e:
                print(f"\n⚠️ Failed to capture screenshot for {item.name}: {str(e)}")
