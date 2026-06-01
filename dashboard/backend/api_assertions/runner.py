"""Plain-English Auto UW assertion runner."""

from __future__ import annotations

import json

from api_tests.oneshield_api_replay import OneShieldApiReplay
from dashboard.backend.api_assertions.assertion_engine import evaluate_assertions
from dashboard.backend.api_assertions.parser import parse_plain_english_api_assertion
from dashboard.backend.api_assertions.schemas import ApiAssertionRunResult
from mcp_tools.policy_flow_generator.persona_generator import generate_persona


def run_plain_english_api_assertion(
    prompt: str,
    pre_generated_persona: dict | None = None,
) -> ApiAssertionRunResult:
    spec = parse_plain_english_api_assertion(prompt)
    if pre_generated_persona is not None:
        persona = pre_generated_persona
    else:
        persona_raw = generate_persona(spec.lob, spec.persona_prompt)
        persona = json.loads(persona_raw)
        if "error" in persona:
            raise ValueError(persona.get("error") or "Persona generation failed.")

    client = OneShieldApiReplay()
    try:
        if spec.lob == "auto":
            flow_result = client.run_captured_auto_flow(
                persona,
                stop_after=spec.stage,
                fast_mode=spec.stage == "rate",
            )
        else:
            raise NotImplementedError(f"UW replay runner not implemented for LOB: {spec.lob!r}")
    finally:
        client.close()

    findings = evaluate_assertions(spec.assertions, persona, flow_result, lob=spec.lob)
    return ApiAssertionRunResult(
        spec=spec,
        persona=persona,
        flow_result=flow_result,
        findings=findings,
        passed=bool(findings) and all(finding.passed for finding in findings),
    )
