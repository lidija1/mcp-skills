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
import tempfile
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from mcp_tools.policy_flow_generator.persona_validator import (
    PersonaValidationError,
    validate_persona,
)

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


def _apply_vehicle_from_catalog(persona: dict, vehicle: dict | None) -> dict:
    """Force generated auto vehicle fields to match the local vehicle catalog."""
    if not vehicle:
        return persona
    persona["Year"] = str(vehicle["Year"])
    persona["Make"] = str(vehicle["Make"])
    persona["Model"] = str(vehicle["Model"])
    persona["Spec"] = str(vehicle["Spec"])
    return persona


def _ollama_base_url() -> str:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip().rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    return base


def _ollama_chat(system_prompt: str, user_message: str, max_tokens: int) -> str:
    payload = {
        "model": _OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "options": {
            "temperature": 0,
            "num_predict": max_tokens,
        },
        "format": "json",
    }
    data = json.dumps(payload).encode("utf-8")
    attempts = max(1, int(os.getenv("PERSONA_OLLAMA_RETRIES", "2")))
    last_error = "Ollama response did not contain message.content."

    for _ in range(attempts):
        req = urllib.request.Request(
            f"{_ollama_base_url()}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Ollama is not reachable at {_ollama_base_url()}. Start Ollama or update OLLAMA_BASE_URL."
            ) from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("Ollama returned a non-JSON HTTP response.") from exc

        message = body.get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        last_error = f"{last_error} done_reason={body.get('done_reason')!r}"

    raise RuntimeError(last_error)


def _generate_persona_with_ollama(lob: str, system_prompt: str, user_message: str, description: str) -> str:
    raw = _ollama_chat(system_prompt, user_message, max_tokens=2048)
    parsed = _parse_model_json(raw)
    parsed = _normalize_model_persona(lob, parsed)
    parsed["_lob"] = lob
    parsed["_provider"] = "ollama"
    _ensure_persona_type(lob, parsed, description)
    _ensure_unique_email(parsed, lob)
    parsed = validate_persona(lob, parsed)
    return json.dumps(parsed)


def _generate_persona_variations_with_ollama(
    lob: str,
    count: int,
    system_prompt: str,
    user_message: str,
    base_description: str,
) -> str:
    raw = _ollama_chat(system_prompt, user_message, max_tokens=8192)
    parsed = _parse_model_json(raw)
    if not isinstance(parsed, list):
        parsed = [parsed]
    if len(parsed) < count:
        raise ValueError(f"Model returned only {len(parsed)} variation(s), expected {count}.")

    for idx, persona in enumerate(parsed):
        if isinstance(persona, dict):
            persona = _normalize_model_persona(lob, persona)
            parsed[idx] = persona
            persona["_lob"] = lob
            persona["_provider"] = "ollama"
            persona["_variation_index"] = idx
            _ensure_persona_type(lob, persona, base_description)
            _ensure_unique_email(persona, lob, extra=idx)
            parsed[idx] = validate_persona(lob, persona)

    return json.dumps(parsed[:count], indent=2)


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
_DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
_DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
_OLLAMA_BASE_URL = "http://localhost:11434/v1"
_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")


def _detect_provider() -> str:
    """Return 'anthropic', 'openai', 'ollama', or 'none'."""
    forced = os.getenv("AI_PROVIDER", "").lower().strip()
    if forced in ("anthropic", "openai", "deepseek", "ollama"):
        return forced
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("DEEPSEEK_API_KEY"):
        return "deepseek"
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
  "SR22FilingState":    "Massachusetts",        // REQUIRED when SR22="Yes"; otherwise omit
  "Occupation":         "Day Care",
  "LicenseStatus":      "Active License" | "Suspended" | "Revoked",
  "VehicleType":        "Private Passenger Auto",
  "Year":               string,    // pre-assigned from vehicle catalog — copy exact value from user message
  "Make":               string,    // pre-assigned from vehicle catalog — copy exact value from user message
  "Model":              string,    // pre-assigned from vehicle catalog — copy exact value from user message
  "Spec":               string,    // pre-assigned from vehicle catalog — copy exact value from user message
  "VehicleUse":         "Pleasure" | "Commute" | "Business",
  "DistanceToWork":     string,    // miles one-way; REQUIRED when VehicleUse="Commute" (e.g. "10"); OMIT otherwise
  "Ownership":          "Owned" | "Leased" | "Financed",
  "LossPayeeType":      "Leased" | "Financed",  // REQUIRED when Ownership != "Owned"; OMIT otherwise
  "LossPayeeName":      string,                  // REQUIRED when Ownership != "Owned"; OMIT otherwise
  "PolicyCoverage":     "Bronze" | "Silver" | "Gold" | "Platinum",
  "PaymentPlan":        "Pay In Full",
  "FullTimeStudent":    "Yes" | "No",   // OMIT unless driver is under 25 and persona implies student status
  "VehicleWithStudentAtSchool": "Yes" | "No",  // REQUIRED when FullTimeStudent="Yes"; OMIT otherwise
  "GoodStudent":        "Yes" | "No",   // REQUIRED when FullTimeStudent="Yes"; "Yes" if GPA >= B average; OMIT otherwise
  "DefensiveDriver":    "Yes" | "No"    // "Yes" if persona completed a defensive driver course; OMIT or "No" otherwise
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
  "good_student"                 → DOB after {_UNDER_25_CUTOFF.strftime('%m/%d/%Y')} (age 19-24), EmploymentCategory="Student", FullTimeStudent="Yes", VehicleWithStudentAtSchool="No", GoodStudent="Yes"
  "defensive_driver"             → DefensiveDriver="Yes" (any age)
  "low_mileage_commuter"         → VehicleUse="Commute", DistanceToWork="5"
  "high_mileage_commuter"        → VehicleUse="Commute", DistanceToWork="50"

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
    "cyber": _CYBER_SYSTEM_PROMPT,
    "homeowner": _HOMEOWNER_SYSTEM_PROMPT,
}
_VALID_LOBS = ", ".join(_LOB_PROMPTS)
_VARIATION_CHUNK_SIZE = 10
_EMAIL_SEQUENCE = 0


def _email_domain_for_lob(lob: str) -> str:
    return {
        "auto": "uwtest.com",
        "cyber": "cybertest.com",
        "homeowner": "hometest.com",
    }.get(lob, "uwtest.com")


def _email_local_part(value: str) -> str:
    local = re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")
    return local or "customer"


def _current_time_token(extra: str = "") -> str:
    global _EMAIL_SEQUENCE
    _EMAIL_SEQUENCE += 1
    token = datetime.now().strftime("%Y%m%d%H%M%S%f")
    suffix = re.sub(r"[^a-zA-Z0-9]+", "", str(extra or ""))
    sequence = f"{_EMAIL_SEQUENCE:04d}"
    return f"{token}{suffix}{sequence}" if suffix else f"{token}{sequence}"


def _ensure_unique_email(persona: dict, lob: str, extra: str = "") -> None:
    """Mutate a generated persona so Email contains this computer's current time."""
    if not isinstance(persona, dict):
        return

    raw_email = str(persona.get("Email") or "").strip()
    timestamp = _current_time_token(extra)

    if "{timestamp}" in raw_email:
        persona["Email"] = raw_email.replace("{timestamp}", timestamp)
        return

    if "@" in raw_email:
        local, domain = raw_email.rsplit("@", 1)
        persona["Email"] = f"{_email_local_part(local)}_{timestamp}@{domain.strip() or _email_domain_for_lob(lob)}"
        return

    first_name = persona.get("FirstName") or persona.get("CustomerName") or lob
    persona["Email"] = f"{_email_local_part(first_name)}_{timestamp}@{_email_domain_for_lob(lob)}"


def _age_from_dob(dob: object) -> int | None:
    try:
        parsed = datetime.strptime(str(dob), "%m/%d/%Y").date()
    except (TypeError, ValueError):
        return None
    age = _TODAY.year - parsed.year - (( _TODAY.month, _TODAY.day) < (parsed.month, parsed.day))
    return age


def _ensure_persona_type(lob: str, persona: dict, description: str = "") -> None:
    if not isinstance(persona, dict) or persona.get("_persona_type"):
        return

    text = str(description or "").lower()
    if lob == "auto":
        age = _age_from_dob(persona.get("DOB"))
        sr22 = str(persona.get("SR22")) == "Yes"
        license_status = str(persona.get("LicenseStatus") or "")
        ownership = str(persona.get("Ownership") or "")
        vehicle_use = str(persona.get("VehicleUse") or "")

        if sr22 and license_status in {"Revoked", "Suspended"} and age is not None and age < 25:
            persona["_persona_type"] = "triple_risk"
        elif sr22 or license_status in {"Revoked", "Suspended"}:
            persona["_persona_type"] = "high_risk_driver"
        elif age is not None and age < 25:
            persona["_persona_type"] = "young_driver"
        elif vehicle_use == "Business" or "business" in text:
            persona["_persona_type"] = "business_driver"
        elif ownership == "Leased" and _contains_any(text, "bmw", "luxury", "leased"):
            persona["_persona_type"] = "leased_luxury"
        else:
            persona["_persona_type"] = "clean_standard"
        return

    if lob == "homeowner":
        loses = str(persona.get("Loses")) == "Yes"
        refused = str(persona.get("Refused")) == "Yes"
        declined = str(persona.get("Declined")) == "Yes"
        renovation = str(persona.get("Renovation")) == "Yes"
        rented = str(persona.get("ResidenceRented")) == "Yes"
        year_built = str(persona.get("YearBuilt") or "")
        replacement_cost = str(persona.get("ReplacementCost") or "").replace(",", "")
        try:
            replacement_num = int(replacement_cost)
        except ValueError:
            replacement_num = 0
        coastal = _contains_any(text, "coastal", "wind", "shore", "beach") or str(persona.get("WindstormDeductable")) == "5%"
        high_value = replacement_num >= 800000 or str(persona.get("PolicyCoverageOption")) == "Platinum"

        if refused and declined and loses:
            persona["_persona_type"] = "risk_flagged"
        elif high_value:
            persona["_persona_type"] = "high_value_home"
        elif coastal:
            persona["_persona_type"] = "coastal_exposure"
        elif rented:
            persona["_persona_type"] = "investment_property"
        elif year_built.isdigit() and int(year_built) >= 2018:
            persona["_persona_type"] = "new_construction"
        elif loses or refused or declined or renovation or (year_built.isdigit() and int(year_built) < 1950):
            persona["_persona_type"] = "risky_property"
        else:
            persona["_persona_type"] = "standard_homeowner"
        return

    if lob == "cyber":
        if str(persona.get("CyberTraining")) == "No" or str(persona.get("CyberRegulations")) == "No" or str(persona.get("SituationsLast3Years")) != "None":
            persona["_persona_type"] = "high_risk_startup"
        elif str(persona.get("NatureOfBusiness")) == "Healthcare":
            persona["_persona_type"] = "healthcare_provider"
        else:
            persona["_persona_type"] = "small_office"
        return

    persona["_persona_type"] = "custom"


def _clean_model_json(raw: str) -> str:
    """Return the likely JSON payload from a model response."""
    cleaned = (raw or "").strip()
    # Strip <think>...</think> blocks emitted by reasoning models (e.g. qwen3)
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL).strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    starts = [idx for idx in (cleaned.find("["), cleaned.find("{")) if idx != -1]
    if not starts:
        return cleaned

    start = min(starts)
    end_array = cleaned.rfind("]")
    end_object = cleaned.rfind("}")
    end = max(end_array, end_object)
    if end >= start:
        return cleaned[start:end + 1].strip()
    return cleaned[start:].strip()


def _parse_model_json(raw: str):
    return json.loads(_clean_model_json(raw))


def _normalize_model_persona(lob: str, persona):
    if not isinstance(persona, dict):
        return persona

    if lob == "auto":
        sr22_aliases = ("SR2022", "SR_22", "SR-22", "SR22Indicator")
        if "SR22" not in persona:
            for alias in sr22_aliases:
                if alias in persona:
                    persona["SR22"] = persona.pop(alias)
                    break
        else:
            for alias in sr22_aliases:
                persona.pop(alias, None)

    return persona


# ---------------------------------------------------------------------------
# Fast local persona generation
# ---------------------------------------------------------------------------

_FIRST_NAMES = [
    "Alex",
    "Jordan",
    "Morgan",
    "Taylor",
    "Casey",
    "Jamie",
    "Riley",
    "Avery",
]
_LAST_NAMES = [
    "Parker",
    "Miller",
    "Johnson",
    "Rivera",
    "Nguyen",
    "Carter",
    "Brooks",
    "Reed",
]
_STREET_NAMES = [
    "Maple Street",
    "Oak Avenue",
    "Pine Terrace",
    "Union Street",
    "Main Street",
    "Birch Lane",
]


def _contains_any(text: str, *terms: str) -> bool:
    return any(term in text for term in terms)


def _make_tc_id() -> str:
    return f"AI_{random.randint(100000, 999999)}"


def _pick_name() -> tuple[str, str]:
    return random.choice(_FIRST_NAMES), random.choice(_LAST_NAMES)


def _dob_for_age(age: int) -> str:
    age = max(16, min(age, 85))
    return date(_TODAY.year - age, random.randint(1, 12), random.randint(1, 28)).strftime("%m/%d/%Y")


def _extract_age(description: str, default: int) -> int:
    text = description.lower()
    match = re.search(r"\b(?:age|aged)\s*(\d{2})\b", text)
    if not match:
        match = re.search(r"\b(\d{2})\s*[- ]?\s*(?:year|yr)[ -]?old\b", text)
    if not match:
        match = re.search(r"\bover\s+(\d{2})\b", text)
    if match:
        return max(16, min(int(match.group(1)), 85))
    return default


def _phone() -> str:
    return f"413-555-{random.randint(1000, 9999)}"


def _address(prefix: str = "") -> str:
    label = f"{prefix} " if prefix else ""
    return f"{random.randint(100, 999)} {label}{random.choice(_STREET_NAMES)}"


def _format_money(value: int) -> str:
    return f"{value:,}"


def _base_customer(lob: str, description: str, default_age: int) -> dict:
    first_name, last_name = _pick_name()
    return {
        "TC_ID": _make_tc_id(),
        "CustomerType": "Individual",
        "FirstName": first_name,
        "LastName": last_name,
        "DOB": _dob_for_age(_extract_age(description, default_age)),
        "PhoneNum": _phone(),
        "Email": f"{_email_local_part(first_name)}_{{timestamp}}@{_email_domain_for_lob(lob)}",
        "Address": _address(),
        "ZIP": "01101",
        "State": "Massachusetts",
        "City": "Springfield",
        "Producer": "Janis Irey",
        "EffectiveDate": _EFF_DATE.strftime("%m/%d/%Y"),
        "BillingMethod": "Direct Billed",
        "PaymentPlan": "Pay In Full",
    }


def _coverage_from_text(text: str, default: str = "Gold") -> str:
    if _contains_any(text, "platinum", "full coverage", "full-coverage"):
        return "Platinum"
    if _contains_any(text, "gold"):
        return "Gold"
    if _contains_any(text, "silver"):
        return "Silver"
    if _contains_any(text, "bronze", "minimum", "basic"):
        return "Bronze"
    return default


def _fast_auto_persona(description: str, vehicle: dict | None) -> dict:
    text = description.lower()
    age = _extract_age(description, 42)
    if _contains_any(text, "young", "under 25"):
        age = min(age, 22)
    elif _contains_any(text, "teen", "first-time driver"):
        age = 18
    elif _contains_any(text, "senior", "retired"):
        age = max(age, 70)

    persona = _base_customer("auto", description, age)
    sr22 = _contains_any(text, "sr-22", "sr22")
    license_status = "Active License"
    if "revoked" in text:
        license_status = "Revoked"
    elif "suspended" in text:
        license_status = "Suspended"

    ownership = "Owned"
    if "leased" in text:
        ownership = "Leased"
    elif "financed" in text or "loan" in text:
        ownership = "Financed"

    vehicle_use = "Business" if "business" in text else "Commute" if "commute" in text else "Pleasure"
    employment = "Retired" if "retired" in text else "Student" if "student" in text or age < 23 else "Employed"
    damage = _contains_any(text, "damage", "accident", "claim", "loss")
    if vehicle is None:
        sampled = _sample_vehicles(1)
        vehicle = sampled[0] if sampled else {
            "Year": "2020",
            "Make": "Toyota",
            "Model": "Camry",
            "Spec": "LE 4dr Sedan",
        }

    persona.update({
        "DOB": _dob_for_age(age),
        "Program": "Personal Auto",
        "FalseInfo": "No",
        "DamageInfo": "Yes" if damage else "No",
        "Gender": "Female" if persona["FirstName"] in {"Taylor", "Riley", "Avery"} else "Male",
        "MaritalStatus": "Married" if age >= 30 else "Single",
        "DriverStatus": "Active (rated)",
        "EmploymentCategory": employment,
        "SR22": "Yes" if sr22 else "No",
        "Occupation": "Day Care",
        "LicenseStatus": license_status,
        "VehicleType": "Private Passenger Auto",
        "Year": str(vehicle["Year"]),
        "Make": str(vehicle["Make"]),
        "Model": str(vehicle["Model"]),
        "Spec": str(vehicle["Spec"]),
        "VehicleUse": vehicle_use,
        "Ownership": ownership,
        "PolicyCoverage": _coverage_from_text(text),
    })

    if damage:
        persona["DescribeDamage"] = "Prior accident damage noted on the vehicle"
    if sr22:
        persona["SR22FilingState"] = "Massachusetts"
    if ownership != "Owned":
        persona["LossPayeeType"] = ownership
        persona["LossPayeeName"] = (
            "BMW Financial Services"
            if "bmw" in text
            else "Leasing Company" if ownership == "Leased"
            else "Auto Finance Company"
        )

    if sr22 and license_status != "Active License" and age < 25:
        persona["_persona_type"] = "triple_risk"
    elif sr22 or license_status != "Active License":
        persona["_persona_type"] = "high_risk_driver"
    elif age < 25:
        persona["_persona_type"] = "young_driver"
    elif "business" in text:
        persona["_persona_type"] = "business_driver"
    else:
        persona["_persona_type"] = "clean_standard"
    return persona


def _fast_homeowner_persona(description: str) -> dict:
    text = description.lower()
    persona = _base_customer("homeowner", description, 45)
    high_value = _contains_any(text, "luxury", "high value", "high-value", "expensive")
    coastal = _contains_any(text, "coastal", "wind", "shore", "beach")
    old_home = _contains_any(text, "old", "historic", "older")
    new_home = _contains_any(text, "new construction", "newly built", "new home")
    rented = _contains_any(text, "rented", "rental", "investment")
    losses = _contains_any(text, "loss", "losses", "claim", "claims")
    refused = _contains_any(text, "refused", "cancelled", "canceled")
    declined = _contains_any(text, "declined", "non-renew", "nonrenew")
    renovation = _contains_any(text, "renovation", "renovating", "under construction")

    replacement = 950000 if high_value else 650000 if coastal else 320000
    if old_home and not high_value:
        replacement = 280000
    contents = int(replacement * 0.6)
    loss_of_use = int(replacement * 0.2)
    other_structures = int(replacement * 0.1)

    persona.update({
        "Program": "Homeowner",
        "ProgramType": "Basic",
        "DayCare": "No",
        "UndergroundOil": "Yes" if old_home else "No",
        "ResidenceRented": "Yes" if rented else "No",
        "ResidenceVacant": "No",
        "Animals": "Yes" if rented or "dog" in text or "animal" in text else "No",
        "PolicyCoverageOption": _coverage_from_text(text, "Platinum" if high_value else "Gold"),
        "ResidenceType": "Homeowner",
        "ReplacementCost": _format_money(replacement),
        "Contents": _format_money(contents),
        "LossOfUse": _format_money(loss_of_use),
        "OtherStructures": _format_money(other_structures),
        "AllPerilsDeductable": "5,000" if coastal or high_value else "1,000",
        "WindstormDeductable": "5%" if coastal else "2%",
        "Liability": "500,000" if high_value else "300,000",
        "MedPayments": "5,000" if high_value else "1,000",
        "Renovation": "Yes" if renovation else "No",
        "LivedHere": "Yes" if new_home else "No",
        "YearBuilt": "1938" if old_home else "2021" if new_home else "1998",
        "ConstructionType": "Masonry" if coastal else "Superior" if high_value else "Frame",
        "RoofType": "Concrete Tile" if coastal else "Metal" if new_home else "Asphalt Shingle",
        "Loses": "Yes" if losses else "No",
        "ExistingClient": "No",
        "Refused": "Yes" if refused else "No",
        "Declined": "Yes" if declined else "No",
    })

    if refused and declined and losses:
        persona["_persona_type"] = "risk_flagged"
    elif high_value:
        persona["_persona_type"] = "high_value_home"
    elif coastal:
        persona["_persona_type"] = "coastal_exposure"
    elif rented:
        persona["_persona_type"] = "investment_property"
    elif new_home:
        persona["_persona_type"] = "new_construction"
    elif losses or refused or declined or renovation or old_home:
        persona["_persona_type"] = "risky_property"
    else:
        persona["_persona_type"] = "standard_homeowner"
    return persona


def _fast_cyber_persona(description: str) -> dict:
    text = description.lower()
    persona = _base_customer("cyber", description, 38)
    healthcare = _contains_any(text, "healthcare", "clinic", "medical", "hospital")
    technology = _contains_any(text, "technology", "software", "startup", "saas")
    financial = _contains_any(text, "financial", "bank", "fintech")
    retail = _contains_any(text, "retail", "ecommerce", "e-commerce", "online sales")
    education = _contains_any(text, "school", "education", "university")
    manufacturing = "manufacturing" in text
    prior_incident = "ransomware" in text or "phishing" in text or "breach" in text
    no_training = _contains_any(text, "no training", "poor controls", "poor control")
    no_regs = _contains_any(text, "no regulation", "no regulations", "non-compliant", "non compliant")

    if healthcare:
        nature = "Healthcare"
    elif technology:
        nature = "Technology"
    elif financial:
        nature = "Financial Services"
    elif retail:
        nature = "Retail"
    elif education:
        nature = "Education"
    elif manufacturing:
        nature = "Manufacturing"
    else:
        nature = "Office"

    incident = "None"
    if "ransomware" in text:
        incident = "Ransomware Attack"
    elif "phishing" in text:
        incident = "Phishing Attack"
    elif "breach" in text or prior_incident:
        incident = "Data Breach"

    high_risk = prior_incident or no_training or no_regs
    high_limit = technology or financial or high_risk
    persona.update({
        "Program": "Cyber",
        "BusinessStartDate": "2018" if technology else "2012",
        "TotalEmployees": "55" if high_limit else "12",
        "NatureOfBusiness": nature,
        "PctOnlineSales": "85" if retail or technology else "20",
        "AggregateLimit": "2,000,000" if high_limit else "1,000,000",
        "PerClaimLimit": "1,000,000" if high_limit else "500,000",
        "PerClaimDeductible": "2,500" if high_limit else "1,000",
        "CyberTraining": "No" if no_training else "Yes",
        "SituationsLast3Years": incident,
        "CyberRegulations": "No" if no_regs else "Yes",
        "_persona_type": "high_risk_startup" if high_risk else "healthcare_provider" if healthcare else "small_office",
    })
    return persona


def _build_fast_persona(lob: str, description: str, vehicle: dict | None = None) -> dict:
    if lob == "auto":
        persona = _fast_auto_persona(description, vehicle)
    elif lob == "homeowner":
        persona = _fast_homeowner_persona(description)
    elif lob == "cyber":
        persona = _fast_cyber_persona(description)
    else:
        raise ValueError(f"Unknown LOB '{lob}'. Valid options: {_VALID_LOBS}")
    persona["_lob"] = lob
    persona["_provider"] = "local-fast"
    _ensure_unique_email(persona, lob)
    return persona


_FAST_VARIATION_THEMES = {
    "auto": [
        ("young SR-22 driver with revoked license and Platinum coverage", "Young high-risk driver with SR-22 and revoked license"),
        ("suspended license, financed vehicle, commute use, Silver coverage", "Suspended-license driver on a financed commute vehicle"),
        ("leased luxury BMW, full coverage, business use", "Leased luxury vehicle with business use"),
        ("senior retired driver, clean record, owned vehicle, Gold coverage", "Senior clean-record owned-vehicle profile"),
        ("student first-time driver under 25, Bronze coverage", "Student first-time driver with minimum coverage"),
        ("prior accident damage, active license, owned vehicle", "Driver with prior vehicle damage"),
        ("SR-22 filing, active license, owned vehicle, Silver coverage", "SR-22 filing with otherwise active license"),
        ("clean adult driver, commute use, owned vehicle, Gold coverage", "Clean standard adult driver"),
    ],
    "homeowner": [
        ("coastal wind exposure, masonry construction, tile roof, Platinum coverage", "Coastal wind-exposed property"),
        ("prior losses, renovation in progress, older home", "Older property with losses and renovation"),
        ("new construction, modern roof, no losses, Gold coverage", "New construction with clean history"),
        ("rented investment property with animals", "Rented investment property"),
        ("refused and declined by prior carrier with losses", "Prior carrier refusal and loss history"),
        ("luxury high-value home with high liability limits", "High-value luxury home"),
        ("standard frame construction, clean history, Basic coverage", "Standard homeowner profile"),
        ("historic older property with underground oil tank", "Historic property with older-home risk"),
    ],
    "cyber": [
        ("healthcare business with ransomware incident and no training", "Healthcare business with ransomware exposure"),
        ("technology startup, high online sales, weak controls", "Technology startup with weak controls"),
        ("financial services firm with compliance exposure", "Financial services compliance exposure"),
        ("retail ecommerce business with phishing incident", "Retail ecommerce phishing exposure"),
        ("education organization with clean controls and training", "Education organization with clean controls"),
        ("manufacturing business with data breach history", "Manufacturing business with breach history"),
        ("small office with training, no prior incidents", "Small office clean cyber risk"),
        ("SaaS company with no cyber regulations and high limits", "SaaS company with high-limit exposure"),
    ],
}


def _variation_text(lob: str, base_description: str, index: int) -> tuple[str, str]:
    themes = _FAST_VARIATION_THEMES.get(lob, [])
    if not themes:
        return base_description, f"Variation {index + 1}"
    extra, note = themes[index % len(themes)]
    cycle = index // len(themes)
    cycle_text = f"; variant cycle {cycle + 1}" if cycle else ""
    return f"{base_description}; {extra}{cycle_text}", note


def _build_fast_persona_variations(
    lob: str,
    base_description: str,
    count: int,
    vehicles: list | None = None,
) -> list[dict]:
    personas = []
    for index in range(count):
        description, note = _variation_text(lob, base_description, index)
        vehicle = vehicles[index] if vehicles and index < len(vehicles) else None
        persona = _build_fast_persona(lob, description, vehicle)
        persona["_variation_index"] = index
        persona["_note"] = note
        personas.append(persona)
    return personas


def _fast_batch_persona(i: int, scenario: dict) -> dict:
    lob = str(scenario.get("lob", "")).lower().strip()
    description = str(scenario.get("description", "")).strip()

    if not lob or not description:
        return {"error": f"Scenario {i}: missing 'lob' or 'description'", "_scenario_index": i}
    if lob not in _LOB_PROMPTS:
        return {"error": f"Scenario {i}: unknown LOB '{lob}'", "_scenario_index": i}

    vehicle = None
    if lob == "auto":
        vehicle = _find_vehicle_from_description(description)
        if vehicle is None:
            sampled = _sample_vehicles(1)
            vehicle = sampled[0] if sampled else None

    try:
        persona = _build_fast_persona(lob, description, vehicle)
    except Exception as exc:
        persona = {"error": str(exc)}
    persona["_scenario_index"] = i
    return persona

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
    "cyber": [
        "small_office - low-risk office with training, controls, and no incidents",
        "healthcare_provider - healthcare business with compliance-sensitive exposure",
        "high_risk_startup - poor controls, no training, or prior cyber incident",
        "e_commerce - high online sales and elevated transaction exposure",
        "financial_services - regulated financial profile with higher limits",
    ],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def atomic_write_json(path, data, *, indent: int = 2, encoding: str = "utf-8") -> None:
    """Write `data` as JSON to `path` atomically.

    Writes to a sibling .tmp file first, then calls os.replace() which is an
    atomic rename on both Windows NTFS and Linux.  The original file is never
    partially overwritten — a crash during the write leaves it intact.

    Args:
        path: str or pathlib.Path destination.
        data: JSON-serialisable object.
        indent: JSON pretty-print indent (default 2).
        encoding: File encoding (default utf-8).
    """
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=indent, ensure_ascii=False)
    fd, tmp_path = tempfile.mkstemp(dir=dest.parent, prefix=dest.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as fh:
            fh.write(payload)
        os.replace(tmp_path, dest)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


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

    vehicle = None
    vehicle_constraint = ""
    if lob == "auto":
        vehicles = _sample_vehicles(1)
        if vehicles:
            vehicle = vehicles[0]
            vehicle_constraint = (
                f"\n\nPre-assigned vehicle — copy these EXACT values into Year/Make/Model/Spec "
                f"(do NOT alter them):\n"
                f"  Year={vehicle['Year']}  Make={vehicle['Make']}  "
                f"Model={vehicle['Model']}  Spec={vehicle['Spec']}"
            )

    if lob == "auto":
        requested_vehicle = _find_vehicle_from_description(description)
        if requested_vehicle:
            vehicle = requested_vehicle
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

        elif provider == "deepseek":
            import openai as _openai
            client = _openai.OpenAI(
                api_key=os.getenv("DEEPSEEK_API_KEY"),
                base_url=_DEEPSEEK_BASE_URL,
            )
            response = client.chat.completions.create(
                model=_DEEPSEEK_MODEL,
                max_tokens=1024,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            raw = response.choices[0].message.content.strip()

        elif provider == "ollama":
            return _generate_persona_with_ollama(lob, system_prompt, user_message, description)

        else:
            return json.dumps({
                "error": (
                    "No AI provider configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY "
                    "in your .env file, or set AI_PROVIDER=anthropic|openai|ollama explicitly."
                )
            })

        parsed = _parse_model_json(raw)
        parsed = _normalize_model_persona(lob, parsed)
        if lob == "auto":
            _apply_vehicle_from_catalog(parsed, vehicle)
        parsed["_lob"] = lob
        parsed["_provider"] = provider
        _ensure_persona_type(lob, parsed, description)
        _ensure_unique_email(parsed, lob)
        parsed = validate_persona(lob, parsed)
        return json.dumps(parsed)

    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"Model returned non-JSON: {exc}", "raw": raw})
    except PersonaValidationError as exc:
        return json.dumps({
            "error": "Persona validation failed",
            "lob": exc.lob,
            "validation_errors": exc.errors,
        })
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


def _generate_persona_variation_chunk(
    lob: str,
    base_description: str,
    count: int,
    start_index: int,
    vehicles: list | None = None,
) -> list:
    """Generate a small persona-variation chunk."""
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
        f"This is chunk starting at overall variation index {start_index}. "
        f"Do not reuse names or risk-detail wording from earlier chunks.\n\n"
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

        elif provider == "deepseek":
            import openai as _openai
            client = _openai.OpenAI(
                api_key=os.getenv("DEEPSEEK_API_KEY"),
                base_url=_DEEPSEEK_BASE_URL,
            )
            response = client.chat.completions.create(
                model=_DEEPSEEK_MODEL,
                max_tokens=8192,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            raw = response.choices[0].message.content.strip()

        elif provider == "ollama":
            raw = _ollama_chat(system_prompt, user_message, max_tokens=8192)

        else:
            return json.dumps({
                "error": (
                    "No AI provider configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY "
                    "in your .env file."
                )
            })

        parsed = _parse_model_json(raw)
        if not isinstance(parsed, list):
            parsed = [parsed]  # model returned single object — wrap it

        for idx, persona in enumerate(parsed):
            if isinstance(persona, dict):
                persona = _normalize_model_persona(lob, persona)
                if lob == "auto" and vehicles and idx < len(vehicles):
                    _apply_vehicle_from_catalog(persona, vehicles[idx])
                parsed[idx] = persona
                persona["_lob"] = lob
                persona["_provider"] = provider
                persona["_variation_index"] = start_index + idx
                _ensure_persona_type(lob, persona, base_description)
                _ensure_unique_email(persona, lob, extra=start_index + idx)

        return parsed[:count]

    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned non-JSON: {exc}. Raw response starts: {raw[:500]}") from exc
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc


def generate_persona_variations(lob: str, base_description: str, count: int) -> str:
    """
    Generate `count` distinct persona variations for the given LOB, all inspired
    by `base_description`.

    Returns a JSON string: an array of persona dicts, or a dict with "error".
    """
    lob = lob.lower().strip()
    if lob not in _LOB_PROMPTS:
        return json.dumps({"error": f"Unknown LOB '{lob}'. Valid: {_VALID_LOBS}"})

    count = max(1, min(count, 100))  # hard-clamp

    all_vehicles: list = []
    if lob == "auto":
        requested_vehicle = _find_vehicle_from_description(base_description)
        if requested_vehicle:
            all_vehicles = [requested_vehicle for _ in range(count)]
        else:
            all_vehicles = _sample_vehicles(count)

    if _detect_provider() == "ollama":
        results: list[dict] = [None] * count  # type: ignore[list-item]

        def _run_variation(index: int) -> tuple[int, dict]:
            variation_description, note = _variation_text(lob, base_description, index)
            vehicle = all_vehicles[index] if index < len(all_vehicles) else None
            user_message = f"Generate test data for this {lob.upper()} persona: {variation_description}"
            if lob == "auto" and vehicle:
                user_message += _vehicle_constraint_text(vehicle)

            try:
                raw = _generate_persona_with_ollama(
                    lob,
                    _LOB_PROMPTS[lob],
                    user_message,
                    variation_description,
                )
                persona = json.loads(raw)
            except json.JSONDecodeError:
                persona = {"error": "Non-JSON persona variation", "raw": raw}
            except Exception as exc:
                persona = {"error": str(exc)}

            if isinstance(persona, dict):
                persona["_variation_index"] = index
                persona["_note"] = note
            return index, persona

        with ThreadPoolExecutor(max_workers=min(count, _VARIATION_CHUNK_SIZE)) as pool:
            futures = [pool.submit(_run_variation, index) for index in range(count)]
            for future in as_completed(futures):
                index, persona = future.result()
                results[index] = persona

        return json.dumps(results, indent=2)

    try:
        chunks = []
        for start in range(0, count, _VARIATION_CHUNK_SIZE):
            chunk_count = min(_VARIATION_CHUNK_SIZE, count - start)
            chunk_vehicles = all_vehicles[start:start + chunk_count] if all_vehicles else None
            chunks.append((start, chunk_count, chunk_vehicles))

        chunk_results: dict[int, list] = {}

        def _run_chunk(start, chunk_count, chunk_vehicles):
            try:
                return start, _generate_persona_variation_chunk(
                    lob=lob,
                    base_description=base_description,
                    count=chunk_count,
                    start_index=start,
                    vehicles=chunk_vehicles,
                )
            except ValueError:
                if chunk_count == 1:
                    raise
                chunk = []
                for offset in range(chunk_count):
                    single_vehicles = [chunk_vehicles[offset]] if chunk_vehicles else None
                    chunk.extend(_generate_persona_variation_chunk(
                        lob=lob,
                        base_description=base_description,
                        count=1,
                        start_index=start + offset,
                        vehicles=single_vehicles,
                    ))
                return start, chunk

        max_workers = min(len(chunks), 10)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_run_chunk, *args): args[0] for args in chunks}
            for future in as_completed(futures):
                start_idx, chunk = future.result()
                chunk_results[start_idx] = chunk

        results = []
        for start, chunk_count, _ in chunks:
            results.extend(chunk_results[start])

        return json.dumps(results[:count], indent=2)

    except Exception as exc:
        return json.dumps({"error": str(exc)})


def _generate_one_persona(args: tuple) -> dict:
    """Worker for parallel batch generation. Returns a persona dict."""
    i, scenario = args
    lob = str(scenario.get("lob", "")).lower().strip()
    description = str(scenario.get("description", "")).strip()

    if not lob or not description:
        return {"error": f"Scenario {i}: missing 'lob' or 'description'", "_scenario_index": i}

    raw = generate_persona(lob, description)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"error": f"Non-JSON response for scenario {i}", "raw": raw}

    parsed["_scenario_index"] = i
    return parsed


_BATCH_MAX_WORKERS = 10  # concurrent AI API calls; tune down if rate-limited


def generate_batch_personas(scenarios: list) -> str:
    """
    Generate multiple persona JSON objects without executing browser flows.

    Each item in `scenarios` must be a dict with "lob" and "description" keys.
    Returns a JSON array where each element is the persona object (or an error
    object) for that scenario, with an added "_scenario_index" field.

    AI calls are issued concurrently (up to _BATCH_MAX_WORKERS threads) so
    large persona batches finish faster than serial generation.
    Results are sorted by _scenario_index so the output order matches the input.
    """
    if not scenarios:
        return json.dumps([], indent=2)

    workers = min(_BATCH_MAX_WORKERS, len(scenarios))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_generate_one_persona, (i, s)): i
                   for i, s in enumerate(scenarios)}
        results = [None] * len(scenarios)
        for future in as_completed(futures):
            result = future.result()
            results[result["_scenario_index"]] = result

    return json.dumps(results, indent=2)
