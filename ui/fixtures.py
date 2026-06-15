"""UI page object fixtures for pytest-bdd tests."""
import pytest

from utils.excel_reader import ExcelReader
from utils.json_reader import DataLoader

# Common page fixtures
from ui.pages.common.login_page import LoginPage
from ui.pages.common.new_quote_page import NewQuotePage
from ui.pages.common.customer_page import CustomerPage
from ui.pages.common.policy_summary_page import PolicySummary
from ui.pages.common.contact_information_page import ContactInformationPage

# Auto insurance page fixtures
from ui.pages.common.quote_registration_page import QuoteRegistrationPage
from ui.pages.auto.quote_summary_page import QuoteSummaryPage
from ui.pages.auto.driver_info_page import DriverInfoPage
from ui.pages.auto.vehicle_info_page import VehicleInfoPage
from ui.pages.auto.policy_term_page import PolicyTermPage
from ui.pages.auto.create_policy_page import CreatePolicyPage
from ui.pages.auto.uw_referral_page import UWReferralPage

# Homeowner insurance page fixtures
from ui.pages.homeowner.homeowner_quote_summary_page import HomeOwnerQuoteSummaryPage
from ui.pages.homeowner.homeowner_coverage_page import HomeownerCoveragePage
from ui.pages.homeowner.homeowner_city_information_page import HomeownerCityInformationPage
from ui.pages.homeowner.homeowner_bind_information_page import HomeownerBindInformationPage
from ui.pages.homeowner.homeowner_premium_summary_page import HomeownerPremiumSummaryPage
from ui.pages.homeowner.homeowner_delivery_preferences_page import HomeownerDeliveryPreferencesPage
from ui.pages.homeowner.homeowner_billing_plan_page import HomeownerBillingPlanPage
from ui.pages.homeowner.homeowner_verify_billing_page import HomeownerVerifyBillingPage
from ui.pages.homeowner.homeowner_additional_sections_page import HomeownerAdditionalSectionsPage

# Cyber insurance page fixtures
from ui.pages.cyber.cyber_policy_information_page import CyberPolicyInformationPage

# General Liability page fixtures
from ui.pages.gl.gl_policy_information_page import GeneralLiabilityBasicPolicyInformationPage
from ui.pages.gl.gl_coverages_and_limits_page import GeneralLiabilityCoverageAndLimitsPage
from ui.pages.gl.gl_optional_coverages_page import GeneralLiabilityOptionalCoveragesPage
from ui.pages.gl.gl_liability_location_list_page import GeneralLiabilityLiabilityLocationListPage
from ui.pages.gl.gl_rating_page import GeneralLiabilityRatingBasisAndClassificationPage
from ui.pages.gl.gl_risk_address_page import GeneralLiabilityRiskAddressPage
from ui.pages.cyber.cyber_premium_summary_page import CyberPremiumSummaryPage
from ui.pages.cyber.cyber_reinsurance_page import CyberReinsurancePage
from ui.pages.cyber.cyber_inspection_page import CyberInspectionPage

# Common workflow pages (shared across LOBs)
from ui.pages.common.delivery_preferences_page import DeliveryPreferencesPage
from ui.pages.common.billing_plan_page import BillingPlanPage
from ui.pages.common.verify_billing_page import VerifyBillingPage



# ============================================================================
# Common Page Fixtures
# ============================================================================

@pytest.fixture
def policy_summary_page(page):
    """Policy summary page for data extraction."""
    return PolicySummary(page)


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
def contact_information_page(page):
    """Contact Information page for post-UW contact permission capture."""
    return ContactInformationPage(page)


# ============================================================================
# Auto Insurance Page Fixtures
# ============================================================================

@pytest.fixture
def quote_registration_page(page):
    """Quote registration page for auto insurance (legacy fixture name)."""
    return QuoteRegistrationPage(page)


@pytest.fixture
def auto_quote_registration_page(page):
    """Quote registration page for auto insurance."""
    return QuoteRegistrationPage(page)

# ============================================================================
# Auto Insurance Coverage Page Fixtures
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


@pytest.fixture
def uw_referral_page(page):
    """UW Referral page — asserts underwriting condition type and message."""
    return UWReferralPage(page)

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
    path = "testdata/static/auto/AutoData.json"
    return DataLoader.get_data(path)

# ============================================================================
# Homeowner Insurance Page Fixtures
# ============================================================================

@pytest.fixture
def homeowner_quote_summary_page(page):
    """Quote summary page for homeowner insurance."""
    return HomeOwnerQuoteSummaryPage(page)

@pytest.fixture
def homeowner_coverage_page(page):
    return HomeownerCoveragePage(page)


@pytest.fixture
def homeowner_city_information_page(page):
    return HomeownerCityInformationPage(page)


@pytest.fixture
def homeowner_bind_information_page(page):
    return HomeownerBindInformationPage(page)


@pytest.fixture
def homeowner_premium_summary_page(page):
    return HomeownerPremiumSummaryPage(page)


@pytest.fixture
def homeowner_delivery_preferences_page(page):
    return HomeownerDeliveryPreferencesPage(page)


@pytest.fixture
def homeowner_billing_plan_page(page):
    return HomeownerBillingPlanPage(page)


@pytest.fixture
def homeowner_verify_billing_page(page):
    return HomeownerVerifyBillingPage(page)


@pytest.fixture
def homeowner_additional_sections_page(page):
    return HomeownerAdditionalSectionsPage(page)


@pytest.fixture
def cyber_policy_information_page(page):
    return CyberPolicyInformationPage(page)


@pytest.fixture
def cyber_premium_summary_page(page):
    return CyberPremiumSummaryPage(page)


@pytest.fixture
def cyber_reinsurance_page(page):
    return CyberReinsurancePage(page)


@pytest.fixture
def cyber_inspection_page(page):
    return CyberInspectionPage(page)


@pytest.fixture
def general_liability_risk_address_page(page):
    return GeneralLiabilityRiskAddressPage(page)


@pytest.fixture
def general_liability_basic_policy_information_page(page):
    return GeneralLiabilityBasicPolicyInformationPage(page)


@pytest.fixture
def general_liability_coverage_and_limits_page(page):
    return GeneralLiabilityCoverageAndLimitsPage(page)


@pytest.fixture
def general_liability_optional_coverages_page(page):
    return GeneralLiabilityOptionalCoveragesPage(page)


@pytest.fixture
def general_liability_liability_location_list_page(page):
    return GeneralLiabilityLiabilityLocationListPage(page)


@pytest.fixture
def general_liability_rating_basis_and_classification_page(page):
    return GeneralLiabilityRatingBasisAndClassificationPage(page)


@pytest.fixture
def delivery_preferences_page(page):
    """Delivery preferences page — document delivery settings (common)."""
    return DeliveryPreferencesPage(page)

@pytest.fixture
def billing_plan_page(page):
    """Billing plan page — payment plan selection (common)."""
    return BillingPlanPage(page)

@pytest.fixture
def verify_billing_page(page):
    """Verify billing choices page — final bind confirmation (common)."""
    return VerifyBillingPage(page)
