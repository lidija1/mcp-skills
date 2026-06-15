"""Generate canonical Homeowner workflow and discovery JSON data."""

import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOME_DATA = ROOT / "testdata" / "static" / "homeowner" / "HomeData.json"
DISCOVERY_DATA = (
    ROOT
    / "testdata"
    / "static"
    / "homeowner"
    / "HomeownerDiscoveryData.json"
)
HOME_UW_DATA = ROOT / "testdata" / "static" / "homeowner" / "HomeUWData.json"
HOMEOWNER_UW_RULES_DATA = (
    ROOT
    / "testdata"
    / "static"
    / "homeowner"
    / "HomeownerUWRulesData.json"
)


BASE = {
    "CustomerType": "Individual",
    "DOB": "11/10/1992",
    "PhoneNum": "921-549-5577",
    "ZIP": "01101",
    "State": "Massachusetts",
    "City": "Springfield",
    "Producer": "Janis Irey",
    "Program": "Homeowner",
    "BillingMethod": "Direct Billed",
    "ProgramType": "Basic",
    "Term": "12 Months",
    "Prefix": "Mr.",
    "Suffix": "Jr.",
    "DayCare": "No",
    "UndergroundOil": "No",
    "ResidenceRented": "No",
    "ResidenceVacant": "No",
    "Animals": "No",
    "PolicyCoverageOption": "Gold",
    "ResidenceType": "Homeowner",
    "ReplacementCost": "1,200,000",
    "Contents": "720,000",
    "LossOfUse": "240,000",
    "AllPerilsDeductable": "5,000",
    "WindstormDeductable": "5%",
    "Liability": "100,000",
    "MedPayments": "2,000",
    "Renovation": "No",
    "LivedHere": "No",
    "YearBuilt": "2016",
    "RoofType": "Concrete Tile",
    "ConstructionType": "Frame",
    "Loses": "No",
    "ExistingClient": "No",
    "Refused": "No",
    "Declined": "No",
    "ProtectionClass": "2",
    "BCEG": "02",
    "RoofShape": "Hip Roof",
    "SecondaryWaterResistance": "Yes",
    "OpeningProtection": "Class C - Ordinary Non-Impact or None",
    "RoofWallConnection": "Clips",
    "RoofDeck": "Other Roof Deck or Lumber Roof Deck",
    "RoofDeckAttachment": '8d @ 6"/12"',
    "DistanceToShore": "> 5 miles",
    "PerimeterSecurityProtection": "None",
    "PaymentPlan": "Pay In Full",
}


DROPDOWN_OPTIONS = {
    "ProgramType": ["Basic", "Deluxe"],
    "BillingMethod": ["Direct Billed", "Agency Billed"],
    "Term": ["12 Months"],
    "Prefix": ["Br.", "Dr.", "Fr.", "Mr.", "Mrs.", "Ms.", "Prof.", "Rev.", "Sr."],
    "Suffix": ["Esq.", "II", "III", "IV", "Jr.", "MD", "PhD", "Sr.", "V", "VI", "DDS", "JD"],
    "ResidenceType": ["Homeowner", "Condo/Co-op", "Tenants"],
    "PolicyCoverageOption": ["Bronze", "Silver", "Gold", "Platinum"],
    "AllPerilsDeductable": ["500", "1,000", "2,500", "5,000", "10,000", "25,000", "50,000", "100,000", "250,000"],
    "WindstormDeductable": ["2%", "5%", "10%", "15%", "20%", "25%", "None"],
    "Liability": ["100,000", "300,000", "500,000", "1,000,000", "No Coverage"],
    "MedPayments": ["1,000", "2,000", "5,000", "10,000", "15,000"],
    "ConstructionType": ["Fire Resistive", "Frame", "Joisted Masonry", "Masonry Non-Combustible", "Modified Fire-Resistive", "Non-Combustible"],
    "ProtectionClass": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
    "BCEG": ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "99"],
    "RoofType": ["Aluminum Shingles", "Asbestos Shakes", "Asphalt", "Cedar Shakes", "Cedar Shingles", "Clay Tile", "Composition", "Composition (Fiberglass, Asphalt, etc.)", "Concrete Tile", "Copper", "Fiberglass", "Flat", "Metal", "Other", "Plastic", "Poured", "Recycled Roofing Products", "Rock", "Roll Roofing", "Rolled Paper", "Single Ply Membrane Systems", "Slate", "Steel on Steel Joist", "Steel/Porcelain Shingles", "Tar & Gravel (Built-Up)", "Tile", "Tin", "WD Shingles", "Wood Shake/Shingle"],
    "RoofShape": ["Hip Roof", "Other"],
    "SecondaryWaterResistance": ["Yes", "No"],
    "OpeningProtection": ["Class A - Hurricane Impact Glass", "Class A - Hurricane Impact Shutters", "Class B - Basic Impact Glass", "Class B - Basic Impact Shutters", "Class C - Ordinary Non-Impact or None"],
    "RoofWallConnection": ["Toe Nails", "Clips", "Single Wraps", "Double Wraps"],
    "RoofDeck": ["Other Roof Deck or Lumber Roof Deck", "Reinforced Concrete Roof Deck"],
    "RoofDeckAttachment": ['6d @ 6"/12"', '8d @ 6"/12"', '8d @ 6"/6"'],
    "DistanceToShore": ["1 mile - 5 miles", "1001 feet - 1 mile", "< 1000 feet", "> 5 miles"],
    "PerimeterSecurityProtection": ["Closed Circuit TV Camera", "External Motion Activated Detection System", "None", "Both"],
}


OPTIONAL_COVERAGES = [
    "Building Additions and Alteration at other residence",
    "Business Property Extension",
    "Coverage C Increased Special Limit of Liability",
    "Credit Card, Fund Transfer Card, Forgery & Counterfeit Money Coverage Increased Limits",
    "Earthquake Extension",
    "Increased Limits on Personal Property in Other Residences",
    "Other Structures- Increased Limits",
    "Homeowner's Builders Risk Theft Coverage",
    "Permitted Incidental Occupancies",
    "Scheduled Personal Property",
    "Special Computer Coverage",
    "Specific Structures Away From Residence Premises",
    "Watercraft Liability - Under Construction",
    "Watercraft Physical Damage",
    "Waterbed Liability Coverage",
    "Landscape Increased Limits",
    "Water Back Up of Sewers or Drains",
    "Additional Residences Rented to Others",
    "Business Pursuits",
    "Ensuing Fungi Increase",
    "Farmers Personal Liability",
    "Full Time Domestic Employee",
    "Incidental Farming Personal Liability",
    "Incidental Motorized Land Conveyances",
    "Other Insured Location Occupied by Insured",
    "Personal Injury",
]


def case(case_id, test_name, first_name, last_name, address, **updates):
    result = deepcopy(BASE)
    result.update(
        {
            "TC_ID": case_id,
            "TestName": test_name,
            "Description": test_name,
            "FirstName": first_name,
            "LastName": last_name,
            "Email": f"{case_id.lower()}_{{timestamp}}@home.com",
            "Address": address,
        }
    )
    result.update(updates)
    return result


def build_home_cases():
    return [
        case(
            "HO_001",
            "Baseline Homeowner Gold policy with standard limits",
            "Luna",
            "Horton",
            "230 Old Taunton Ave",
        ),
        case(
            "HO_002",
            "Platinum Homeowner policy with mitigation and security controls",
            "Melody",
            "Bray",
            "231 Old Taunton Ave",
            PolicyCoverageOption="Platinum",
            BillingMethod="Agency Billed",
            ProtectionClass="1",
            BCEG="01",
            OpeningProtection="Class A - Hurricane Impact Glass",
            RoofWallConnection="Double Wraps",
            RoofDeck="Reinforced Concrete Roof Deck",
            RoofDeckAttachment='8d @ 6"/6"',
            DistanceToShore="1 mile - 5 miles",
            PerimeterSecurityProtection="Both",
            SecurityProtectionSelections=[
                "Central Reporting Fire Alarm",
                "Central Reporting Burglar Alarm",
                "Residential Sprinkler System",
                "Permanently Installed Generator",
                "Lightning Protection System",
                "Gas Leak Detector",
            ],
        ),
        case(
            "HO_003",
            "Condo Silver policy reveals number of floors and removes other structures",
            "Scott",
            "Alvarado",
            "233 Old Taunton Ave",
            ResidenceType="Condo/Co-op",
            PolicyCoverageOption="Silver",
            NumberOfFloors="8",
            RiskFloor="4",
            ReplacementCost="900,000",
            Contents="540,000",
            LossOfUse="180,000",
        ),
        case(
            "HO_004",
            "Tenants Bronze policy with prior address conditional fields",
            "Wanda",
            "May",
            "222 Old Taunton Ave",
            ResidenceType="Tenants",
            PolicyCoverageOption="Bronze",
            NumberOfFloors="3",
            RiskFloor="2",
            ReplacementCost="",
            Contents="420,000",
            LossOfUse="70,000",
            LivedHere="Yes",
            PriorAddressLine1="18 Previous Street",
            PriorAddressLine2="Unit 4",
            PriorCity="Springfield",
            PriorState="Massachusetts",
            PriorZIP="01103",
            PriorCountry="United States",
        ),
    ]


def discovery_case(case_id, test_name, flow, **updates):
    result = case(
        case_id,
        test_name,
        f"Discovery{case_id[-3:]}",
        flow[:20],
        f"{500 + int(case_id[-3:])} Old Taunton Ave",
        OptionalFlow=flow,
    )
    result.update(updates)
    return result


def build_discovery_cases():
    return [
        discovery_case(
            "HO_DISC_001",
            "Verify every discovered Homeowner dropdown and selectable option",
            "DropdownInventory",
            ExpectedDropdownOptions=DROPDOWN_OPTIONS,
        ),
        discovery_case(
            "HO_DISC_002",
            "Verify prior-address fields appear when residence history is under three years",
            "ConditionalFields",
            LivedHere="Yes",
            PriorAddressLine1="18 Previous Street",
            PriorAddressLine2="Unit 4",
            PriorCity="Springfield",
            PriorState="Massachusetts",
            PriorZIP="01103",
            PriorCountry="United States",
        ),
        discovery_case(
            "HO_DISC_003",
            "Verify all discovered Homeowner optional coverage checkboxes",
            "OptionalCoverages",
            OptionalCoverageSelections=OPTIONAL_COVERAGES,
        ),
        discovery_case(
            "HO_DISC_004",
            "Open Reinsurance Add flow and verify hidden detail fields",
            "Reinsurance",
            ReinsuranceType="Facultative",
            ExpectedReinsuranceTypes=["Facultative", "Treaty"],
        ),
        discovery_case(
            "HO_DISC_005",
            "Open Inspection Add flow and exercise request fields and dropdowns",
            "Inspection",
            InspectionType="Comprehensive",
            InspectionCompany="Inspection Company",
            InspectionCompleted="No",
            InspectionRequestDetails="Homeowner discovery inspection request",
            ExpectedInspectionTypes=["Comprehensive", "Liability", "Property"],
            ExpectedInspectionCompletedOptions=["Yes", "No"],
        ),
        discovery_case(
            "HO_DISC_006",
            "Open Manuscripts Add flow and verify search and manuscript controls",
            "Manuscript",
            ManuscriptSearch="Homeowner",
        ),
        discovery_case(
            "HO_DISC_007",
            "Open Additional Interests and verify all Add entry actions",
            "AdditionalInterests",
            ExpectedAdditionalInterestActions=[
                "Add",
                "Add New Entity",
                "Add New Financial Service Provider",
            ],
        ),
    ]


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def add_test_names(path):
    if not path.exists():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    for case_data in payload.get("testCases", []):
        name = (
            case_data.get("TestName")
            or case_data.get("Description")
            or case_data.get("description")
            or case_data.get("UW_Description")
            or f"Homeowner underwriting case {case_data['TC_ID']}"
        )
        case_data["TestName"] = name
        case_data["Description"] = name
        case_data.pop("description", None)
    write_json(path, payload)


def main():
    write_json(HOME_DATA, {"testCases": build_home_cases()})
    write_json(
        DISCOVERY_DATA,
        {
            "metadata": {
                "description": "Data-driven no-bind coverage for discovered Homeowner controls and Add flows.",
                "caseCount": 7,
            },
            "testCases": build_discovery_cases(),
        },
    )
    add_test_names(HOME_UW_DATA)
    add_test_names(HOMEOWNER_UW_RULES_DATA)
    print(f"Wrote {HOME_DATA}")
    print(f"Wrote {DISCOVERY_DATA}")


if __name__ == "__main__":
    main()
