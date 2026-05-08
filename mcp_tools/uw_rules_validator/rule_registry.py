"""
UW Rules Registry — pre-defined edge cases with expected outcomes.

Each entry in RULE_CASES defines:
  - case_id          : unique identifier
  - rule_id          : groups cases under one rule (for validate_rule filtering)
  - rule_name        : human-readable rule label
  - lob              : "auto" | "cyber" | "homeowner"
  - case_type        : "positive" (should trigger UW) | "negative" (should bind) | "boundary"
  - severity         : "critical" | "high" | "warning"
  - description      : what this case is testing
  - persona          : full test-data dict, immediately runnable
  - expected_outcome : "uw_referral" | "policy_bound"
  - expected_conditions : list of substrings that must appear in UW condition text
                           (case-sensitive, same matching used by UWReferralPage.assert_uw_condition)
  - min_conditions   : minimum number of UW condition rows expected (None = don't check)

Auto confirmed condition substrings (from auto_uw_rules.feature):
  SR-22    → "SR-22 / Certificate of Insurance Indicator is checked"
  License  → "driver license status that is revoked or suspended"
  Under 25 → "All drivers under 25 years of age"
"""

from datetime import date, timedelta

_TODAY = date.today()
_EFF_DATE = _TODAY + timedelta(days=1)

# DOB on or before this date = driver is >= 25 on effective date (NO trigger)
# DOB after this date        = driver is <  25 on effective date (triggers under-25 rule)
_UNDER_25_CUTOFF = _EFF_DATE - timedelta(days=25 * 365 + 6)

# Boundary DOBs (computed dynamically so tests stay valid regardless of run date)
_EXACTLY_25_DOB = _UNDER_25_CUTOFF.strftime("%m/%d/%Y")           # exactly 25 → no trigger
_JUST_UNDER_25_DOB = (_UNDER_25_CUTOFF + timedelta(days=1)).strftime("%m/%d/%Y")  # 24y 364d → triggers

# ---------------------------------------------------------------------------
# Condition text constants (substring match, case-sensitive)
# ---------------------------------------------------------------------------
COND_SR22 = "SR-22 / Certificate of Insurance Indicator is checked"
COND_LICENSE = "driver license status that is revoked or suspended"
COND_UNDER25 = "All drivers under 25 years of age"

# ---------------------------------------------------------------------------
# Shared base fields (overridden per case)
# ---------------------------------------------------------------------------
_AUTO_BASE = {
    "CustomerType": "Individual",
    "ZIP": "01101",
    "State": "Massachusetts",
    "City": "Springfield",
    "Producer": "Janis Irey",
    "EffDateOffset": "1",
    "Program": "Personal Auto",
    "BillingMethod": "Direct Billed",
    "FalseInfo": "No",
    "DamageInfo": "No",
    "DriverStatus": "Active (rated)",
    "Occupation": "Day Care",
    "VehicleType": "Private Passenger Auto",
    "Year": "2018",
    "Make": "BMW",
    "Model": "M3",
    "Spec": "Convertible 2-Door | 2WD | 4.0 Ltrs | 4x2",
    "PaymentPlan": "Pay In Full",
}

_CYBER_BASE = {
    "CustomerType": "Individual",
    "ZIP": "01101",
    "City": "Springfield",
    "Producer": "Janis Irey",
    "Program": "Cyber",
    "EffDateOffset": "1",
    "BillingMethod": "Direct Billed",
    "PaymentPlan": "Pay In Full",
}

_HOMEOWNER_BASE = {
    "CustomerType": "Individual",
    "ZIP": "01101",
    "State": "Massachusetts",
    "City": "Springfield",
    "Producer": "Janis Irey",
    "Program": "Homeowner",
    "EffDateOffset": "1",
    "BillingMethod": "Direct Billed",
    "ProgramType": "Basic",
    "DayCare": "No",
    "UndergroundOil": "No",
    "ResidenceRented": "No",
    "ResidenceVacant": "No",
    "Animals": "No",
    "ResidenceType": "Homeowner",
    "PaymentPlan": "Pay In Full",
}


def _auto(case_id, rule_id, rule_name, case_type, severity, description,
          expected_outcome, expected_conditions, min_conditions=None, **fields):
    persona = {**_AUTO_BASE, "TC_ID": case_id, **fields}
    return {
        "case_id": case_id,
        "rule_id": rule_id,
        "rule_name": rule_name,
        "lob": "auto",
        "case_type": case_type,
        "severity": severity,
        "description": description,
        "persona": persona,
        "expected_outcome": expected_outcome,
        "expected_conditions": expected_conditions,
        "min_conditions": min_conditions,
    }


def _cyber(case_id, rule_id, rule_name, case_type, severity, description,
           expected_outcome, expected_conditions, min_conditions=None, **fields):
    persona = {**_CYBER_BASE, "TC_ID": case_id, **fields}
    return {
        "case_id": case_id,
        "rule_id": rule_id,
        "rule_name": rule_name,
        "lob": "cyber",
        "case_type": case_type,
        "severity": severity,
        "description": description,
        "persona": persona,
        "expected_outcome": expected_outcome,
        "expected_conditions": expected_conditions,
        "min_conditions": min_conditions,
    }


def _homeowner(case_id, rule_id, rule_name, case_type, severity, description,
               expected_outcome, expected_conditions, min_conditions=None, **fields):
    persona = {**_HOMEOWNER_BASE, "TC_ID": case_id, **fields}
    return {
        "case_id": case_id,
        "rule_id": rule_id,
        "rule_name": rule_name,
        "lob": "homeowner",
        "case_type": case_type,
        "severity": severity,
        "description": description,
        "persona": persona,
        "expected_outcome": expected_outcome,
        "expected_conditions": expected_conditions,
        "min_conditions": min_conditions,
    }


# ===========================================================================
# AUTO RULE CASES
# ===========================================================================

RULE_CASES = [

    # ── Rule: SR-22 ──────────────────────────────────────────────────────────

    _auto(
        case_id="UW_TC_001",
        rule_id="AUTO_SR22",
        rule_name="SR-22 Certificate Required",
        case_type="positive",
        severity="critical",
        description="SR-22 only — isolated trigger, clean license, adult driver. Must refer.",
        expected_outcome="uw_referral",
        expected_conditions=[COND_SR22],
        min_conditions=1,
        FirstName="Tyler", LastName="Hendricks", DOB="06/15/1993",
        PhoneNum="413-555-0101", Email="thendricks_{timestamp}@uwtest.com",
        Address="88 Walnut Street",
        Gender="Male", MaritalStatus="Single", EmploymentCategory="Employed",
        SR22="Yes", LicenseStatus="Active License",
        VehicleUse="Pleasure", Ownership="Owned", PolicyCoverage="Silver",
    ),

    _auto(
        case_id="UW_TC_NEG_SR22",
        rule_id="AUTO_SR22",
        rule_name="SR-22 Certificate Required",
        case_type="negative",
        severity="critical",
        description="No SR-22, clean record, adult driver. Must NOT refer on SR-22 rule.",
        expected_outcome="policy_bound",
        expected_conditions=[],
        min_conditions=None,
        FirstName="Laura", LastName="Bennett", DOB="07/20/1985",
        PhoneNum="413-555-0110", Email="lbennett_{timestamp}@uwtest.com",
        Address="99 Elm Street",
        Gender="Female", MaritalStatus="Married", EmploymentCategory="Employed",
        SR22="No", LicenseStatus="Active License",
        VehicleUse="Commute", Ownership="Owned", PolicyCoverage="Gold",
    ),

    # ── Rule: License Status ─────────────────────────────────────────────────

    _auto(
        case_id="UW_TC_002",
        rule_id="AUTO_LICENSE",
        rule_name="Suspended/Revoked Licence",
        case_type="positive",
        severity="critical",
        description="Suspended licence only — no SR-22, no age factor. Must refer.",
        expected_outcome="uw_referral",
        expected_conditions=[COND_LICENSE],
        min_conditions=1,
        FirstName="Brandon", LastName="Kelley", DOB="03/22/1987",
        PhoneNum="413-555-0202", Email="bkelley_{timestamp}@uwtest.com",
        Address="14 Forest Avenue",
        Gender="Male", MaritalStatus="Married", EmploymentCategory="Employed",
        SR22="No", LicenseStatus="Suspended",
        VehicleUse="Pleasure", Ownership="Owned", PolicyCoverage="Gold",
    ),

    _auto(
        case_id="UW_TC_004",
        rule_id="AUTO_LICENSE",
        rule_name="Suspended/Revoked Licence",
        case_type="positive",
        severity="critical",
        description="Revoked licence only — no SR-22, adult driver. Must refer.",
        expected_outcome="uw_referral",
        expected_conditions=[COND_LICENSE],
        min_conditions=1,
        FirstName="Derek", LastName="Patterson", DOB="11/05/1990",
        PhoneNum="413-555-0404", Email="dpatterson_{timestamp}@uwtest.com",
        Address="77 Spruce Court",
        Gender="Male", MaritalStatus="Single", EmploymentCategory="Employed",
        SR22="No", LicenseStatus="Revoked",
        VehicleUse="Commute", Ownership="Owned", PolicyCoverage="Bronze",
    ),

    # ── Rule: Under 25 ──────────────────────────────────────────────────────

    _auto(
        case_id="UW_TC_003",
        rule_id="AUTO_UNDER25",
        rule_name="Driver Under 25 Years of Age",
        case_type="positive",
        severity="critical",
        description="Age 21 driver, active licence, no SR-22 — isolated age trigger. Must refer.",
        expected_outcome="uw_referral",
        expected_conditions=[COND_UNDER25],
        min_conditions=1,
        FirstName="Marcus", LastName="Crawford", DOB="08/14/2004",
        PhoneNum="413-555-0303", Email="mcrawford_{timestamp}@uwtest.com",
        Address="302 Hickory Lane",
        Gender="Male", MaritalStatus="Single", EmploymentCategory="Employed",
        SR22="No", LicenseStatus="Active License",
        VehicleUse="Commute", Ownership="Owned", PolicyCoverage="Gold",
    ),

    _auto(
        case_id="UW_TC_011",
        rule_id="AUTO_UNDER25",
        rule_name="Driver Under 25 Years of Age",
        case_type="positive",
        severity="critical",
        description="Age 18 driver (minimum boundary) — must trigger under-25 rule.",
        expected_outcome="uw_referral",
        expected_conditions=[COND_UNDER25],
        min_conditions=1,
        FirstName="Austin", LastName="Drummond", DOB="03/28/2008",
        PhoneNum="413-555-1111", Email="adrummond_{timestamp}@uwtest.com",
        Address="61 Cypress Way",
        Gender="Male", MaritalStatus="Single", EmploymentCategory="Employed",
        SR22="No", LicenseStatus="Active License",
        VehicleUse="Commute", Ownership="Owned", PolicyCoverage="Gold",
    ),

    _auto(
        case_id="UW_BOUNDARY_25_UNDER",
        rule_id="AUTO_UNDER25",
        rule_name="Driver Under 25 Years of Age",
        case_type="boundary",
        severity="critical",
        description=(
            f"Driver born {_JUST_UNDER_25_DOB} — exactly 1 day under 25 on effective date. "
            "MUST trigger under-25 rule (hardest boundary edge case)."
        ),
        expected_outcome="uw_referral",
        expected_conditions=[COND_UNDER25],
        min_conditions=1,
        FirstName="Jamie", LastName="Vance", DOB=_JUST_UNDER_25_DOB,
        PhoneNum="413-555-2501", Email="jvance_{timestamp}@uwtest.com",
        Address="1 Boundary Lane",
        Gender="Male", MaritalStatus="Single", EmploymentCategory="Student",
        SR22="No", LicenseStatus="Active License",
        VehicleUse="Pleasure", Ownership="Owned", PolicyCoverage="Bronze",
    ),

    _auto(
        case_id="UW_BOUNDARY_25_EXACT",
        rule_id="AUTO_UNDER25",
        rule_name="Driver Under 25 Years of Age",
        case_type="boundary",
        severity="critical",
        description=(
            f"Driver born {_EXACTLY_25_DOB} — exactly 25 on effective date. "
            "Must NOT trigger under-25 rule (upper boundary, inclusive)."
        ),
        expected_outcome="policy_bound",
        expected_conditions=[],
        min_conditions=None,
        FirstName="Sam", LastName="Cross", DOB=_EXACTLY_25_DOB,
        PhoneNum="413-555-2502", Email="scross_{timestamp}@uwtest.com",
        Address="2 Boundary Lane",
        Gender="Female", MaritalStatus="Single", EmploymentCategory="Employed",
        SR22="No", LicenseStatus="Active License",
        VehicleUse="Commute", Ownership="Owned", PolicyCoverage="Silver",
    ),

    # ── Rule: Combined — SR-22 + Under 25 ───────────────────────────────────

    _auto(
        case_id="UW_TC_005",
        rule_id="AUTO_COMBINED_SR22_UNDER25",
        rule_name="SR-22 + Under 25 (Double Risk)",
        case_type="positive",
        severity="critical",
        description="Age 20 with SR-22 — both triggers must fire simultaneously.",
        expected_outcome="uw_referral",
        expected_conditions=[COND_SR22, COND_UNDER25],
        min_conditions=2,
        FirstName="Ethan", LastName="Morrison", DOB="03/28/2006",
        PhoneNum="413-555-0505", Email="emorrison_{timestamp}@uwtest.com",
        Address="25 Poplar Drive",
        Gender="Male", MaritalStatus="Single", EmploymentCategory="Employed",
        SR22="Yes", LicenseStatus="Active License",
        VehicleUse="Business", Ownership="Owned", PolicyCoverage="Platinum",
    ),

    # ── Rule: Combined — SR-22 + Suspended ──────────────────────────────────

    _auto(
        case_id="UW_TC_006",
        rule_id="AUTO_COMBINED_SR22_LICENSE",
        rule_name="SR-22 + Suspended Licence (Double Risk)",
        case_type="positive",
        severity="critical",
        description="Adult with SR-22 + suspended licence — both triggers must fire.",
        expected_outcome="uw_referral",
        expected_conditions=[COND_SR22, COND_LICENSE],
        min_conditions=2,
        FirstName="Harold", LastName="Whitfield", DOB="03/28/1988",
        PhoneNum="413-555-0606", Email="hwhitfield_{timestamp}@uwtest.com",
        Address="103 Magnolia Blvd",
        Gender="Male", MaritalStatus="Married", EmploymentCategory="Employed",
        SR22="Yes", LicenseStatus="Suspended",
        VehicleUse="Pleasure", Ownership="Owned", PolicyCoverage="Silver",
    ),

    _auto(
        case_id="UW_TC_012",
        rule_id="AUTO_COMBINED_SR22_LICENSE",
        rule_name="SR-22 + Suspended Licence (Double Risk)",
        case_type="positive",
        severity="critical",
        description="Adult with SR-22 + revoked licence — most severe licence/compliance combo.",
        expected_outcome="uw_referral",
        expected_conditions=[COND_SR22, COND_LICENSE],
        min_conditions=2,
        FirstName="Randall", LastName="Becker", DOB="04/25/1985",
        PhoneNum="413-555-1212", Email="rbecker_{timestamp}@uwtest.com",
        Address="33 Juniper Place",
        Gender="Male", MaritalStatus="Divorced", EmploymentCategory="Employed",
        SR22="Yes", LicenseStatus="Revoked",
        VehicleUse="Commute", Ownership="Owned", PolicyCoverage="Bronze",
    ),

    # ── Rule: Combined — Under 25 + Leased ──────────────────────────────────

    _auto(
        case_id="UW_TC_008",
        rule_id="AUTO_COMBINED_UNDER25_LEASED",
        rule_name="Under 25 + Leased Vehicle",
        case_type="positive",
        severity="high",
        description="Age 22 on leased vehicle — under-25 trigger plus loss payee requirements.",
        expected_outcome="uw_referral",
        expected_conditions=[COND_UNDER25],
        min_conditions=1,
        FirstName="Nathan", LastName="Fielding", DOB="05/30/2003",
        PhoneNum="413-555-0808", Email="nfielding_{timestamp}@uwtest.com",
        Address="200 Chestnut Street",
        Gender="Male", MaritalStatus="Single", EmploymentCategory="Employed",
        SR22="No", LicenseStatus="Active License",
        VehicleUse="Commute", Ownership="Leased",
        LossPayeeType="Leased", LossPayeeName="BMW Financial Services",
        PolicyCoverage="Gold",
    ),

    # ── Rule: Combined — Under 25 + Suspended ───────────────────────────────

    _auto(
        case_id="UW_TC_009",
        rule_id="AUTO_COMBINED_UNDER25_LICENSE",
        rule_name="Under 25 + Suspended Licence (Double Risk)",
        case_type="positive",
        severity="critical",
        description="Age 22 with suspended licence — both under-25 and licence triggers must fire.",
        expected_outcome="uw_referral",
        expected_conditions=[COND_UNDER25, COND_LICENSE],
        min_conditions=2,
        FirstName="Gregory", LastName="Ashford", DOB="07/11/2003",
        PhoneNum="413-555-0909", Email="gashford_{timestamp}@uwtest.com",
        Address="46 Willow Path",
        Gender="Male", MaritalStatus="Single", EmploymentCategory="Employed",
        SR22="No", LicenseStatus="Suspended",
        VehicleUse="Commute", Ownership="Owned", PolicyCoverage="Silver",
    ),

    # ── Rule: Combined — SR-22 + Leased ─────────────────────────────────────

    _auto(
        case_id="UW_TC_010",
        rule_id="AUTO_COMBINED_SR22_LEASED",
        rule_name="SR-22 + Leased Vehicle",
        case_type="positive",
        severity="critical",
        description="SR-22 driver on leased vehicle — SR-22 trigger plus loss payee form.",
        expected_outcome="uw_referral",
        expected_conditions=[COND_SR22],
        min_conditions=1,
        FirstName="Calvin", LastName="Monroe", DOB="02/17/1991",
        PhoneNum="413-555-1010", Email="cmonroe_{timestamp}@uwtest.com",
        Address="19 Sycamore Road",
        Gender="Male", MaritalStatus="Single", EmploymentCategory="Employed",
        SR22="Yes", LicenseStatus="Active License",
        VehicleUse="Commute", Ownership="Leased",
        LossPayeeType="Leased", LossPayeeName="BMW Financial Services",
        PolicyCoverage="Gold",
    ),

    # ── Rule: Triple Risk ────────────────────────────────────────────────────

    _auto(
        case_id="UW_TC_007",
        rule_id="AUTO_TRIPLE_RISK",
        rule_name="Triple Risk: SR-22 + Revoked + Under 25",
        case_type="positive",
        severity="critical",
        description=(
            "Age 22, revoked licence, SR-22, prior damage — ALL three UW conditions must fire. "
            "Most extreme risk profile."
        ),
        expected_outcome="uw_referral",
        expected_conditions=[COND_SR22, COND_LICENSE, COND_UNDER25],
        min_conditions=3,
        FirstName="Victor", LastName="Sloane", DOB="09/19/2003",
        PhoneNum="413-555-0707", Email="vsloane_{timestamp}@uwtest.com",
        Address="55 Redwood Circle",
        Gender="Male", MaritalStatus="Single", EmploymentCategory="Employed",
        SR22="Yes", LicenseStatus="Revoked",
        DamageInfo="Yes", DescribeDamage="Rear-end collision damage on trunk lid and bumper",
        VehicleUse="Business", Ownership="Owned", PolicyCoverage="Platinum",
    ),

    # ── Negative: Clean profile (must bind, zero UW) ─────────────────────────

    _auto(
        case_id="UW_NEGATIVE_CLEAN",
        rule_id="AUTO_CLEAN_BASELINE",
        rule_name="Clean Profile — No Risk Factors",
        case_type="negative",
        severity="critical",
        description=(
            "Ideal-risk adult driver: active licence, no SR-22, age 38, owned vehicle, "
            "commute use. Must bind without any UW referral."
        ),
        expected_outcome="policy_bound",
        expected_conditions=[],
        min_conditions=None,
        FirstName="Michael", LastName="Thornton", DOB="04/12/1987",
        PhoneNum="413-555-9900", Email="mthornton_{timestamp}@uwtest.com",
        Address="45 Maple Grove",
        Gender="Male", MaritalStatus="Married", EmploymentCategory="Employed",
        SR22="No", LicenseStatus="Active License",
        VehicleUse="Commute", Ownership="Owned", PolicyCoverage="Gold",
    ),

    # ===========================================================================
    # CYBER RULE CASES
    # ===========================================================================

    _cyber(
        case_id="CY_UW_001",
        rule_id="CYBER_HIGH_RISK",
        rule_name="No Training + Past Incident (Cyber High-Risk)",
        case_type="positive",
        severity="high",
        description=(
            "No employee cyber training, past ransomware attack, no regulations — "
            "maximum cyber risk profile. Expect UW referral."
        ),
        expected_outcome="uw_referral",
        expected_conditions=[],   # Exact condition text not confirmed for Cyber
        min_conditions=None,
        FirstName="Steve", LastName="Ramos", DOB="03/14/1980",
        PhoneNum="413-555-3001", Email="sramos_{timestamp}@uwtest.com",
        Address="18 Commerce Blvd",
        BusinessStartDate="2022", TotalEmployees="45",
        NatureOfBusiness="Technology", PctOnlineSales="85",
        AggregateLimit="2,000,000", PerClaimLimit="2,000,000",
        PerClaimDeductible="5,000",
        CyberTraining="No", SituationsLast3Years="Ransomware Attack",
        CyberRegulations="No",
    ),

    _cyber(
        case_id="CY_UW_002",
        rule_id="CYBER_HIGH_RISK",
        rule_name="No Training + Past Incident (Cyber High-Risk)",
        case_type="positive",
        severity="high",
        description=(
            "Past data breach, no training, no regulations — second high-risk variant."
        ),
        expected_outcome="uw_referral",
        expected_conditions=[],
        min_conditions=None,
        FirstName="Dana", LastName="Fischer", DOB="08/22/1978",
        PhoneNum="413-555-3002", Email="dfischer_{timestamp}@uwtest.com",
        Address="200 Retail Row",
        BusinessStartDate="2020", TotalEmployees="30",
        NatureOfBusiness="Retail", PctOnlineSales="75",
        AggregateLimit="1,000,000", PerClaimLimit="1,000,000",
        PerClaimDeductible="2,500",
        CyberTraining="No", SituationsLast3Years="Data Breach",
        CyberRegulations="No",
    ),

    _cyber(
        case_id="CY_NEGATIVE_CLEAN",
        rule_id="CYBER_CLEAN_BASELINE",
        rule_name="Full Compliance — Low Risk (Cyber Clean)",
        case_type="negative",
        severity="high",
        description=(
            "Established office, full training, no incidents, compliant with regulations. "
            "Should bind without UW referral."
        ),
        expected_outcome="policy_bound",
        expected_conditions=[],
        min_conditions=None,
        FirstName="James", LastName="Smith", DOB="05/15/1985",
        PhoneNum="413-555-3010", Email="jsmith_{timestamp}@uwtest.com",
        Address="123 Main St",
        BusinessStartDate="2010", TotalEmployees="25",
        NatureOfBusiness="Office", PctOnlineSales="20",
        AggregateLimit="1,000,000", PerClaimLimit="1,000,000",
        PerClaimDeductible="500",
        CyberTraining="Yes", SituationsLast3Years="None",
        CyberRegulations="Yes",
    ),

    # ===========================================================================
    # HOMEOWNER RULE CASES
    # ===========================================================================

    _homeowner(
        case_id="HO_UW_001",
        rule_id="HO_PRIOR_LOSSES",
        rule_name="Prior Losses in Last 3 Years",
        case_type="positive",
        severity="high",
        description=(
            "Homeowner with prior losses in last 3 years — risk flag set. Expect UW referral."
        ),
        expected_outcome="uw_referral",
        expected_conditions=[],   # Exact condition text not confirmed for Homeowner
        min_conditions=None,
        FirstName="Patricia", LastName="Chambers", DOB="06/30/1970",
        PhoneNum="413-555-4001", Email="pchambers_{timestamp}@uwtest.com",
        Address="77 Old Oak Road",
        PolicyCoverageOption="Bronze", ReplacementCost="350,000",
        Contents="210,000", AllPerilsDeductable="10,000",
        WindstormDeductable="5%", Liability="100,000", MedPayments="1,000",
        Renovation="No", LivedHere="No", YearBuilt="1965",
        ConstructionType="Frame", RoofType="Asphalt",
        Loses="Yes", ExistingClient="No", Refused="No", Declined="No",
    ),

    _homeowner(
        case_id="HO_UW_002",
        rule_id="HO_REFUSED_DECLINED",
        rule_name="Previously Refused / Declined Coverage",
        case_type="positive",
        severity="critical",
        description=(
            "Coverage previously refused AND declined by another insurer — "
            "maximum red flags. Expect UW referral."
        ),
        expected_outcome="uw_referral",
        expected_conditions=[],
        min_conditions=None,
        FirstName="Robert", LastName="Granger", DOB="11/14/1960",
        PhoneNum="413-555-4002", Email="rgranger_{timestamp}@uwtest.com",
        Address="12 Birchwood Court",
        PolicyCoverageOption="Bronze", ReplacementCost="275,000",
        Contents="165,000", AllPerilsDeductable="10,000",
        WindstormDeductable="5%", Liability="100,000", MedPayments="1,000",
        Renovation="Yes", LivedHere="No", YearBuilt="1952",
        ConstructionType="Frame", RoofType="Wood Shake/Shingle",
        Loses="Yes", ExistingClient="No", Refused="Yes", Declined="Yes",
    ),

    _homeowner(
        case_id="HO_UW_003",
        rule_id="HO_ALL_FLAGS",
        rule_name="All Risk Flags Active (Maximum Homeowner Risk)",
        case_type="positive",
        severity="critical",
        description=(
            "All risk flags set: losses, refused, declined, renovation — "
            "most extreme homeowner risk profile. Expect UW referral."
        ),
        expected_outcome="uw_referral",
        expected_conditions=[],
        min_conditions=None,
        FirstName="Helen", LastName="Pruitt", DOB="04/09/1958",
        PhoneNum="413-555-4003", Email="hpruitt_{timestamp}@uwtest.com",
        Address="5 Riskview Terrace",
        PolicyCoverageOption="Bronze", ReplacementCost="250,000",
        Contents="150,000", AllPerilsDeductable="10,000",
        WindstormDeductable="5%", Liability="100,000", MedPayments="1,000",
        Renovation="Yes", LivedHere="Yes", YearBuilt="1945",
        ConstructionType="Frame", RoofType="Wood Shake/Shingle",
        Loses="Yes", ExistingClient="No", Refused="Yes", Declined="Yes",
    ),

    _homeowner(
        case_id="HO_NEGATIVE_CLEAN",
        rule_id="HO_CLEAN_BASELINE",
        rule_name="Clean History — Low Risk (Homeowner Clean)",
        case_type="negative",
        severity="high",
        description=(
            "New construction 2020, modern materials, no losses, no refusals. "
            "Should bind without UW referral."
        ),
        expected_outcome="policy_bound",
        expected_conditions=[],
        min_conditions=None,
        FirstName="Lunaaaaa", LastName="Horton222", DOB="11/10/1992",
        PhoneNum="921-549-5577", Email="testuser1101_{timestamp}@home.com",
        Address="230 Old Taunton Ave",
        PolicyCoverageOption="Gold", ReplacementCost="1,200,000",
        Contents="720,000", AllPerilsDeductable="5,000",
        WindstormDeductable="5%", Liability="100,000", MedPayments="2,000",
        Renovation="No", LivedHere="Yes", YearBuilt="2016",
        ConstructionType="Frame", RoofType="Concrete Tile",
        Loses="No", ExistingClient="No", Refused="No", Declined="No",
    ),
]

# ---------------------------------------------------------------------------
# Quick-lookup indexes
# ---------------------------------------------------------------------------

CASES_BY_ID = {c["case_id"]: c for c in RULE_CASES}
CASES_BY_LOB = {}
CASES_BY_RULE = {}

for _c in RULE_CASES:
    CASES_BY_LOB.setdefault(_c["lob"], []).append(_c)
    CASES_BY_RULE.setdefault(_c["rule_id"], []).append(_c)

# Rule metadata for list_uw_rules
RULE_METADATA = {}
for _c in RULE_CASES:
    _rid = _c["rule_id"]
    if _rid not in RULE_METADATA:
        RULE_METADATA[_rid] = {
            "rule_id": _rid,
            "rule_name": _c["rule_name"],
            "lob": _c["lob"],
            "severity": _c["severity"],
            "case_ids": [],
        }
    RULE_METADATA[_rid]["case_ids"].append(_c["case_id"])
