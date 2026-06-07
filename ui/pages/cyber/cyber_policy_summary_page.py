from ui.pages.common.policy_summary_page import BasePolicySummary


class CyberPolicySummaryPage(BasePolicySummary):
    """Extract Cyber-specific fields for the policy summary report."""

    def extract_details(self, test_data, common_details=None):
        details = dict(common_details or self.extract_common_details())
        details.update({
            "Billing Method": test_data.get("BillingMethod"),
            "Business Start Date": test_data.get("BusinessStartDate"),
            "Nature Of Business": test_data.get("NatureOfBusiness"),
            "Number Of Employees": test_data.get("NumberOfEmployees"),
            "Percentage Of Online Sale": test_data.get("PercentageOfOnlineSale"),
            "Aggregate Limit": test_data.get("AggregateLimit"),
            "Per Claim Deductible": test_data.get("PerClaimDeductible"),
            "Per Claim Limit": test_data.get("PerClaimLimit"),
            "Business Interruption": test_data.get("BusinessInterruption"),
            "Cyber Extortion": test_data.get("CyberExtortion"),
            "Common Eligibility 1": test_data.get("CommonEligibility1"),
            "Common Eligibility 2": test_data.get("CommonEligibility2"),
            "Common Eligibility 3": test_data.get("CommonEligibility3"),
        })
        return details

    def report_file_name(self):
        return "policy_reports_cyber.csv"
