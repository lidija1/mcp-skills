import pytest
from dotenv import load_dotenv
from playwright.sync_api import Playwright, sync_playwright

from utils.logger import setup_logger

load_dotenv()

# Plugin list for fixtures and step definitions
pytest_plugins = [
    "fixtures.ui_fixtures",      # Page object fixtures
    "ui.steps.auth_steps",       # Login and authentication
    "ui.steps.data_steps",       # Data loading from Excel
    "ui.steps.auto_workflow_steps",  # Auto insurance workflow
    # "fixtures.api_fixtures",   # Removed as user wants UI only
]

@pytest.fixture(scope="session")
def log():
    return setup_logger("PlaywrightTest")

@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    return {
        **browser_type_launch_args,
        "args": [
            *(browser_type_launch_args.get("args") or []),
            "--window-size=1920,1080",
        ],
    }

@pytest.fixture(scope="function")
def page():
    # Starting Playwright Engine
    playwright = sync_playwright().start()

    # Launching browser
    # slow_mo usporava svaku akciju za zadati broj milisekundi
    # headless=False omogućava da vidiš prozor brauzera
    # headless is set to False to allow seeing the browser window
    browser = playwright.chromium.launch(headless=False, slow_mo=100)

    # Creating new context and page (better for test isolation)
    context = browser.new_context()
    page = context.new_page()

    yield page  # This is where the testing happens and the page is used

    # Teardown: Cleaning up after test
    page.close()
    context.close()
    browser.close()
    playwright.stop()

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": None,
    }


@pytest.fixture
def data(test_data):
    """
    Alias za test_data fixture.
    Omogućava koracima da koriste 'data' umesto 'test_data'.
    """
    return test_data
