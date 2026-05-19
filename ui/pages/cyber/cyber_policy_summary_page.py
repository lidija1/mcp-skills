from ui.pages.common.policy_summary_page import BasePolicySummary


class CyberPolicySummaryPage(BasePolicySummary):
    """Extracts Cyber policy summary report fields."""

    def extract_details(self, test_data, common_details=None):
        details = dict(common_details or self.extract_common_details())
        details.update({
            "Billing Method": test_data.get("BillingMethod"),
            "Business Start Date": test_data.get("BusinessStartDate"),
            "Total Employees": test_data.get("TotalEmployees"),
            "Nature Of Business": test_data.get("NatureOfBusiness"),
            "Percent Online Sales": test_data.get("PctOnlineSales"),
            "Aggregate Limit": test_data.get("AggregateLimit"),
            "Per Claim Limit": test_data.get("PerClaimLimit"),
            "Per Claim Deductible": test_data.get("PerClaimDeductible"),
            "Cyber Training": test_data.get("CyberTraining"),
            "Situations Last 3 Years": test_data.get("SituationsLast3Years"),
            "Cyber Regulations": test_data.get("CyberRegulations"),
        })
        return details

    def report_file_name(self):
        return "policy_reports_cyber.csv"
