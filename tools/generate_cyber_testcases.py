import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "testdata" / "static" / "cyber"


def base_case(tc_id, index, test_name, description):
    return {
        "TC_ID": tc_id,
        "TestName": test_name,
        "Description": description,
        "CustomerType": "Individual",
        "FirstName": "Cyber",
        "LastName": f"Case{index:03d}",
        "DOB": f"{(index % 9) + 1:02d}/15/{1980 + (index % 18)}",
        "PhoneNum": f"555-{400 + index % 500:03d}-{1000 + index:04d}",
        "Email": f"cyber_case_{index:03d}_{{timestamp}}@cyber.com",
        "Address": "230 Old Taunton Ave",
        "City": "Norton",
        "ZIP": "02766",
        "Producer": "Janis Irey",
        "Program": "Cyber",
        "BillingMethod": "Direct Billed",
        "BusinessStartDate": str(1995 + ((index - 1) % 25)),
        "NatureOfBusiness": "Office",
        "NumberOfEmployees": "25",
        "PercentageOfOnlineSale": "25",
        "AggregateLimit": "1,000,000",
        "PerClaimDeductible": "500",
        "PerClaimLimit": "600,000",
        "BusinessInterruption": "",
        "CyberExtortion": "",
        "CommonEligibility1": "Yes",
        "CommonEligibility2": "None",
        "CommonEligibility3": "Yes",
        "PaymentPlan": "Pay In Full",
    }


def usual_cases():
    matrix = [
        ("Apartments", "5", "0", "600,000", "100", "300,000"),
        ("Condos", "10", "10", "600,000", "250", "600,000"),
        ("Contractors", "15", "20", "1,000,000", "500", "600,000"),
        ("Office", "25", "25", "1,000,000", "750", "1,000,000"),
        ("Other", "40", "30", "2,000,000", "1,000", "1,000,000"),
        ("Retail", "50", "40", "2,000,000", "1,500", "2,000,000"),
        ("Service", "75", "50", "4,000,000", "2,000", "2,000,000"),
        ("Wholesale", "100", "60", "4,000,000", "500", "4,000,000"),
        ("Manufacturing", "150", "70", "2,000,000", "750", "1,000,000"),
        ("Apartments", "200", "80", "1,000,000", "1,000", "600,000"),
        ("Condos", "250", "90", "600,000", "1,500", "300,000"),
        ("Contractors", "300", "100", "4,000,000", "2,000", "4,000,000"),
        ("Office", "8", "5", "1,000,000", "100", "300,000"),
        ("Other", "18", "15", "2,000,000", "250", "600,000"),
        ("Retail", "35", "35", "4,000,000", "500", "1,000,000"),
        ("Service", "60", "45", "600,000", "750", "600,000"),
        ("Wholesale", "90", "55", "1,000,000", "1,000", "1,000,000"),
        ("Manufacturing", "125", "65", "2,000,000", "1,500", "2,000,000"),
        ("Office", "175", "75", "4,000,000", "2,000", "2,000,000"),
        ("Retail", "225", "95", "4,000,000", "1,000", "4,000,000"),
    ]
    cases = []
    for index, values in enumerate(matrix, start=1):
        nature, employees, online, aggregate, deductible, per_claim = values
        case = base_case(
            f"CYBER_USUAL_{index:03d}",
            index,
            f"Usual flow - {nature} business {index}",
            (
                f"Clean Cyber end-to-end flow for {nature}, {employees} employees, "
                f"{online}% online sales, aggregate {aggregate}, per-claim {per_claim}."
            ),
        )
        case.update({
            "NatureOfBusiness": nature,
            "NumberOfEmployees": employees,
            "PercentageOfOnlineSale": online,
            "AggregateLimit": aggregate,
            "PerClaimDeductible": deductible,
            "PerClaimLimit": per_claim,
        })
        cases.append(case)
    return cases


def optional_cases():
    specs = [
        ("PolicyOptionalCoverage", "Business interruption 10k", {"BusinessInterruption": "10000"}),
        ("PolicyOptionalCoverage", "Business interruption 25k", {"BusinessInterruption": "25000"}),
        ("PolicyOptionalCoverage", "Business interruption 50k", {"BusinessInterruption": "50000"}),
        ("PolicyOptionalCoverage", "Cyber extortion 10k", {"CyberExtortion": "10000"}),
        ("PolicyOptionalCoverage", "Cyber extortion 25k", {"CyberExtortion": "25000"}),
        ("PolicyOptionalCoverage", "Cyber extortion 50k", {"CyberExtortion": "50000"}),
        ("PolicyOptionalCoverage", "Both optional coverages 10k", {
            "BusinessInterruption": "10000", "CyberExtortion": "10000",
        }),
        ("PolicyOptionalCoverage", "Both optional coverages 25k", {
            "BusinessInterruption": "25000", "CyberExtortion": "25000",
        }),
        ("PolicyOptionalCoverage", "Mixed optional coverage limits", {
            "BusinessInterruption": "50000", "CyberExtortion": "10000",
        }),
        ("Reinsurance", "Facultative reinsurance - office profile", {
            "ReinsuranceType": "Facultative",
        }),
        ("Reinsurance", "Facultative reinsurance - retail profile", {
            "ReinsuranceType": "Facultative",
            "NatureOfBusiness": "Retail",
        }),
        ("Reinsurance", "Treaty reinsurance - office profile", {
            "ReinsuranceType": "Treaty",
        }),
        ("Reinsurance", "Treaty reinsurance - wholesale profile", {
            "ReinsuranceType": "Treaty",
            "NatureOfBusiness": "Wholesale",
        }),
        ("InspectionRequest", "Comprehensive inspection request", {
            "InspectionType": "Comprehensive",
            "InspectionCompany": "Inspection Company",
            "InspectionCompleted": "No",
            "InspectionRequestDetails": "Comprehensive Cyber inspection requested.",
        }),
        ("InspectionRequest", "Property inspection request", {
            "InspectionType": "Property",
            "InspectionCompany": "Inspection Company",
            "InspectionCompleted": "No",
            "InspectionRequestDetails": "Property-focused Cyber inspection requested.",
        }),
        ("InspectionAssignment", "Assignment comment - initial review", {
            "InspectionAssignmentComments": "Initial inspection assignment review.",
        }),
        ("InspectionAssignment", "Assignment comment - security controls", {
            "InspectionAssignmentComments": "Review security controls and documentation.",
        }),
        ("InspectionAssignment", "Assignment comment - follow-up", {
            "InspectionAssignmentComments": "Follow-up inspection assignment notes.",
        }),
    ]
    cases = []
    for index, (flow, name, overrides) in enumerate(specs, start=1):
        case = base_case(
            f"CYBER_OPTIONAL_{index:03d}",
            100 + index,
            name,
            f"Exercises optional Cyber flow: {flow}.",
        )
        case["OptionalFlow"] = flow
        case.update(overrides)
        cases.append(case)
    return cases


def write_json(path, cases):
    path.write_text(
        json.dumps({"testCases": cases}, indent=2) + "\n",
        encoding="utf-8",
    )


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    write_json(DATA_DIR / "CyberData.json", usual_cases())
    write_json(DATA_DIR / "CyberOptionalData.json", optional_cases())
    print("Generated 20 usual Cyber cases and 18 optional Cyber cases.")


if __name__ == "__main__":
    main()
