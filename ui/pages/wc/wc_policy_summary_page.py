from ui.pages.common.policy_summary_page import BasePolicySummary


class WCPolicySummaryPage(BasePolicySummary):
    """Extracts Workers Compensation policy summary report fields."""

    def extract_details(self, test_data, common_details=None):
        details = dict(common_details or self.extract_common_details())
        details.update({
            "Producer": test_data.get("Producer"),
            "Effective Date Offset": test_data.get("EffDateOffset"),
        })
        return details

    def report_file_name(self):
        return "policy_reports_workers_compensation.csv"
