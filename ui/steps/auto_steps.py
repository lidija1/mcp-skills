from pytest_bdd import when


@when("I create a new quote")
def new_quote(new_quote_page, log):
    log.info("Starting the 'New Quote' creation process...")
    new_quote_page.click_quotes_button()
    new_quote_page.click_new_quote_button()
    new_quote_page.click_agent_radio_button()
    new_quote_page.click_next_button()
    log.info("Successfully completed the new quote creation step.")


@when("I create a new customer")
def create_new_customer(customer_page, test_data, log):
    log.info("Starting the 'Create new customer' process...")


    # Čekamo da polje First Name bude vidljivo
    customer_page.wait_visible(customer_page.first_name, timeout=5000)  # 5s max

    # Popuni formu
    customer_page.fill_customer_form(test_data)
    customer_page.enter_email(test_data)

    # Screenshot za proveru
    # import time
    # timestamp = int(time.time())
    # page.screenshot(path=f"screenshots/customer_filled_{timestamp}.png", full_page=True)

    # Klikovi
    customer_page.click_search()
    customer_page.click_create_new_customer()
    customer_page.click_next()
    customer_page.click_skip()
    log.info("Successfully completed the new customer creation step.")


@when ("I provide quote registration details")
def step_quote_reg(quote_registration, test_data, log):
    log.info("Starting the 'Quote registration details' process...")
    quote_registration.fill_form(test_data)
    quote_registration.set_eff_date(test_data)
    quote_registration.click_next()
    log.info("Successfully completed the quote registration details step.")


@when("I provide quote summary PA info")
def step_pa_info(quote_summary, test_data, log):
    log.info("Starting the 'Quote summary PA info' process...")
    quote_summary.set_billing(test_data)
    quote_summary.misleading_radio(test_data)
    quote_summary.damage_radio(test_data)
    quote_summary.click_save()
    quote_summary.click_next_red()
    log.info("Successfully completed the quote summary PA info step.")