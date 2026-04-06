from pytest_bdd import when


@when("I explore the WC quote page")
def explore_wc_quote_page(page, log):
    """Pause on the first WC-specific page for UI inspection."""
    log.info("Reached WC quote page — pausing for inspection.")
    page.pause()
