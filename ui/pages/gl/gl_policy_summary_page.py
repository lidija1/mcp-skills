from ui.pages.common.policy_summary_page import BasePolicySummary


class GeneralLiabilityPolicySummaryPage(BasePolicySummary):
    """Extract General Liability fields for the policy summary report."""

    def extract_details(self, test_data, common_details=None):
        details = dict(common_details or self.extract_common_details())
        details.update({
            "Billing Method": test_data.get("BillingMethod"),
            "Audit Frequency": test_data.get("AuditFrequency"),
            "Policy Type": test_data.get("PolicyType"),
            "Form Type": test_data.get("FormType"),
            "Each Occurrence Limit": test_data.get("EachOccurrenceLimit"),
            "General Aggregate Limit": test_data.get("GeneralAggregateLimit"),
            "GL Class Description": test_data.get("GLClassDescription"),
            "Exposure": test_data.get("Exposure"),
        })
        return details

    def report_file_name(self):
        return "policy_reports_general_liability.csv"
