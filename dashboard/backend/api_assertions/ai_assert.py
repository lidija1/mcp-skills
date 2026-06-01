"""
AI-decided assertion engine.

Runs replay for a persona, then feeds the extracted results to the
configured AI provider (Anthropic / OpenAI / Ollama). The model suggests
a list of meaningful plain-English assertions; those are then parsed and
evaluated by the existing assertion engine.

This avoids hard-coding expected values — the AI infers sensible ranges
and rule checks from the persona's risk profile.

Usage:
    from dashboard.backend.api_assertions.ai_assert import run_ai_assert
    result = run_ai_assert("Young SR-22 driver with Gold coverage")
"""

from __future__ import annotations

import json
import os
import re

from api_tests.oneshield_api_replay import OneShieldApiReplay
from dashboard.backend.api_assertions.assertion_engine import evaluate_assertions
from dashboard.backend.api_assertions.parser import parse_plain_english_api_assertion
from dashboard.backend.api_assertions.schemas import ApiAssertionRunResult, ApiAssertionSpec, ApiAssertion
from dashboard.backend.api_assertions.snapshot import snapshot_store, _extract_premium, _extract_uw_conditions
from mcp_tools.policy_flow_generator.persona_generator import generate_persona, _detect_provider

_SYSTEM_PROMPT = """\
You are an insurance test automation advisor. Given a persona profile and the
actual UW test results for that persona, suggest 3–6 meaningful, verifiable
assertions that a QA engineer should check.

Return ONLY a JSON array of plain-English assertion strings — no explanation,
no markdown, no extra text. Each string must be in one of these forms:
  "assert premium is less than 2000"
  "assert premium is greater than 500"
  "assert premium is between 800 and 2500"
  "assert UW condition contains 'All drivers under 25 years of age'"
  "assert flow is not blocked"
  "assert UW condition contains 'SR-22'"
  "assert coverage equals Gold"

Base your suggestions ONLY on the actual values provided — do not invent values
you cannot verify from the input data.
"""


def _build_context(persona: dict, premium: float | None, uw_conditions: list[str], blocked: bool) -> str:
    lines = ["=== PERSONA ==="]
    important_fields = [
        "PolicyCoverage", "SR22", "LicenseStatus", "EmploymentCategory",
        "VehicleUse", "Ownership", "DamageInfo",
    ]
    dob = persona.get("DOB", "")
    if dob:
        lines.append(f"DOB: {dob}")
    for key in important_fields:
        val = persona.get(key)
        if val:
            lines.append(f"{key}: {val}")

    lines.append("\n=== UW TEST RESULTS ===")
    if premium is not None:
        lines.append(f"Total premium: ${premium:,.2f}")
        # Compute ±20% bracket for context
        lo = premium * 0.80
        hi = premium * 1.20
        lines.append(f"  (±20% window: ${lo:,.2f} – ${hi:,.2f})")
    else:
        lines.append("Total premium: not available")

    if uw_conditions:
        lines.append(f"UW conditions fired: {len(uw_conditions)}")
        for cond in uw_conditions[:3]:
            lines.append(f"  - {cond[:120]}")
    else:
        lines.append("UW conditions fired: none")

    lines.append(f"Flow blocked: {blocked}")
    return "\n".join(lines)


def _call_ai(context: str) -> str:
    provider = _detect_provider()
    user_message = (
        f"Here is the persona and UW test results. Suggest 3–6 assertions:\n\n{context}"
    )

    if provider == "anthropic":
        import anthropic as _anthropic
        client = _anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        msg = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        return msg.content[0].text.strip()

    if provider == "openai":
        import openai as _openai
        client = _openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=512,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        return resp.choices[0].message.content.strip()

    if provider == "ollama":
        import urllib.request
        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
        payload = json.dumps({
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "options": {"temperature": 0, "num_predict": 512},
            "format": "json",
        }).encode()
        req = urllib.request.Request(
            f"{base}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode())
        return (body.get("message") or {}).get("content", "").strip()

    raise RuntimeError("No AI provider configured.")


def _parse_ai_suggestions(raw: str) -> list[str]:
    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned).strip()
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1:
        try:
            items = json.loads(cleaned[start:end + 1])
            return [str(item).strip() for item in items if item]
        except json.JSONDecodeError:
            pass
    lines = [line.strip().lstrip("-•* ") for line in cleaned.splitlines() if line.strip()]
    return [line for line in lines if line.startswith("assert") or "premium" in line.lower()]


def run_ai_assert(
    persona_description: str,
    lob: str = "auto",
    pre_generated_persona: dict | None = None,
) -> dict:
    """
    Run replay for a persona, ask AI to decide assertions, evaluate them.

    Args:
        persona_description: NL description of the persona.
        lob:                 Line of business (default "auto").
        pre_generated_persona: Skip persona generation if already available.

    Returns:
        Dict with keys: run_id, persona, premium, uw_conditions, blocked,
        ai_suggestions (list[str]), findings (list of finding dicts), passed.
    """
    if pre_generated_persona is not None:
        persona = pre_generated_persona
    else:
        raw = generate_persona(lob, persona_description)
        persona = json.loads(raw)
        if "error" in persona:
            raise ValueError(persona["error"])

    client = OneShieldApiReplay()
    try:
        flow_result = client.run_captured_auto_flow(
            persona,
            stop_after="rating-detail",
            fast_mode=False,
        )
    finally:
        client.close()

    premium = _extract_premium(flow_result)
    uw_conditions = _extract_uw_conditions(flow_result)
    blocked = bool(flow_result.get("blocked_reason"))

    run_id = snapshot_store.save(
        persona, flow_result, lob=lob, persona_desc=persona_description
    )

    context = _build_context(persona, premium, uw_conditions, blocked)
    raw_ai = _call_ai(context)
    suggestions = _parse_ai_suggestions(raw_ai)

    # Parse and evaluate each suggestion as a plain-English assertion
    findings_out = []
    for suggestion in suggestions:
        try:
            spec = parse_plain_english_api_assertion(suggestion, lob=lob)
            evaluated = evaluate_assertions(spec.assertions, persona, flow_result, lob=lob)
            for finding in evaluated:
                findings_out.append({
                    "suggestion": suggestion,
                    "type": finding.type,
                    "operator": finding.operator,
                    "expected": finding.expected,
                    "actual": finding.actual,
                    "passed": finding.passed,
                    "message": finding.message,
                })
        except Exception as exc:
            findings_out.append({
                "suggestion": suggestion,
                "type": "parse_error",
                "passed": False,
                "message": str(exc)[:200],
            })

    passed = bool(findings_out) and all(f["passed"] for f in findings_out)

    return {
        "run_id": run_id,
        "persona_description": persona_description,
        "persona": persona,
        "premium": premium,
        "uw_conditions": uw_conditions,
        "blocked": blocked,
        "ai_suggestions": suggestions,
        "findings": findings_out,
        "passed": passed,
    }
