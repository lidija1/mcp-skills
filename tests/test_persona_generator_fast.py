import json

import mcp_tools.policy_flow_generator.persona_generator as persona_generator


def _model_persona(monkeypatch, lob: str, description: str, payload: dict) -> dict:
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "oneshield-persona-json")
    monkeypatch.setattr(persona_generator, "_ollama_chat", lambda *args, **kwargs: json.dumps(payload))
    return json.loads(persona_generator.generate_persona(lob, description))


def test_auto_model_output_is_validated_and_normalized(monkeypatch):
    persona = _model_persona(
        monkeypatch,
        "auto",
        "22-year-old driver with SR-22, revoked license, leased BMW, Platinum coverage",
        {
            "TC_ID": "AI_123456",
            "CustomerType": "Individual",
            "FirstName": "Jordan",
            "LastName": "Parker",
            "DOB": "04/15/2004",
            "PhoneNum": "413-555-1834",
            "Email": "jordan_{timestamp}@uwtest.com",
            "Address": "225 Maple Street",
            "ZIP": "01101",
            "State": "Massachusetts",
            "City": "Springfield",
            "Producer": "Janis Irey",
            "EffectiveDate": "05/29/2026",
            "Program": "Personal Auto",
            "BillingMethod": "Direct Billed",
            "FalseInfo": "No",
            "DamageInfo": "No",
            "Gender": "Male",
            "MaritalStatus": "Single",
            "DriverStatus": "Active (rated)",
            "EmploymentCategory": "Student",
            "SR2022": "Yes",
            "SR22FilingState": "Massachusetts",
            "Occupation": "Day Care",
            "LicenseStatus": "Revoked",
            "VehicleType": "Private Passenger Auto",
            "Year": "2019",
            "Make": "BMW",
            "Model": "X6 50I AWD",
            "Spec": "Utility Vehicle - Four-Wheel Drive 4-Door | 4WD | 4.4 Ltrs | 4x4",
            "VehicleUse": "Pleasure",
            "Ownership": "Leased",
            "LossPayeeType": "Leased",
            "LossPayeeName": "BMW Financial Services",
            "PolicyCoverage": "Platinum",
            "PaymentPlan": "Pay In Full",
        },
    )

    assert persona["_provider"] == "ollama"
    assert persona["_persona_type"] == "triple_risk"
    assert persona["SR22"] == "Yes"
    assert "SR2022" not in persona
    assert persona["Ownership"] == "Leased"
    assert persona["PolicyCoverage"] == "Platinum"


def test_homeowner_model_output_is_validated(monkeypatch):
    persona = _model_persona(
        monkeypatch,
        "homeowner",
        "coastal property with prior losses and renovation",
        {
            "TC_ID": "AI_654321",
            "CustomerType": "Individual",
            "FirstName": "Morgan",
            "LastName": "Rivera",
            "DOB": "06/12/1984",
            "PhoneNum": "413-555-2841",
            "Email": "morgan_{timestamp}@hometest.com",
            "Address": "714 Shoreline Avenue",
            "ZIP": "01101",
            "State": "Massachusetts",
            "City": "Springfield",
            "Producer": "Janis Irey",
            "Program": "Homeowner",
            "EffectiveDate": "05/29/2026",
            "BillingMethod": "Direct Billed",
            "ProgramType": "Basic",
            "DayCare": "No",
            "UndergroundOil": "No",
            "ResidenceRented": "No",
            "ResidenceVacant": "No",
            "Animals": "No",
            "PolicyCoverageOption": "Platinum",
            "ResidenceType": "Homeowner",
            "ReplacementCost": "1,200,000",
            "Contents": "720,000",
            "AllPerilsDeductable": "10,000",
            "WindstormDeductable": "5%",
            "Liability": "500,000",
            "MedPayments": "5,000",
            "Renovation": "Yes",
            "LivedHere": "No",
            "YearBuilt": "2018",
            "ConstructionType": "Masonry",
            "RoofType": "Concrete Tile",
            "Loses": "Yes",
            "ExistingClient": "No",
            "Refused": "No",
            "Declined": "No",
            "PaymentPlan": "Pay In Full",
        },
    )

    assert persona["_provider"] == "ollama"
    assert persona["Program"] == "Homeowner"
    assert persona["WindstormDeductable"] == "5%"
    assert persona["Loses"] == "Yes"
    assert persona["Renovation"] == "Yes"


def test_invalid_model_output_returns_validation_error_without_fallback(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setattr(
        persona_generator,
        "_ollama_chat",
        lambda *args, **kwargs: json.dumps({"Program": "Personal Auto", "SR2022": "Yes"}),
    )

    result = json.loads(persona_generator.generate_persona("auto", "SR-22 driver"))

    assert result["error"] == "Persona validation failed"
    assert result["lob"] == "auto"
    assert result["validation_errors"]
    assert result.get("_provider") != "local-fast"


def test_model_failure_returns_error_without_fallback(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")

    def fail_model(*args, **kwargs):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(persona_generator, "_ollama_chat", fail_model)

    result = json.loads(persona_generator.generate_persona("auto", "leased BMW with Platinum coverage"))

    assert result == {"error": "model unavailable"}


def test_batch_personas_do_not_fall_back_when_model_fails(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")

    def fail_model(*args, **kwargs):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(persona_generator, "_ollama_chat", fail_model)

    personas = json.loads(persona_generator.generate_batch_personas([
        {"lob": "auto", "description": "leased BMW with Platinum coverage"},
        {"lob": "homeowner", "description": "coastal property with prior losses"},
    ]))

    assert [p["_scenario_index"] for p in personas] == [0, 1]
    assert [p["error"] for p in personas] == ["model unavailable", "model unavailable"]
    assert all(p.get("_provider") != "local-fast" for p in personas)
