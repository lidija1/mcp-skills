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
    if isinstance(browser, list):
        if len(browser) > 0:
            return browser[0]
        return "chromium"


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
        headless=True,
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
    """
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        page = item.funcargs.get("page")
        if page:
            allure.attach(
                page.screenshot(full_page=True),
                name=f"failure_{item.name}",
                attachment_type=allure.attachment_type.PNG
            )

