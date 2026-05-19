import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "reports" / "general_liability_dropdown_inventory.json"
DATA = ROOT / "testdata" / "static" / "general_liability" / "GeneralLiabilityDropdownOptionsData.json"
OPTION_SENTINELS = {"- Select -", "-Select-"}
MATRIX_FIELDS = {
    "BillingMethod",
    "AuditFrequency",
    "CoverageType",
    "PolicyType",
    "FormType",
    "DefenseTreatment",
    "LimitVentilationRequired",
    "EachOccurrenceLimit",
    "GeneralAggregateLimit",
    "PersonalAndAdvertisingInjuryLimit",
    "ProductsAndCompletedOperationsAggregateLimit",
    "FireDamageLegalLiabilityLimitAnyOneFire",
    "MedicalExpenseLimitAnyOnePerson",
    "GeneralLiabilityDeductible",
    "DeductibleType",
    "DeductibleApplies",
    "GLClassCode",
    "GLClassDescription",
    "PayerCurrency",
    "PaymentPlan",
}

EXPECTED_FALLBACKS = {
    "CoverageType": ["Commercial General Liability"],
    "GLClassCode": ["501"],
}


def test_general_liability_dropdown_options_data_covers_live_probe():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    data = json.loads(DATA.read_text(encoding="utf-8"))

    expected = []
    for section in ("basic_policy_information", "coverage_and_limits", "rating_basis_and_classification", "billing_plan"):
        for key, raw_options in source[section].items():
            if key not in MATRIX_FIELDS:
                continue
            options = list(raw_options or []) or EXPECTED_FALLBACKS.get(key, [])
            for option in options:
                if option not in OPTION_SENTINELS:
                    expected.append((key, option))

    actual = [
        (case["DropdownDataKey"], case["DropdownOption"])
        for case in data["testCases"]
    ]

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    missing_descriptions = [
        case["TC_ID"]
        for case in data["testCases"]
        if not case.get("Description")
    ]

    assert not missing
    assert not extra
    assert not missing_descriptions
    assert data["metadata"]["caseCount"] == len(data["testCases"])
