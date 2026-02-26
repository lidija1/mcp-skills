import pytest
import allure
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from utils.logger import setup_logger
from utils.policy_reporter import generate_trend_chart

load_dotenv()

# Plugin list for fixtures and step definitions
pytest_plugins = [
    "fixtures.ui_fixtures",
    "ui.steps.auth_steps",
    "ui.steps.data_steps",
    "ui.steps.auto_workflow_steps",
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
    browser = request.config.getoption("--browser", default="chromium")
    valid_browsers = ["chromium", "firefox", "webkit"]

    if isinstance(browser, list):
        if len(browser) > 0 and browser[0] in valid_browsers:
            return browser[0]
        else:
            pytest.fail(f"Invalid browser specified in list: {browser}")

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
def browser(playwright, browser_name):
    browser_type = {
        "chromium": playwright.chromium,
        "firefox": playwright.firefox,
        "webkit": playwright.webkit,
    }.get(browser_name)

    if not browser_type:
        raise ValueError(f"Unsupported browser: {browser_name}")

    browser = browser_type.launch(
        headless=False,
        slow_mo=100
    )

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

def pytest_sessionfinish():
    """
    This method is executed automatically at the end of the tests.
    """
    print("\n" + "=" * 30)
    print("Generating business report...")

    try:
        # Calling the function to generate the trend chart
        generate_trend_chart("policy_summary/policy_reports.csv")
        print("Graph is generated successfully!")
    except Exception as e:
        print(f"Error generating graph: {e}")

    print("=" * 30)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook to capture screenshot on failure and attach it to Allure report.
    Everytime when test outcome is not passed, take screenshot and attach to Allure report.
    """
    outcome = yield
    report = outcome.get_result()

    # Capture screenshot if test failed (report.failed = True means test did not pass)
    if report.when == "call" and report.failed:
        page = None

        # Try to get the page fixture from funcargs
        if hasattr(item, 'funcargs') and 'page' in item.funcargs:
            page = item.funcargs.get("page")

        # If not found in funcargs, try to get it from the fixture request
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
        else:
            print(f"\n⚠️ Page fixture not available for screenshot in test: {item.name}")
