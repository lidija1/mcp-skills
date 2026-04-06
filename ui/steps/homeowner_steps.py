import allure
from pytest_bdd import when


@when("I provide quote summary HO info")
def homeowner_quote(homeowner_quote_summary_page, test_data, log):
    """Fill quote summary information for homeowner insurance."""
    log.info("Filling homeowner quote summary information...")
    homeowner_quote_summary_page.summary_steps(test_data)
    log.info("Successfully filled homeowner quote summary information.")


@when("I provide quote summary HO info for UW testing")
def homeowner_quote_uw(page, homeowner_quote_summary_page, test_data, log):
    """
    Fill Quote Summary (Page 1) eligibility data and handle UW referral that may
    fire on that page's save (e.g. ResidenceVacant=Yes, DayCare=Yes, Animals=Yes).

    If the Page 1 save redirects to the UW referral page, the exception is caught
    here and the step returns early so the Then assertion can validate the condition.
    """
    uw_indicator = page.locator("text=underwriting referral")
    try:
        log.info("Filling homeowner quote summary for UW testing...")
        homeowner_quote_summary_page.summary_steps(test_data)
        log.info("Quote summary completed — proceeding to coverage.")
    except Exception as exc:
        if uw_indicator.is_visible(timeout=5_000):
            log.info("UW referral detected on quote summary save — proceeding to assertion.")
            return
        raise exc


@when("I provide location coverage info")
def ho_coverage_info(homeowner_coverage_page, test_data, log):
    log.info("Filling homeowner location coverage information...")
    homeowner_coverage_page.coverage_steps(test_data)
    log.info("Successfully filled homeowner location coverage information.")


@when("I provide location coverage info for UW testing")
def ho_coverage_info_uw(page, homeowner_coverage_page, test_data, log):
    """
    Fill Location Coverage (Page 2) and handle three UW trigger points:

    1. UW already visible — fired on Quote Summary save (e.g. ResidenceVacant=Yes).
       Skip the coverage form entirely and let the Then step assert.

    2. Hard-stop on coverage save — Renovation=Yes fires immediately when the
       Location Coverage form is saved. coverage_steps() raises because Bind
       Information link is intercepted by the referral page. Caught in except block.

    3. Soft-referral after Rate Quote — the full flow completes normally and UW
       conditions appear after Rate Quote is clicked (e.g. old Frame, bad roof,
       Refused/Declined in Bind Info).
    """
    uw_indicator = page.locator("text=underwriting referral")

    # Case 1 — UW already shown from a Page 1 trigger; nothing to do here.
    if uw_indicator.is_visible(timeout=2_000):
        log.info("UW referral already visible before coverage step — skipping.")
        return

    try:
        log.info("Filling location coverage for UW testing...")
        homeowner_coverage_page.coverage_steps(test_data)
        log.info("Coverage steps completed — Rate Quote clicked, UW referral expected.")
    except Exception as exc:
        # Case 2 — UW fired on coverage save (hard-stop intercepted the page).
        if uw_indicator.is_visible(timeout=5_000):
            log.info("UW referral detected on coverage save — proceeding to assertion.")
            return
        raise exc


    
