import json
import re
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mcp_tools.policy_flow_generator.persona_generator import atomic_write_json  # noqa: E402
SOURCE = ROOT / "reports" / "homeowner_dropdown_options.json"
HOME_DATA = ROOT / "testdata" / "static" / "homeowner" / "HomeData.json"
OUTPUT = ROOT / "testdata" / "static" / "homeowner" / "HomeownerDropdownOptionsData.json"

OPTION_SENTINELS = {"- Select -", "-Select-"}

FIELD_METADATA = {
    "ProgramType": ("Quote Summary", "Program Type"),
    "BillingMethod": ("Quote Summary", "Billing Method"),
    "Term": ("Quote Summary", "Term"),
    "Prefix": ("Quote Summary", "Prefix"),
    "Suffix": ("Quote Summary", "Suffix"),
    "ResidenceType": ("Location Coverage", "Residence Type"),
    "PolicyCoverageOption": ("Location Coverage", "Policy Coverage Option"),
    "AllPerilsDeductable": ("Location Coverage", "All Perils Deductible"),
    "WindstormDeductable": ("Location Coverage", "Windstorm or Hail"),
    "Liability": ("Location Coverage", "Liability"),
    "MedPayments": ("Location Coverage", "Medical Payments"),
    "ConstructionType": ("Location Coverage", "Construction Type"),
    "ProtectionClass": ("Location Coverage", "Protection Class"),
    "BCEG": ("Location Coverage", "BCEG"),
    "RoofType": ("Location Coverage", "Roof Type"),
    "RoofShape": ("Location Coverage", "Roof Shape"),
    "SecondaryWaterResistance": ("Location Coverage", "Secondary Water Resistance"),
    "OpeningProtection": ("Location Coverage", "Opening Protection"),
    "RoofWallConnection": ("Location Coverage", "Roof Wall Connection"),
    "RoofDeck": ("Location Coverage", "Roof Deck"),
    "RoofDeckAttachment": ("Location Coverage", "Roof Deck Attachment"),
    "DistanceToShore": ("Location Coverage", "Distance to Shore"),
    "PerimeterSecurityProtection": ("Location Coverage", "Perimeter Security Protection"),
}


def load_base_case():
    payload = json.loads(HOME_DATA.read_text(encoding="utf-8"))
    for case in payload["testCases"]:
        if case.get("TC_ID") == "HO_001":
            base = deepcopy(case)
            break
    else:
        raise ValueError("HO_001 not found in HomeData.json")

    base.pop("Pool", None)
    base["Loses"] = "No"
    base["Prefix"] = "Mr."
    base["Suffix"] = "Jr."
    base["Term"] = "12 Months"
    base["ProtectionClass"] = "1"
    base["BCEG"] = "01"
    base["RoofShape"] = "Hip Roof"
    base["SecondaryWaterResistance"] = "Yes"
    base["OpeningProtection"] = "Class C - Ordinary Non-Impact or None"
    base["RoofWallConnection"] = "Clips"
    base["RoofDeck"] = "Other Roof Deck or Lumber Roof Deck"
    base["RoofDeckAttachment"] = '8d @ 6"/12"'
    base["DistanceToShore"] = "> 5 miles"
    base["PerimeterSecurityProtection"] = "None"
    return base


def slug(value):
    text = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return text[:32] or "option"


def selectable_options(option_payload):
    for section in ("quote_summary", "location_coverage"):
        for item in option_payload.get(section, []):
            name = item["name"]
            if name not in FIELD_METADATA:
                continue
            for option in item.get("options", []):
                if option in OPTION_SENTINELS:
                    continue
                yield name, option


def build_cases():
    option_payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    base = load_base_case()
    cases = []

    for index, (key, option) in enumerate(selectable_options(option_payload), start=1):
        screen, field_label = FIELD_METADATA[key]
        case = deepcopy(base)
        case_id = f"TC_HO_DD_{index:04d}"
        case["TC_ID"] = case_id
        case["TestName"] = (
            f"{screen} {field_label} option - {option}"
        )
        case[key] = option
        case["FirstName"] = f"Dropdown{index:03d}"
        case["LastName"] = slug(key)[:20]
        case["Email"] = f"ho_dropdown_{index:04d}_{{timestamp}}@home.com"
        case["Address"] = f"{300 + index} Old Taunton Ave"
        case["Description"] = case["TestName"]
        case["DropdownScreen"] = screen
        case["DropdownField"] = field_label
        case["DropdownDataKey"] = key
        case["DropdownOption"] = option
        cases.append(case)

    return {
        "metadata": {
            "description": (
                "Generated Homeowner dropdown-option matrix. Each case changes one "
                "Homeowner-specific dropdown value and includes a human-readable Description."
            ),
            "source": str(SOURCE.relative_to(ROOT)),
            "baseCase": "testdata/static/homeowner/HomeData.json::HO_001",
            "caseCount": len(cases),
        },
        "testCases": cases,
    }


def main():
    payload = build_cases()
    atomic_write_json(OUTPUT, payload)
    print(f"Wrote {payload['metadata']['caseCount']} cases to {OUTPUT}")


if __name__ == "__main__":
    main()
