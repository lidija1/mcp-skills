from datetime import datetime

from utils.file_writer import save_summary_to_csv
from ui.pages.common.base_page import BasePage


class BasePolicySummary(BasePage):
    """Base reader for fields shared by policy summary pages."""

    def __init__(self, page):
        super().__init__(page)

    def get_policy_number(self) -> str:
        return self.read_summary("Policy Number")

    def get_program(self) -> str:
        return self.read_summary("Program")

    def get_customer_name(self) -> str:
        return self.read_summary("Customer Name")

    def get_status(self) -> str:
        return self.read_summary("Status")

    def get_payment_method(self) -> str:
        return self.read_summary("Payment Method")

    def get_jurisdiction(self) -> str:
        return self.read_summary("Primary Jurisdiction")

    def get_premium(self) -> str:
        return self.read_summary("Total Policy Premium")

    def get_payment_plan(self) -> str:
        return self.read_summary("Payment Plan")

    def extract_common_details(self):
        """Read fields that are shared across LOB policy summary pages."""
        return {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Policy Number": self.get_policy_number(),
            "Program": self.get_program(),
            "Customer Name": self.get_customer_name(),
            "Status": self.get_status(),
            "Payment Method": self.get_payment_method(),
            "Primary Jurisdiction": self.get_jurisdiction(),
            "Total Policy Premium": self.get_premium(),
            "Payment Plan": self.get_payment_plan(),
        }


class PolicySummary(BasePolicySummary):
    """Routes policy summary extraction to the matching LOB-specific page object."""

    def extract_details(self, test_data):
        common_details = self.extract_common_details()
        return self._lob_summary(common_details.get("Program")).extract_details(test_data, common_details)

    def save_lob_report(self, details):
        """Save policy summary details to a report file separated by LOB/program."""
        file_name = self._lob_summary(details.get("Program")).report_file_name()
        return save_summary_to_csv(details, file_name=file_name)

    def _lob_summary(self, program):
        program_name = str(program or "").strip().lower()

        if program_name == "homeowner":
            from ui.pages.homeowner.homeowner_policy_summary_page import HomeownerPolicySummaryPage
            return HomeownerPolicySummaryPage(self.page)

        if program_name == "cyber":
            from ui.pages.cyber.cyber_policy_summary_page import CyberPolicySummaryPage
            return CyberPolicySummaryPage(self.page)

        if program_name == "general liability":
            from ui.pages.gl.gl_policy_summary_page import GeneralLiabilityPolicySummaryPage
            return GeneralLiabilityPolicySummaryPage(self.page)

        from ui.pages.auto.auto_policy_summary_page import AutoPolicySummaryPage
        return AutoPolicySummaryPage(self.page)
