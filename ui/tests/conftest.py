
from utils.excel_reader import ExcelReader
from pytest_bdd import given, parsers, when
import pytest
from ui.pages.customer_page import CustomerPage

from ui.pages.new_quote_page import newQuote


@given('The user is logged in with valid credentials')
def shared_user_login(login_page):
    """
    Ovaj korak je sada dostupan i za login.feature i za personal_auto.feature.
    Koristi 'login_page' fixture koji smo već definisali.
    """
    login_page.navigate()
    login_page.click_splash_button()
    login_page.fill_credentials_from_env()
    login_page.click_login()


@given(parsers.parse('the data is loaded "{excel_path}", "{sheet_name}", "{tc_id}"'), target_fixture="test_data")
def load_excel_data(excel_path, sheet_name, tc_id):
    all_data = ExcelReader.get_excel_data(excel_path, sheet_name)
    # Filtriramo red po TC_ID koloni
    current_row = next(
        (row for row in all_data if str(row.get("TC_ID", "")).strip() == str(tc_id).strip()),
        None
    )

    if current_row is None:
        available = [r.get("TC_ID", "") for r in all_data[:10]]
        raise AssertionError(f"TC_ID '{tc_id}' not found. First TC_ID values: {available}")

    return current_row


@when("I create a new quote")
def new_quote(new_quote_page):
    new_quote_page.click_quotes_button()
    new_quote_page.click_new_quote_button()
    new_quote_page.click_agent_radio_button()
    new_quote_page.click_next_button()


@when("I create a new customer")
def create_new_customer(page, test_data):
    customer_page = CustomerPage(page)

    # Čekamo da polje First Name bude vidljivo
    page.wait_for_selector(customer_page.first_name, timeout=5000)  # 5s max

    # Popuni formu
    customer_page.fill_customer_form(test_data)
    customer_page.enter_email(test_data)

    # Screenshot za proveru
    import time
    timestamp = int(time.time())
    page.screenshot(path=f"screenshots/customer_filled_{timestamp}.png", full_page=True)

    # Klikovi
    page.click(customer_page.search_button)
    page.click(customer_page.create_new_customer_button)
    page.click(customer_page.next_button)
    page.click(customer_page.skip_button)


@when ("I provide PA information")
def step_impl(quote_registration, test_data):
    quote_registration.fill_form(test_data)
    quote_registration.set_eff_date(test_data)
    quote_registration.click_next()
