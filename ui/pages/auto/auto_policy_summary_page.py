from ui.pages.common.policy_summary_page import BasePolicySummary


class AutoPolicySummaryPage(BasePolicySummary):
    """Extracts Personal Auto policy summary report fields."""

    def extract_details(self, test_data, common_details=None):
        details = dict(common_details or self.extract_common_details())
        details.update({
            "Employment Category": test_data.get("EmploymentCategory"),
            "Vehicle Use": test_data.get("VehicleUse"),
            "Ownership": test_data.get("Ownership"),
            "Policy Coverage Option": test_data.get("PolicyCoverage"),
            "Vehicle Type": test_data.get("VehicleType"),
            "Vehicle Year": test_data.get("Year"),
            "Vehicle Make": test_data.get("Make"),
            "Vehicle Model": test_data.get("Model"),
        })
        return details

    def report_file_name(self):
        return "policy_reports_personal_auto.csv"
