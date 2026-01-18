from pytest_bdd import when

from ui.pages.customer_page import CustomerPage


@when("I create a new quote")
def new_quote(new_quote_page):
    new_quote_page.click_quotes_button()
    new_quote_page.click_new_quote_button()
    new_quote_page.click_agent_radio_button()
    new_quote_page.click_next_button()


@when("I create a new customer")
def create_new_customer(customer_page, test_data):


    # Čekamo da polje First Name bude vidljivo
    # page.wait_for_selector(customer_page.first_name, timeout=5000)  # 5s max

    # Popuni formu
    customer_page.fill_customer_form(test_data)
    customer_page.enter_email(test_data)

    # Screenshot za proveru
    # import time
    # timestamp = int(time.time())
    # page.screenshot(path=f"screenshots/customer_filled_{timestamp}.png", full_page=True)

    # Klikovi
    customer_page.click(customer_page.search_button)
    customer_page.click(customer_page.create_new_customer_button)
    customer_page.click(customer_page.next_button)
    customer_page.click(customer_page.skip_button)


@when ("I provide PA information")
def step_impl(quote_registration, test_data):
    quote_registration.fill_form(test_data)
    quote_registration.set_eff_date(test_data)
    quote_registration.click_next()