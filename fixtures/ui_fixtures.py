"""UI page object fixtures for pytest-bdd tests."""
import pytest
from utils.excel_reader import ExcelReader
from utils.json_reader import DataLoader

# Common page fixtures
from ui.pages.common.login_page import LoginPage
from ui.pages.common.new_quote_page import NewQuotePage
from ui.pages.common.customer_page import CustomerPage
from ui.pages.common.quote_registration_page import QuoteRegistrationPage

# Auto insurance page fixtures
from ui.pages.auto.quote_summary_page import QuoteSummaryPage
from ui.pages.auto.driver_info_page import DriverInfoPage
from ui.pages.auto.vehicle_info_page import VehicleInfoPage
from ui.pages.auto.policy_term_page import PolicyTermPage
from ui.pages.auto.create_policy_page import CreatePolicyPage


# ============================================================================
# Common Page Fixtures
# ============================================================================

@pytest.fixture
def login_page(page):
    """Login page for authentication."""
    return LoginPage(page)


@pytest.fixture
def new_quote_page(page):
    """New quote page for initiating quotes."""
    return NewQuotePage(page)


@pytest.fixture
def customer_page(page):
    """Customer page for creating and managing customers."""
    return CustomerPage(page)


@pytest.fixture
def quote_registration_page(page):
    """Quote registration page for quote details."""
    return QuoteRegistrationPage(page)


# ============================================================================
# Auto Insurance Page Fixtures
# ============================================================================

@pytest.fixture
def quote_summary_page(page):
    """Quote summary page for auto insurance."""
    return QuoteSummaryPage(page)


@pytest.fixture
def driver_info_page(page):
    """Driver information page for auto insurance."""
    return DriverInfoPage(page)


@pytest.fixture
def vehicle_info_page(page):
    """Vehicle information page for auto insurance."""
    return VehicleInfoPage(page)


@pytest.fixture
def policy_term_page(page):
    """Policy term page for coverage details."""
    return PolicyTermPage(page)


@pytest.fixture
def create_policy_page(page):
    """Create policy page for binding quotes."""
    return CreatePolicyPage(page)


# ============================================================================
# Data Fixtures
# ============================================================================

@pytest.fixture
def excel_data():
    """Load test data from Excel file."""
    path = "C:\\Projekti\\SandboxPlaywright\\testdata\\static\\AutoData.xlsx"
    return ExcelReader.get_excel_data(path)


@pytest.fixture
def json_data():
    """Load test data from JSON file."""
    path = "testdata/static/AutoData.json"
    return DataLoader.get_data(path)