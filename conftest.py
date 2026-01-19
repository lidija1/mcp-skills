import pytest
from dotenv import load_dotenv
from playwright.sync_api import Playwright

from utils.logger import setup_logger

load_dotenv()

# Lista putanja do tvojih fixture fajlova (bez .py ekstenzije)
pytest_plugins = [
    "fixtures.ui_fixtures",
    "ui.steps.common_steps",
    "ui.steps.auto_steps",
    # "fixtures.api_fixtures",  <-- Kasnije kad dodaš API
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

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": None,
    }

