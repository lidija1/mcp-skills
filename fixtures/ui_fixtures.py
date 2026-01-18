import pytest
from ui.pages.login_page import LoginPage
from ui.pages.new_quote_page import newQuote
from ui.pages.quote_registration import QuoteRegistration
from ui.pages.quote_summary import QuoteSummary
from utils.excel_reader import ExcelReader
from ui.pages.customer_page import CustomerPage

@pytest.fixture
def login_page(page):
    """
    Initializes the LoginPage with the current Playwright page instance.
    This fixture can be used in any test or BDD step.
    """
    return LoginPage(page)

@pytest.fixture
def new_quote_page(page):
    return newQuote(page)

@pytest.fixture
def excel_data():
    path = "C:\Projekti\SandboxPlaywright\testdata\static\AutoData.xlsx"
    return ExcelReader.get_excel_data(path)

@pytest.fixture
def customer_page(page):
    return CustomerPage(page)

@pytest.fixture
def quote_registration(page):
    return QuoteRegistration(page)

@pytest.fixture
def quote_summary(page):
    return QuoteSummary(page)


# Ovde možeš dodati i druge stranice kako ih budeš pravio
# @pytest.fixture
# def policy_page(page):
#     from ui.pages.policy_page import PolicyPage
#     return PolicyPage(page)