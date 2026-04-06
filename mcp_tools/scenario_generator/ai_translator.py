"""
AI Translator: Natural Language → Personal Auto test data JSON.

Uses the Anthropic API (Claude) to translate a plain-English scenario
description into the exact JSON structure consumed by the Playwright test
framework (AutoData.json / AutoUWRulesData.json schema).
"""

import json
import os
import re
from datetime import date, timedelta
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# ---------------------------------------------------------------------------
# Date calculations baked into the system prompt at import time
# ---------------------------------------------------------------------------

_TODAY = date.today()
_EFF_DATE = _TODAY + timedelta(days=1)
# DOB threshold: must be born AFTER this date to be "under 25" on eff date
_UNDER_25_CUTOFF = _EFF_DATE - timedelta(days=25 * 365 + 6)

_SYSTEM_PROMPT = f"""
You are a test data generator for a Personal Auto insurance policy automation framework.

Your job: translate a natural-language scenario description into a single valid JSON object
that matches the schema below. Today is {_TODAY.strftime('%Y-%m-%d')}.

════════════════════════════════════════════════════════
FIELD SCHEMA — use ONLY the values listed (case-sensitive)
════════════════════════════════════════════════════════

{{
  "TC_ID":              "AI_XXXXXX",           // replace X's with a 6-digit random number
  "CustomerType":       "Individual",           // always "Individual"
  "FirstName":          string,                 // realistic first name
  "LastName":           string,                 // realistic last name
  "DOB":                "MM/DD/YYYY",           // realistic date of birth; see age rules below
  "PhoneNum":           "413-555-XXXX",         // random 4 digits for XXXX
  "Email":              "firstname_{{timestamp}}@uwtest.com",  // lowercase, literal {{timestamp}}
  "Address":            string,                 // e.g. "123 Maple Street"
  "ZIP":                "01101",                // always this value
  "State":              "Massachusetts",        // always this value
  "City":               "Springfield",          // always this value
  "Producer":           "Janis Irey",           // always this value
  "EffDateOffset":      "1",                    // always "1"
  "Program":            "Personal Auto",        // always this value
  "BillingMethod":      "Direct Billed",        // always this value
  "FalseInfo":          "No",                   // always "No"
  "DamageInfo":         "Yes" | "No",           // "Yes" only for pre-existing vehicle damage
  "DescribeDamage":     string,                 // REQUIRED if DamageInfo="Yes"; OMIT otherwise
  "Gender":             "Male" | "Female",
  "MaritalStatus":      "Single" | "Married" | "Divorced" | "Widowed",
  "DriverStatus":       "Active (rated)",       // always this value
  "EmploymentCategory": "Employed" | "Unemployed" | "Retired" | "Student",
  "SR22":               "Yes" | "No",
  "Occupation":         "Day Care",             // always this value
  "LicenseStatus":      "Active License" | "Suspended" | "Revoked",
  "VehicleType":        "Private Passenger Auto",  // always this value
  "Year":               "2018",                 // always this value
  "Make":               "BMW",                  // always this value
  "Model":              "M3",                   // always this value
  "Spec":               "Convertible 2-Door | 2WD | 4.0 Ltrs | 4x2",  // always this value
  "VehicleUse":         "Pleasure" | "Commute" | "Business",
  "Ownership":          "Owned" | "Leased" | "Financed",
  "LossPayeeType":      "Leased" | "Financed",  // REQUIRED when Ownership != "Owned"; OMIT otherwise
  "LossPayeeName":      string,                 // REQUIRED when Ownership != "Owned"; OMIT otherwise
  "PolicyCoverage":     "Bronze" | "Silver" | "Gold" | "Platinum",
  "PaymentPlan":        "Pay In Full"           // always this value
}}

════════════════════════════════════════════════════════
UW TRIGGER RULES — confirmed soft-referral triggers only
════════════════════════════════════════════════════════

  1. SR22 = "Yes"              → fires "SR-22 / Certificate of Insurance Indicator is checked"
  2. LicenseStatus = "Suspended" or "Revoked"
                               → fires "driver license status that is revoked or suspended"
  3. Driver DOB after {_UNDER_25_CUTOFF.strftime('%m/%d/%Y')}
                               → fires "All drivers under 25 years of age"
     (effective date is {_EFF_DATE.strftime('%m/%d/%Y')}; driver must be < 25 on that date)

  Nothing else triggers a UW referral. Do NOT set FalseInfo="Yes" or treat
  pre-existing damage, age >25, unemployment, or vehicle ownership type as UW triggers.

════════════════════════════════════════════════════════
SCENARIO INTERPRETATION GUIDE
════════════════════════════════════════════════════════

  "high risk driver"          → SR22="Yes", LicenseStatus="Revoked"
  "multiple accidents"        → DamageInfo="Yes", DescribeDamage="Multiple prior accident damage on front and rear bumper"
  "young driver" / "under 25" → DOB between {_UNDER_25_CUTOFF.strftime('%m/%d/%Y')} and today; pick an age 19–24
  "teen driver"               → DOB ~16–18 years ago
  "SR-22"                     → SR22="Yes"
  "suspended licence/license" → LicenseStatus="Suspended"
  "revoked licence/license"   → LicenseStatus="Revoked"
  "leased vehicle"            → Ownership="Leased", LossPayeeType="Leased", LossPayeeName="BMW Financial Services"
  "financed vehicle"          → Ownership="Financed", LossPayeeType="Financed", LossPayeeName="Chase Auto Finance"
  "business use"              → VehicleUse="Business"
  "commute"                   → VehicleUse="Commute"
  "clean record" / "standard" → SR22="No", LicenseStatus="Active License", DamageInfo="No"
  "full coverage"             → PolicyCoverage="Platinum"
  "minimum coverage"          → PolicyCoverage="Bronze"
  "triple risk"               → SR22="Yes", LicenseStatus="Revoked", DOB after {_UNDER_25_CUTOFF.strftime('%m/%d/%Y')}
  "elderly driver"            → DOB ~65–80 years ago (NOT a UW trigger — just realistic DOB)

  Age guidance for DOB field:
    • Specify "middle-aged" → DOB ~35–50 years ago
    • No age hint → default to DOB ~30–40 years ago

════════════════════════════════════════════════════════
RESPONSE FORMAT
════════════════════════════════════════════════════════

Return ONLY a valid JSON object. No explanation, no markdown fences, no extra text.
The JSON must be parseable by Python json.loads().
"""


def translate_scenario(description: str) -> str:
    """
    Translate a plain-English scenario description into an AutoData-schema JSON string.

    Args:
        description: e.g. "High-risk 20-year-old with SR-22 on a leased vehicle."

    Returns:
        JSON string (one test-case object), or JSON with an "error" key on failure.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return json.dumps({"error": "ANTHROPIC_API_KEY not set in environment / .env"})

    client = anthropic.Anthropic(api_key=api_key)

    try:
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Generate test data for this scenario: {description}",
                }
            ],
        )
        raw = message.content[0].text.strip()

        # Strip markdown code fences if the model wraps its output
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        # Validate parsability before returning
        json.loads(raw)
        return raw

    except anthropic.APIError as exc:
        return json.dumps({"error": f"Anthropic API error: {exc}"})
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"Model returned non-JSON output: {exc}", "raw": raw})
    except Exception as exc:
        return json.dumps({"error": str(exc)})
