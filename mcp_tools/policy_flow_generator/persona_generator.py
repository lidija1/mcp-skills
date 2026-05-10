"""
Multi-LOB Persona Generator: Natural Language → structured test-data JSON.

Supports Personal Auto and Homeowner policy-flow lines of business.
Each LOB has a curated schema, known UW trigger rules, and archetype
mappings so the AI produces realistic, immediately runnable test data.
"""

import json
import os
import random
import re
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# Vehicle catalog (auto LOB) — loaded once, sampled per generation call
# ---------------------------------------------------------------------------

_VEHICLE_CATALOG: list | None = None
_VEHICLE_MAKES: set[str] | None = None


def _load_vehicle_catalog() -> list:
    """Flatten docs/auto_vehicle_catalog_*.json → list of {Year, Make, Model, Spec} dicts."""
    global _VEHICLE_CATALOG
    if _VEHICLE_CATALOG is not None:
        return _VEHICLE_CATALOG

    catalog_files = sorted((_PROJECT_ROOT / "docs").glob("auto_vehicle_catalog_*.json"))
    if not catalog_files:
        _VEHICLE_CATALOG = []
        return _VEHICLE_CATALOG

    with open(catalog_files[-1], encoding="utf-8") as fh:
        data = json.load(fh)

    flat = []
    for year_entry in data.get("years", []):
        year = year_entry["year"]
        for make_entry in year_entry.get("makes", []):
            make = make_entry["make"]
            for model_entry in make_entry.get("models", []):
                model = model_entry["model"]
                for spec in model_entry.get("specifications", []):
                    flat.append({"Year": year, "Make": make, "Model": model, "Spec": spec})

    _VEHICLE_CATALOG = flat
    return _VEHICLE_CATALOG


def _sample_vehicles(count: int) -> list:
    """Return `count` distinct vehicles from the catalog (repeats only if count > catalog size)."""
    catalog = _load_vehicle_catalog()
    if not catalog:
        return []
    if count <= len(catalog):
        return random.sample(catalog, count)
    return random.choices(catalog, k=count)


def _normalize_vehicle_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _vehicle_makes() -> set[str]:
    global _VEHICLE_MAKES
    if _VEHICLE_MAKES is None:
        _VEHICLE_MAKES = {
            _normalize_vehicle_text(vehicle["Make"])
            for vehicle in _load_vehicle_catalog()
            if vehicle.get("Make")
        }
    return _VEHICLE_MAKES


def _vehicle_matches_description(vehicle: dict, description: str) -> bool:
    text = f" {_normalize_vehicle_text(description)} "
    make = _normalize_vehicle_text(vehicle.get("Make", ""))
    model = _normalize_vehicle_text(vehicle.get("Model", ""))
    if not make or f" {make} " not in text:
        return False

    model_tokens = [
        token for token in model.split()
        if len(token) > 1 and token not in {"awd", "fwd", "rwd", "2wd", "4wd", "se", "le", "s"}
    ]
    return not model_tokens or any(f" {token} " in text for token in model_tokens)


def _find_vehicle_from_description(description: str) -> dict | None:
    """Return a runnable catalog vehicle when the user explicitly names one."""
    text = f" {_normalize_vehicle_text(description)} "
    if not text.strip():
        return None

    mentioned_makes = [make for make in _vehicle_makes() if f" {make} " in text]
    if not mentioned_makes:
        return None

    catalog = _load_vehicle_catalog()
    exact_model_matches = [
        vehicle for vehicle in catalog
        if _vehicle_matches_description(vehicle, description)
    ]
    if exact_model_matches:
        return sorted(
            exact_model_matches,
            key=lambda vehicle: (str(vehicle.get("Year", "")), str(vehicle.get("Model", ""))),
            reverse=True,
        )[0]

    # User gave a make but no catalog model; keep the make instead of randomizing to another brand.
    make_matches = [
        vehicle for vehicle in catalog
        if _normalize_vehicle_text(vehicle.get("Make", "")) in mentioned_makes
    ]
    if make_matches:
        return sorted(
            make_matches,
            key=lambda vehicle: (str(vehicle.get("Year", "")), str(vehicle.get("Model", ""))),
            reverse=True,
        )[0]

    return None


def _vehicle_constraint_text(vehicle: dict, plural: bool = False) -> str:
    label = "Pre-assigned vehicles" if plural else "Pre-assigned vehicle"
    return (
        f"\n\n{label} — copy these EXACT values into Year/Make/Model/Spec "
        f"(do NOT alter them):\n"
        f"  Year={vehicle['Year']}  Make={vehicle['Make']}  "
        f"Model={vehicle['Model']}  Spec={vehicle['Spec']}"
    )


# ---------------------------------------------------------------------------
# Provider detection
# ---------------------------------------------------------------------------
# Priority:
#   1. AI_PROVIDER env var ("anthropic" or "openai") forces a specific provider
#   2. ANTHROPIC_API_KEY present  → use Anthropic
#   3. OPENAI_API_KEY present     → use OpenAI
#   4. Neither set                → error reported at call time

_ANTHROPIC_MODEL = "claude-opus-4-6"
_OPENAI_MODEL = "gpt-4o"


def _detect_provider() -> str:
    """Return 'anthropic', 'openai', or 'none'."""
    forced = os.getenv("AI_PROVIDER", "").lower().strip()
    if forced in ("anthropic", "openai"):
        return forced
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return "none"

# ---------------------------------------------------------------------------
# Date helpers (computed at import time so prompts stay current)
# ---------------------------------------------------------------------------

_TODAY = date.today()
_EFF_DATE = _TODAY + timedelta(days=1)
_UNDER_25_CUTOFF = _EFF_DATE - timedelta(days=25 * 365 + 6)

# ---------------------------------------------------------------------------
# Per-LOB system prompts
# ---------------------------------------------------------------------------

_AUTO_SYSTEM_PROMPT = f"""
You are a test data generator for a Personal Auto insurance policy automation framework.
Today is {_TODAY.strftime('%Y-%m-%d')}. Default effective date is tomorrow ({_EFF_DATE.strftime('%m/%d/%Y')}); adjust for persona context (past date for backdated/historical scenarios, future date for renewals).

Translate the natural-language persona description into a single valid JSON object.

════════════════════════════════════════════════
FIELD SCHEMA — use ONLY the listed values (case-sensitive)
════════════════════════════════════════════════

{{
  "TC_ID":              "AI_XXXXXX",            // 6-digit random number
  "CustomerType":       "Individual",
  "FirstName":          string,
  "LastName":           string,
  "DOB":                "MM/DD/YYYY",
  "PhoneNum":           "413-555-XXXX",
  "Email":              "firstname_{{timestamp}}@uwtest.com",
  "Address":            string,
  "ZIP":                "01101",
  "State":              "Massachusetts",
  "City":               "Springfield",
  "Producer":           "Janis Irey",
  "EffectiveDate":      "MM/DD/YYYY",         // policy start date; default: {_EFF_DATE.strftime('%m/%d/%Y')}; use a past date for backdated/historical scenarios, future date for renewals
  "Program":            "Personal Auto",
  "BillingMethod":      "Direct Billed",
  "FalseInfo":          "No",
  "DamageInfo":         "Yes" | "No",
  "DescribeDamage":     string,           // REQUIRED if DamageInfo="Yes"; OMIT otherwise
  "Gender":             "Male" | "Female",
  "MaritalStatus":      "Single" | "Married" | "Divorced" | "Widowed",
  "DriverStatus":       "Active (rated)",
  "EmploymentCategory": "Employed" | "Unemployed" | "Retired" | "Student",
  "SR22":               "Yes" | "No",
  "Occupation":         "Day Care",
  "LicenseStatus":      "Active License" | "Suspended" | "Revoked",
  "VehicleType":        "Private Passenger Auto",
  "Year":               string,    // pre-assigned from vehicle catalog — copy exact value from user message
  "Make":               string,    // pre-assigned from vehicle catalog — copy exact value from user message
  "Model":              string,    // pre-assigned from vehicle catalog — copy exact value from user message
  "Spec":               string,    // pre-assigned from vehicle catalog — copy exact value from user message
  "VehicleUse":         "Pleasure" | "Commute" | "Business",
  "Ownership":          "Owned" | "Leased" | "Financed",
  "LossPayeeType":      "Leased" | "Financed",  // REQUIRED when Ownership != "Owned"; OMIT otherwise
  "LossPayeeName":      string,                  // REQUIRED when Ownership != "Owned"; OMIT otherwise
  "PolicyCoverage":     "Bronze" | "Silver" | "Gold" | "Platinum",
  "PaymentPlan":        "Pay In Full"
}}

════════════════════════════════════════════════
UW TRIGGER RULES
════════════════════════════════════════════════

  1. SR22 = "Yes"               → fires SR-22 referral
  2. LicenseStatus = "Suspended" or "Revoked" → fires license referral
  3. Driver DOB after {_UNDER_25_CUTOFF.strftime('%m/%d/%Y')}
                                → fires under-25 referral

════════════════════════════════════════════════
PERSONA ARCHETYPE GUIDE
════════════════════════════════════════════════

  "young_driver" / "under 25"    → DOB between {_UNDER_25_CUTOFF.strftime('%m/%d/%Y')} and today (age 19-24)
  "teen_driver"                  → DOB ~16-18 years ago
  "high_risk_driver"             → SR22="Yes", LicenseStatus="Revoked"
  "triple_risk"                  → SR22="Yes", LicenseStatus="Revoked", DOB after {_UNDER_25_CUTOFF.strftime('%m/%d/%Y')}
  "clean_standard"               → SR22="No", LicenseStatus="Active License", DamageInfo="No"
  "senior_driver"                → DOB ~65-80 years ago, clean record
  "business_driver"              → VehicleUse="Business", EmploymentCategory="Employed"
  "leased_luxury"                → Ownership="Leased", LossPayeeType="Leased", LossPayeeName="BMW Financial Services"
  "multiple_accidents"           → DamageInfo="Yes", DescribeDamage="Multiple prior accident damage on front and rear bumper"
  "full_coverage"                → PolicyCoverage="Platinum"
  "minimum_coverage"             → PolicyCoverage="Bronze"

Return ONLY a valid JSON object. No explanation, markdown, or extra text.
"""

_CYBER_SYSTEM_PROMPT = f"""
You are a test data generator for a Cyber insurance policy automation framework.
Today is {_TODAY.strftime('%Y-%m-%d')}.

Translate the natural-language persona description into a single valid JSON object.

════════════════════════════════════════════════
FIELD SCHEMA — use ONLY the listed values (case-sensitive)
════════════════════════════════════════════════

{{
  "TC_ID":                  "AI_XXXXXX",
  "CustomerType":           "Individual",
  "FirstName":              string,
  "LastName":               string,
  "DOB":                    "MM/DD/YYYY",          // business owner DOB, age 25-70
  "PhoneNum":               "413-555-XXXX",
  "Email":                  "firstname_{{timestamp}}@cybertest.com",
  "Address":                string,
  "ZIP":                    "01101",
  "City":                   "Springfield",
  "Producer":               "Janis Irey",
  "Program":                "Cyber",
  "EffectiveDate":          "MM/DD/YYYY",         // policy start date; default: {_EFF_DATE.strftime('%m/%d/%Y')}; use a past date for backdated/historical scenarios, future date for renewals
  "BillingMethod":          "Direct Billed",
  "BusinessStartDate":      "YYYY",               // 4-digit year only; realistic business founding year
  "TotalEmployees":         string,               // integer as string, e.g. "10"
  "NatureOfBusiness":       "Office" | "Retail" | "Healthcare" | "Technology" | "Education" | "Financial Services" | "Manufacturing",
  "PctOnlineSales":         string,               // 0-100 as string, e.g. "20"
  "AggregateLimit":         "500,000" | "1,000,000" | "2,000,000",
  "PerClaimLimit":          "500,000" | "1,000,000" | "2,000,000",
  "PerClaimDeductible":     "500" | "1,000" | "2,500" | "5,000",
  "CyberTraining":          "Yes" | "No",
  "SituationsLast3Years":   "None" | "Data Breach" | "Ransomware Attack" | "Phishing Attack",
  "CyberRegulations":       "Yes" | "No",
  "PaymentPlan":            "Pay In Full"
}}

════════════════════════════════════════════════
UW TRIGGER RULES (Cyber)
════════════════════════════════════════════════

  - CyberTraining = "No"                    → likely triggers UW review
  - SituationsLast3Years != "None"          → likely triggers UW review
  - CyberRegulations = "No"                 → likely triggers UW review
  - PctOnlineSales > 80%                    → elevated risk flag

════════════════════════════════════════════════
PERSONA ARCHETYPE GUIDE
════════════════════════════════════════════════

  "small_office"          → NatureOfBusiness="Office", TotalEmployees="5-15",
                            PctOnlineSales="5-15", CyberTraining="Yes",
                            SituationsLast3Years="None", CyberRegulations="Yes",
                            AggregateLimit="500,000"

  "high_risk_startup"     → NatureOfBusiness="Technology", TotalEmployees="50+",
                            PctOnlineSales="70-90", CyberTraining="No",
                            SituationsLast3Years="Data Breach" | "Ransomware Attack",
                            CyberRegulations="No", AggregateLimit="2,000,000"

  "established_retail"    → NatureOfBusiness="Retail", TotalEmployees="20-50",
                            PctOnlineSales="30-50", CyberTraining="Yes",
                            SituationsLast3Years="None", CyberRegulations="Yes"

  "healthcare_provider"   → NatureOfBusiness="Healthcare", TotalEmployees="10-30",
                            PctOnlineSales="10", CyberTraining="Yes",
                            CyberRegulations="Yes", AggregateLimit="1,000,000"

  "e_commerce"            → NatureOfBusiness="Retail" | "Technology",
                            PctOnlineSales="80-95", TotalEmployees="10-25",
                            AggregateLimit="2,000,000"

  "financial_services"    → NatureOfBusiness="Financial Services",
                            CyberTraining="Yes", CyberRegulations="Yes",
                            AggregateLimit="2,000,000", PerClaimDeductible="2,500"

  "no_training_no_regs"   → CyberTraining="No", CyberRegulations="No",
                            SituationsLast3Years picks any incident type

Return ONLY a valid JSON object. No explanation, markdown, or extra text.
"""

_HOMEOWNER_SYSTEM_PROMPT = f"""
You are a test data generator for a Homeowner insurance policy automation framework.
Today is {_TODAY.strftime('%Y-%m-%d')}.

Translate the natural-language persona description into a single valid JSON object.

════════════════════════════════════════════════
FIELD SCHEMA — use ONLY the listed values (case-sensitive)
════════════════════════════════════════════════

{{
  "TC_ID":                  "AI_XXXXXX",
  "CustomerType":           "Individual",
  "FirstName":              string,
  "LastName":               string,
  "DOB":                    "MM/DD/YYYY",      // homeowner age 25-75
  "PhoneNum":               "413-555-XXXX",
  "Email":                  "firstname_{{timestamp}}@hometest.com",
  "Address":                string,
  "ZIP":                    "01101",
  "State":                  "Massachusetts",
  "City":                   "Springfield",
  "Producer":               "Janis Irey",
  "Program":                "Homeowner",
  "EffectiveDate":          "MM/DD/YYYY",         // policy start date; default: {_EFF_DATE.strftime('%m/%d/%Y')}; use a past date for backdated/historical scenarios, future date for renewals
  "BillingMethod":          "Direct Billed",
  "ProgramType":            "Basic",
  "DayCare":                "Yes" | "No",
  "UndergroundOil":         "Yes" | "No",
  "ResidenceRented":        "Yes" | "No",
  "ResidenceVacant":        "Yes" | "No",
  "Animals":                "Yes" | "No",
  "PolicyCoverageOption":   "Bronze" | "Silver" | "Gold" | "Platinum",
  "ResidenceType":          "Homeowner",
  "ReplacementCost":        string,            // e.g. "350,000" or "1,200,000"
  "Contents":               string,            // typically ~60% of ReplacementCost
  "AllPerilsDeductable":    "1,000" | "2,500" | "5,000" | "10,000",
  "WindstormDeductable":    "1%" | "2%" | "5%",
  "Liability":              "100,000" | "300,000" | "500,000",
  "MedPayments":            "1,000" | "2,000" | "5,000",
  "Renovation":             "Yes" | "No",      // under construction/major renovation?
  "LivedHere":              "Yes" | "No",      // lived there < 3 years?
  "YearBuilt":              string,            // 4-digit year
  "ConstructionType":       "Frame" | "Masonry" | "Superior",
  "RoofType":               "Concrete Tile" | "Asphalt Shingle" | "Metal" | "Wood Shake",
  "Loses":                  "Yes" | "No",      // any losses in last 3 years?
  "ExistingClient":         "Yes" | "No",
  "Refused":                "Yes" | "No",      // cancelled/refused coverage last 3 years?
  "Declined":               "Yes" | "No",      // non-renewed or declined?
  "PaymentPlan":            "Pay In Full"
}}

NOTE: "AllPerilsDeductable" and "WindstormDeductable" — these spellings are intentional
(match the application field names exactly).

════════════════════════════════════════════════
UW TRIGGER RULES (Homeowner)
════════════════════════════════════════════════

  - Loses = "Yes"         → prior losses — likely triggers UW review
  - Refused = "Yes"       → prior cancellation/refusal — likely triggers UW review
  - Declined = "Yes"      → non-renewed/declined — likely triggers UW review
  - Renovation = "Yes"    → property under construction — elevated risk
  - Very old YearBuilt (< 1950) → elevated risk

════════════════════════════════════════════════
PERSONA ARCHETYPE GUIDE
════════════════════════════════════════════════

  "standard_homeowner"    → ReplacementCost="300,000"-"500,000", Frame construction,
                            Asphalt Shingle roof, YearBuilt 1980-2010,
                            All "No" for risk flags, Gold or Silver coverage

  "high_value_home"       → ReplacementCost="800,000"-"2,000,000", Superior or Masonry,
                            Concrete Tile or Metal roof, YearBuilt 2000-2020,
                            Platinum coverage, high Liability="500,000"

  "risky_property"        → Loses="Yes" or Refused="Yes", old YearBuilt (1940-1970),
                            Renovation="Yes", Asphalt Shingle or Wood Shake roof,
                            Bronze coverage, lower ReplacementCost

  "new_construction"      → YearBuilt 2018-2024, Superior or Frame construction,
                            Metal or Concrete Tile roof, LivedHere="Yes" (moved in recently),
                            Renovation="No", All "No" risk flags, Gold coverage

  "risk_flagged"          → Refused="Yes" AND Declined="Yes", Loses="Yes",
                            older YearBuilt, Wood Shake roof

  "coastal_exposure"      → WindstormDeductable="5%", higher AllPerilsDeductable,
                            Masonry construction, Concrete Tile roof

  "investment_property"   → ResidenceRented="Yes", Animals="Yes",
                            moderate ReplacementCost, standard construction

Return ONLY a valid JSON object. No explanation, markdown, or extra text.
"""

_LOB_PROMPTS = {
    "auto": _AUTO_SYSTEM_PROMPT,
    "homeowner": _HOMEOWNER_SYSTEM_PROMPT,
}
_VALID_LOBS = ", ".join(_LOB_PROMPTS)

# ---------------------------------------------------------------------------
# Archetype reference (returned by list_archetypes)
# ---------------------------------------------------------------------------

PERSONA_ARCHETYPES = {
    "auto": [
        "young_driver — under 25, potential SR-22/license issues, UW referral likely",
        "teen_driver — 16-18 years old, first-time driver",
        "high_risk_driver — SR-22 + revoked licence, strong UW trigger",
        "triple_risk — SR-22 + revoked licence + under 25, all three UW triggers",
        "clean_standard — middle-aged driver, clean record, owned vehicle",
        "senior_driver — 65-80 years old, clean record, commute use",
        "business_driver — business-use vehicle, employed, moderate risk",
        "leased_luxury — leased BMW, financed, loss payee required",
        "multiple_accidents — pre-existing vehicle damage, prior claims",
    ],
    "homeowner": [
        "standard_homeowner — average home, frame construction, clean history",
        "high_value_home — luxury property >$800k replacement cost, premium coverage",
        "risky_property — prior losses, old construction, renovation in progress",
        "new_construction — recently built 2018-2024, modern materials, low risk",
        "risk_flagged — refused + declined + losses, multiple UW triggers",
        "coastal_exposure — windstorm focus, masonry construction, tile roof",
        "investment_property — rented residence, animals, standard coverage",
    ],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_persona(lob: str, description: str) -> str:
    """
    Generate a persona JSON string for the given LOB from a NL description.

    Automatically selects the AI provider based on available API keys:
      - Set AI_PROVIDER=anthropic or AI_PROVIDER=openai to force a provider.
      - Otherwise uses Anthropic if ANTHROPIC_API_KEY is set, else OpenAI.

    Args:
        lob: "auto" or "homeowner"
        description: Natural-language persona, e.g.
            "Young driver aged 21 with SR-22 on a leased vehicle" (auto)
            "High-value home with history of losses and renovation" (homeowner)

    Returns:
        JSON string (one persona dict) or JSON with "error" key on failure.
    """
    lob = lob.lower().strip()
    if lob not in _LOB_PROMPTS:
        return json.dumps({
            "error": f"Unknown LOB '{lob}'. Valid options: {_VALID_LOBS}"
        })

    provider = _detect_provider()
    system_prompt = _LOB_PROMPTS[lob]

    vehicle_constraint = ""
    if lob == "auto":
        vehicles = _sample_vehicles(1)
        if vehicles:
            v = vehicles[0]
            vehicle_constraint = (
                f"\n\nPre-assigned vehicle — copy these EXACT values into Year/Make/Model/Spec "
                f"(do NOT alter them):\n"
                f"  Year={v['Year']}  Make={v['Make']}  Model={v['Model']}  Spec={v['Spec']}"
            )

    if lob == "auto":
        requested_vehicle = _find_vehicle_from_description(description)
        if requested_vehicle:
            vehicle_constraint = _vehicle_constraint_text(requested_vehicle)

    user_message = f"Generate test data for this {lob.upper()} persona: {description}{vehicle_constraint}"
    raw = ""

    try:
        if provider == "anthropic":
            import anthropic as _anthropic
            client = _anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            message = client.messages.create(
                model=_ANTHROPIC_MODEL,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            raw = message.content[0].text.strip()

        elif provider == "openai":
            import openai as _openai
            client = _openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model=_OPENAI_MODEL,
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            raw = response.choices[0].message.content.strip()

        else:
            return json.dumps({
                "error": (
                    "No AI provider configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY "
                    "in your .env file, or set AI_PROVIDER=anthropic|openai explicitly."
                )
            })

        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        parsed = json.loads(raw)
        parsed["_lob"] = lob
        parsed["_provider"] = provider
        return json.dumps(parsed)

    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"Model returned non-JSON: {exc}", "raw": raw})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def list_archetypes(lob: str | None = None) -> str:
    """Return available persona archetypes as a formatted string."""
    if lob:
        lob = lob.lower().strip()
        if lob not in PERSONA_ARCHETYPES:
            return f"Unknown LOB '{lob}'. Valid: {_VALID_LOBS}"
        archetypes = {lob: PERSONA_ARCHETYPES[lob]}
    else:
        archetypes = PERSONA_ARCHETYPES

    lines = []
    for l, items in archetypes.items():
        lines.append(f"\n### {l.upper()} Personas")
        for item in items:
            lines.append(f"  • {item}")
    return "\n".join(lines)


def generate_persona_variations(lob: str, base_description: str, count: int) -> str:
    """
    Generate `count` distinct persona variations for the given LOB, all inspired
    by `base_description`. Uses a single AI call requesting a JSON array so
    the model can produce meaningfully different personas in one pass.

    Returns a JSON string: an array of persona dicts, or a dict with "error".
    """
    lob = lob.lower().strip()
    if lob not in _LOB_PROMPTS:
        return json.dumps({"error": f"Unknown LOB '{lob}'. Valid: {_VALID_LOBS}"})

    count = max(1, min(count, 25))  # hard-clamp

    base_system = _LOB_PROMPTS[lob]
    original_tail = "Return ONLY a valid JSON object. No explanation, markdown, or extra text."
    array_instructions = (
        f"\n\n════════════════════════════════════════════════\n"
        f"ARRAY MODE — Generate {count} distinct variations\n"
        f"════════════════════════════════════════════════\n\n"
        f"Return a JSON ARRAY of exactly {count} persona objects.\n"
        f"Each object must be complete and valid (all required fields present).\n"
        f"Each object must also include a \"_note\" field: a single sentence describing "
        f"what makes this variation distinct from the others "
        f"(e.g. \"Young driver with SR-22 and revoked licence\" or "
        f"\"Senior clean-record driver on a leased luxury vehicle\").\n"
        f"Vary key attributes across the {count} personas — names, ages, coverage levels,\n"
        f"risk characteristics, vehicle/property details, and personal details — so\n"
        f"every persona is meaningfully different, not a minor copy of the previous one.\n"
        f"Stay true to the base description theme (LOB, risk class, coverage tier).\n\n"
        f"Return ONLY a JSON ARRAY (starts with '[', ends with ']'). No extra text."
    )

    if original_tail in base_system:
        system_prompt = base_system.replace(original_tail, array_instructions)
    else:
        system_prompt = base_system + "\n\n" + array_instructions

    vehicle_section = ""
    if lob == "auto":
        vehicles = _sample_vehicles(count)
        requested_vehicle = _find_vehicle_from_description(base_description)
        if requested_vehicle:
            vehicles = [requested_vehicle for _ in range(count)]
        if vehicles:
            lines = [
                f"  [{i}] Year={v['Year']}  Make={v['Make']}  "
                f"Model={v['Model']}  Spec={v['Spec']}"
                for i, v in enumerate(vehicles)
            ]
            vehicle_section = (
                "\n\nPre-assigned vehicles — assign vehicles[i] to persona index i. "
                "Copy Year/Make/Model/Spec EXACTLY; do NOT alter those four fields:\n"
                + "\n".join(lines)
            )

    user_message = (
        f"Generate exactly {count} distinct {lob.upper()} persona variations based on: "
        f"{base_description}\n\n"
        f"Return a JSON array of {count} complete persona objects."
        f"{vehicle_section}"
    )

    provider = _detect_provider()
    raw = ""
    try:
        if provider == "anthropic":
            import anthropic as _anthropic
            client = _anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            message = client.messages.create(
                model=_ANTHROPIC_MODEL,
                max_tokens=8192,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            raw = message.content[0].text.strip()

        elif provider == "openai":
            import openai as _openai
            client = _openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model=_OPENAI_MODEL,
                max_tokens=8192,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            raw = response.choices[0].message.content.strip()

        else:
            return json.dumps({
                "error": (
                    "No AI provider configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY "
                    "in your .env file."
                )
            })

        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            parsed = [parsed]  # model returned single object — wrap it

        for idx, persona in enumerate(parsed):
            if isinstance(persona, dict):
                persona["_lob"] = lob
                persona["_provider"] = provider
                persona["_variation_index"] = idx

        return json.dumps(parsed, indent=2)

    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"Model returned non-JSON: {exc}", "raw": raw[:500]})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def generate_batch_personas(scenarios: list) -> str:
    """
    Generate multiple persona JSON objects without executing browser flows.

    Each item in `scenarios` must be a dict with "lob" and "description" keys.
    Returns a JSON array where each element is the persona object (or an error
    object) for that scenario, with an added "_scenario_index" field.
    """
    results = []
    for i, scenario in enumerate(scenarios):
        lob = str(scenario.get("lob", "")).lower().strip()
        description = str(scenario.get("description", "")).strip()

        if not lob or not description:
            results.append({
                "error": f"Scenario {i}: missing 'lob' or 'description'",
                "_scenario_index": i,
            })
            continue

        raw = generate_persona(lob, description)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"error": f"Non-JSON response for scenario {i}", "raw": raw}

        parsed["_scenario_index"] = i
        results.append(parsed)

    return json.dumps(results, indent=2)
