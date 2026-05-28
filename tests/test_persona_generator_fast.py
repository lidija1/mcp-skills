import json

import mcp_tools.policy_flow_generator.persona_generator as persona_generator


def _fast_persona(monkeypatch, lob: str, description: str) -> dict:
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("PERSONA_FAST_LOCAL", "1")
    return json.loads(persona_generator.generate_persona(lob, description))


def test_fast_auto_persona_maps_high_risk_keywords(monkeypatch):
    persona = _fast_persona(
        monkeypatch,
        "auto",
        "22-year-old driver with SR-22, revoked license, leased BMW, Platinum coverage",
    )

    assert persona["_provider"] == "local-fast"
    assert persona["_persona_type"] == "triple_risk"
    assert persona["Program"] == "Personal Auto"
    assert persona["SR22"] == "Yes"
    assert persona["LicenseStatus"] == "Revoked"
    assert persona["Ownership"] == "Leased"
    assert persona["PolicyCoverage"] == "Platinum"
    assert persona["LossPayeeType"] == "Leased"


def test_fast_homeowner_persona_has_runnable_required_fields(monkeypatch):
    persona = _fast_persona(
        monkeypatch,
        "homeowner",
        "coastal property with prior losses and renovation",
    )

    assert persona["_provider"] == "local-fast"
    assert persona["Program"] == "Homeowner"
    assert persona["ProgramType"] == "Basic"
    assert persona["WindstormDeductable"] == "5%"
    assert persona["Loses"] == "Yes"
    assert persona["Renovation"] == "Yes"
    assert persona["PaymentPlan"] == "Pay In Full"


def test_fast_cyber_persona_is_supported(monkeypatch):
    persona = _fast_persona(
        monkeypatch,
        "cyber",
        "healthcare company with ransomware and no training",
    )

    assert persona["_provider"] == "local-fast"
    assert persona["Program"] == "Cyber"
    assert persona["NatureOfBusiness"] == "Healthcare"
    assert persona["SituationsLast3Years"] == "Ransomware Attack"
    assert persona["CyberTraining"] == "No"
    assert persona["AggregateLimit"] == "2,000,000"


def test_fast_persona_variations_skip_model_chunks(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("PERSONA_FAST_LOCAL", "1")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("local fast variations should not call model chunk generation")

    monkeypatch.setattr(persona_generator, "_generate_persona_variation_chunk", fail_if_called)

    raw = persona_generator.generate_persona_variations(
        "auto",
        "22-year-old driver with SR-22 and revoked license",
        6,
    )
    personas = json.loads(raw)

    assert len(personas) == 6
    assert [p["_variation_index"] for p in personas] == list(range(6))
    assert {p["_provider"] for p in personas} == {"local-fast"}
    assert len({p["_note"] for p in personas}) == 6
    assert all(p["SR22"] == "Yes" for p in personas)


def test_fast_batch_personas_skip_single_model_path(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("PERSONA_FAST_LOCAL", "1")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("local fast batch should not call generate_persona")

    monkeypatch.setattr(persona_generator, "generate_persona", fail_if_called)

    raw = persona_generator.generate_batch_personas([
        {"lob": "auto", "description": "leased BMW with Platinum coverage"},
        {"lob": "homeowner", "description": "coastal property with prior losses"},
        {"lob": "cyber", "description": "healthcare company with ransomware"},
    ])
    personas = json.loads(raw)

    assert [p["_scenario_index"] for p in personas] == [0, 1, 2]
    assert {p["_provider"] for p in personas} == {"local-fast"}
    assert personas[0]["Ownership"] == "Leased"
    assert personas[1]["Program"] == "Homeowner"
    assert personas[2]["NatureOfBusiness"] == "Healthcare"
