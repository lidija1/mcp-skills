from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mcp_tools.policy_flow_generator.persona_generator import atomic_write_json  # noqa: E402
SOURCE = ROOT / "reports" / "general_liability_dropdown_inventory.json"
BASE_DATA = ROOT / "testdata" / "static" / "general_liability" / "GeneralLiabilityData.json"
OUTPUT_DATA = ROOT / "testdata" / "static" / "general_liability" / "GeneralLiabilityDropdownOptionsData.json"
OUTPUT_FEATURE = ROOT / "ui" / "features" / "general_liability" / "general_liability_dropdown_options.feature"

OPTION_SENTINELS = {"- Select -", "-Select-"}

FIELD_METADATA = {
    "BillingMethod": ("Basic Policy Information", "Billing Method"),
    "AuditFrequency": ("Basic Policy Information", "Audit Frequency"),
    "CoverageType": ("Coverage and Limits", "Coverage Type"),
    "PolicyType": ("Coverage and Limits", "Policy Type"),
    "FormType": ("Coverage and Limits", "Form Type"),
    "DefenseTreatment": ("Coverage and Limits", "Defense Treatment"),
    "LimitVentilationRequired": ("Coverage and Limits", "Limit Ventilation Required"),
    "EachOccurrenceLimit": ("Coverage and Limits", "Each Occurrence Limit"),
    "GeneralAggregateLimit": ("Coverage and Limits", "General Aggregate Limit"),
    "PersonalAndAdvertisingInjuryLimit": ("Coverage and Limits", "Personal & Advertising Injury"),
    "ProductsAndCompletedOperationsAggregateLimit": ("Coverage and Limits", "Products & Completed Operations"),
    "FireDamageLegalLiabilityLimitAnyOneFire": ("Coverage and Limits", "Fire Damage Legal Liability"),
    "MedicalExpenseLimitAnyOnePerson": ("Coverage and Limits", "Medical Expense Limit - Any One Person"),
    "GeneralLiabilityDeductible": ("Coverage and Limits", "General Liability Deductible"),
    "DeductibleType": ("Coverage and Limits", "Deductible Type"),
    "DeductibleApplies": ("Coverage and Limits", "Deductible Applies"),
    "GLClassCode": ("Rating Basis and Classification", "GL Class Code"),
    "GLClassDescription": ("Rating Basis and Classification", "GL Class Description"),
    "PayerCurrency": ("Billing Plan", "Payer Currency"),
    "PaymentPlan": ("Billing Plan", "Payment Plan"),
}

# These controls were not captured by the generic live collector, so we backfill
# the confirmed values from the base GL case to keep the matrix complete.
FALLBACK_VALUES = {
    "CoverageType": ["Commercial General Liability"],
    "GLClassCode": ["501"],
}


def slug(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return text[:32] or "option"


def load_base_case() -> dict:
    payload = json.loads(BASE_DATA.read_text(encoding="utf-8"))
    for case in payload["testCases"]:
        if case.get("TC_ID") == "TC_ID_0001":
            return deepcopy(case)
    raise ValueError("TC_ID_0001 not found in GeneralLiabilityData.json")


def load_inventory() -> dict:
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def selectable_options(inventory: dict):
    for section in ("basic_policy_information", "coverage_and_limits", "rating_basis_and_classification", "billing_plan"):
        for key, raw_options in inventory.get(section, {}).items():
            if key not in FIELD_METADATA:
                continue
            options = list(raw_options or [])
            if not options and key in FALLBACK_VALUES:
                options = FALLBACK_VALUES[key]
            for option in options:
                if option in OPTION_SENTINELS:
                    continue
                yield key, option


def build_cases() -> dict:
    inventory = load_inventory()
    base = load_base_case()
    cases = []

    for index, (key, option) in enumerate(selectable_options(inventory), start=1):
        screen, field_label = FIELD_METADATA[key]
        case = deepcopy(base)
        case_id = f"TC_GL_DD_{index:04d}"
        case["TC_ID"] = case_id
        case[key] = option
        case["FirstName"] = f"GLDrop{index:03d}"
        case["LastName"] = f"{slug(key)}_{index:03d}"
        case["Email"] = f"gl_dropdown_{index:04d}_{{timestamp}}@example.com"
        case["PhoneNum"] = f"921-549-{1000 + index:04d}"[-12:]
        case["Address"] = f"{200 + index} Old Taunton Ave"
        case["Description"] = (
            f"General Liability dropdown option coverage: {screen} / {field_label} = {option}."
        )
        case["DropdownScreen"] = screen
        case["DropdownField"] = field_label
        case["DropdownDataKey"] = key
        case["DropdownOption"] = option
        cases.append(case)

    return {
        "metadata": {
            "description": (
                "Generated General Liability dropdown-option matrix. Each case changes "
                "one confirmed dropdown value and keeps the dependent GL flow intact."
            ),
            "source": str(SOURCE.relative_to(ROOT)),
            "baseCase": "testdata/static/general_liability/GeneralLiabilityData.json::TC_ID_0001",
            "caseCount": len(cases),
        },
        "testCases": cases,
    }


def render_feature(case_ids: list[str]) -> str:
    rows = "\n".join(f"      | {case_id} |" for case_id in case_ids)
    return f"""Feature: General Liability dropdown options

  Background:
    Given The user is logged in with valid credentials

  @general_liability @dropdown_matrix
  Scenario Outline: Exercise the General Liability dropdown option matrix
    Given the data is loaded "testdata/static/general_liability/GeneralLiabilityDropdownOptionsData.json", "<TC_ID>"
    When i create a new quote
    When i create a new customer
    When I provide quote registration details
    When I provide general liability risk address details
    When I provide general liability basic policy information
    When I provide general liability coverage and limits
    When I provide general liability liability location list details
    When I provide general liability rating basis and classification details
    When I rate the general liability quote
    When I request issue for the general liability quote
    When I proceed to the general liability billing plan
    When I complete the general liability billing plan
    When I bind the general liability policy
    Then the general liability flow is complete
    Then I read and extract policy summary page details for general liability

    Examples:
      | TC_ID |
{rows}
"""


def main() -> int:
    payload = build_cases()
    OUTPUT_DATA.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FEATURE.parent.mkdir(parents=True, exist_ok=True)

    atomic_write_json(OUTPUT_DATA, payload)
    OUTPUT_FEATURE.write_text(render_feature([case["TC_ID"] for case in payload["testCases"]]), encoding="utf-8")

    print(f"Wrote {payload['metadata']['caseCount']} cases to {OUTPUT_DATA}")
    print(f"Wrote feature outline to {OUTPUT_FEATURE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
