"""Auto insurance quote and policy workflow step definitions."""
from datetime import datetime

from pytest_bdd import when, given, then

from utils.file_writer import save_summary_to_csv


@when("i create a new quote")
def create_new_quote(new_quote_page, log):
    """Initiate a new quote creation process."""
    log.info("Starting new quote creation...")
    new_quote_page.new_quote_steps()
    log.info("Successfully created new quote.")


@when("i create a new customer")
def create_new_customer(customer_page, test_data, log):
    """Create a new customer with provided data."""
    log.info("Starting customer creation...")
    customer_page.customer_steps(test_data)
    log.info("Successfully created new customer.")


@when("I provide quote registration details")
def provide_quote_registration(quote_registration_page, test_data, log):
    """Fill quote registration details."""
    log.info("Filling quote registration details...")
    quote_registration_page.quote_registration_steps(test_data)
    log.info("Successfully filled quote registration details.")


@when("I provide quote summary PA info")
def provide_quote_summary(quote_summary_page, test_data, log):
    """Fill quote summary information."""
    log.info("Filling quote summary information...")
    quote_summary_page.summary_steps(test_data)
    log.info("Successfully filled quote summary information.")


@when("I provide Driver Details")
def provide_driver_details(driver_info_page, test_data, log):
    """Fill driver information."""
    log.info("Filling driver details...")
    driver_info_page.fill_driver_info(test_data)
    log.info("Successfully filled driver details.")


@when("I provide Vehicle Details")
def provide_vehicle_details(vehicle_info_page, test_data, log):
    """Fill vehicle information."""
    log.info("Filling vehicle details...")
    vehicle_info_page.fill_vehicle_info(test_data)
    log.info("Successfully filled vehicle details.")


@given("I provide policy term details")
def provide_policy_term_details(policy_term_page, test_data, log):
    """Fill policy term and coverage details."""
    log.info("Filling policy term details...")
    policy_term_page.policy_term_steps(test_data)
    log.info("Successfully filled policy term details.")


@when("I create a policy from the quote")
def create_policy_from_quote(create_policy_page, log):
    """Create and bind a policy from the quote."""
    log.info("Creating policy from quote...")
    create_policy_page.policy_creation_steps()
    log.info("Successfully created and bound policy.")


@then("I read and extract policy summary page details")
def read_extract_summary(policy_summary_page, test_data, log):
    """Extract details from the policy summary page."""
    log.info("Extracting policy summary details...")
    
    details = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Policy Number": policy_summary_page.get_policy_number(),
        "Program": policy_summary_page.get_program(),
        "Customer Name": policy_summary_page.get_customer_name(),
        "Status": policy_summary_page.get_status(),
        "Payment Method": policy_summary_page.get_payment_method(),
        "Primary Jurisdiction": policy_summary_page.get_jurisdiction(),
        "Total Policy Premium": policy_summary_page.get_premium(),
        "Payment Plan": policy_summary_page.get_payment_plan(),
        "Employment Category": test_data.get("EmploymentCategory"),
        "Vehicle Use": test_data.get("VehicleUse"),
        "Ownership": test_data.get("Ownership"),
        "Policy Coverage Option": test_data.get("PolicyCoverage")
    }

    path = save_summary_to_csv(details)
    log.info("Data is saved to CSV file at: " + path)
    
    log.info("-" * 40)
    log.info("POLICY SUMMARY DETAILS:")
    for key, value in details.items():
        log.info(f"{key}: {value}")
    log.info("-" * 40)
    
    # Also print to stdout so it's visible in console output during -s run
    print("\n" + "=" * 50)
    print("POLICY SUMMARY REPORT")
    print("=" * 50)
    for key, value in details.items():
        print(f"{key:20}: {value}")
    print("=" * 50 + "\n")
