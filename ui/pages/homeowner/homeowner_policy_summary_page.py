from ui.pages.common.policy_summary_page import BasePolicySummary


class HomeownerPolicySummaryPage(BasePolicySummary):
    """Extracts Homeowner policy summary report fields."""

    def extract_details(self, test_data, common_details=None):
        details = dict(common_details or self.extract_common_details())
        details.update({
            "Program Type": test_data.get("ProgramType"),
            "Billing Method": test_data.get("BillingMethod"),
            "Policy Coverage Option": test_data.get("PolicyCoverageOption"),
            "Residence Type": test_data.get("ResidenceType"),
            "Replacement Cost": test_data.get("ReplacementCost"),
            "Contents": test_data.get("Contents"),
            "Loss Of Use": test_data.get("LossOfUse"),
            "All Perils Deductible": test_data.get("AllPerilsDeductable"),
            "Windstorm Deductible": test_data.get("WindstormDeductable"),
            "Liability": test_data.get("Liability"),
            "Medical Payments": test_data.get("MedPayments"),
            "Year Built": test_data.get("YearBuilt"),
            "Roof Type": test_data.get("RoofType"),
            "Construction Type": test_data.get("ConstructionType"),
        })
        return details

    def report_file_name(self):
        return "policy_reports_homeowner.csv"
