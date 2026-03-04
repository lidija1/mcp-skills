from pytest_bdd import when

@when("I provide quote summary HO info")
def homeowner_quote(homeowner_quote_summary_page, test_data, log):
    """Fill quote summary information for homeowner insurance."""
    log.info("Filling homeowner quote summary information...")
    homeowner_quote_summary_page.summary_steps(test_data)
    log.info("Successfully filled homeowner quote summary information.")

@when("I provide location coverage info")
def ho_coverage_info(homeowner_coverage_page, test_data, log):
    log.info("Filling homeowner location coverage information...")
    homeowner_coverage_page.coverage_steps(test_data)
    log.info("Successfully filled homeowner location coverage information.")
    
