"""
Regression sweep: AI generates variant list → parallel replay runs →
rule assertions (direction + magnitude + ladder) → AI pattern analysis.

Phase 1: AI generates RegressionVariant list from baseline description.
Phase 2: Baseline snapshot captured.
Phase 3: All variants run in parallel via ThreadPoolExecutor.
Phase 4: AI reads the full result table, identifies patterns, suggests follow-ups.

Entry point: run_sweep(baseline_description, lob, focus) → SweepResult
"""
from __future__ import annotations

import json
import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from api_tests.oneshield_api_replay import OneShieldApiReplay
from dashboard.backend.api_assertions.snapshot import (
    snapshot_store,
    _extract_premium,
    _extract_uw_conditions,
)
from mcp_tools.policy_flow_generator.persona_generator import generate_persona, _detect_provider


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class RegressionVariant:
    label: str
    persona_description: str
    field_mutated: str
    category: str           # risk_adding | discount | hard_stop | ladder
    expected_direction: str # gt | lt | blocked
    min_delta_pct: float | None = None
    max_delta_pct: float | None = None


@dataclass
class VariantResult:
    variant: RegressionVariant
    run_id: str
    persona: dict[str, Any]
    actual_premium: float | None
    delta_pct: float | None
    uw_conditions: list[str]
    blocked: bool
    blocked_reason: str
    direction_passed: bool
    magnitude_passed: bool | None  # None = no magnitude assertion defined
    passed: bool
    message: str
    error: str = ""


@dataclass
class SweepAnalysis:
    patterns: list[str]
    root_causes: list[str]
    follow_up_variants: list[RegressionVariant]


@dataclass
class SweepResult:
    sweep_id: str
    baseline_description: str
    baseline_premium: float | None
    baseline_run_id: str
    baseline_persona: dict[str, Any]
    variants: list[RegressionVariant]
    results: list[VariantResult]
    analysis: SweepAnalysis | None = None

    @property
    def passed(self) -> bool:
        return bool(self.results) and all(r.passed for r in self.results)

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)


# ---------------------------------------------------------------------------
# Shared AI caller (Anthropic / OpenAI / Ollama)
# ---------------------------------------------------------------------------

def _call_ai(system_prompt: str, user_message: str, max_tokens: int = 2048) -> str:
    provider = _detect_provider()

    if provider == "anthropic":
        import anthropic as _anthropic
        client = _anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        msg = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return msg.content[0].text.strip()

    if provider == "openai":
        import openai as _openai
        client = _openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return resp.choices[0].message.content.strip()

    if provider == "deepseek":
        import openai as _openai
        client = _openai.OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        )
        resp = client.chat.completions.create(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
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
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "options": {"temperature": 0, "num_predict": max_tokens},
        }).encode()
        req = urllib.request.Request(
            f"{base}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = json.loads(resp.read().decode())
        return (body.get("message") or {}).get("content", "").strip()

    raise RuntimeError(
        "No AI provider configured. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or DEEPSEEK_API_KEY in .env"
    )


def _strip_json(raw: str) -> str:
    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned).strip()
    return re.sub(r"\s*```$", "", cleaned).strip()


# ---------------------------------------------------------------------------
# Phase 1 — AI variant generation
# ---------------------------------------------------------------------------

_VARIANT_SYSTEM_PROMPT = """\
You are an insurance QA engineer generating regression test variants for a premium sweep.

Given a baseline auto insurance persona, generate a list of variant test cases.
Each variant changes exactly ONE risk factor from the baseline.

Return ONLY a JSON array. Each element must have exactly these keys:
{
  "label": "short human-readable name (e.g. 'coverage Bronze' or 'SR-22 required')",
  "persona_description": "full NL baseline description WITH the mutation applied",
  "field_mutated": "the OneShield persona JSON field being changed (e.g. 'PolicyCoverage' or 'LicenseStatus')",
  "category": "risk_adding | discount | hard_stop | ladder",
  "expected_direction": "gt | lt | blocked",
  "min_delta_pct": <number or null>,
  "max_delta_pct": <number or null>
}

Rules:
- persona_description must include all baseline details plus the single mutation
- category "ladder" = sequential series of the same factor stepped up (e.g. Bronze → Silver → Gold → Platinum)
- expected_direction "blocked" = flow declined entirely (no premium expected)
- min_delta_pct: minimum absolute % change from baseline (null if not applicable)
- max_delta_pct: sanity cap to catch runaway surcharges (null if uncapped)

Unless focus is specified, cover ALL four categories:
  RISK ADDING:  young driver (DOB ~20 years ago),
                elderly driver (DOB ~75 years ago), business vehicle use (VehicleUse=Business),
                SR-22 required (SR22=Yes), leased vehicle (Ownership=Leased)
  DISCOUNTS:    good student (FullTimeStudent=Yes + GoodStudent=Yes, driver under 25),
                defensive driver course (DefensiveDriver=Yes),
                low mileage commuter (VehicleUse=Commute + DistanceToWork=5),
                minimum coverage (PolicyCoverage=Bronze)
  HARD STOPS:   suspended license (LicenseStatus=Suspended), revoked license (LicenseStatus=Revoked)
  LADDER:       coverage tier — generate exactly 4 variants in order:
                  Bronze (PolicyCoverage=Bronze, expected lt baseline),
                  Silver (PolicyCoverage=Silver, expected lt baseline if baseline is Gold/Platinum),
                  Gold (PolicyCoverage=Gold),
                  Platinum (PolicyCoverage=Platinum, expected gt baseline)
                Each step must have expected_direction relative to the BASELINE (not prior step).
                Use min_delta_pct=2 between each tier as a sanity floor.
"""


def _generate_variants(baseline_description: str, lob: str, focus: str | None) -> list[RegressionVariant]:
    focus_line = f"\nFocus only on this category: {focus}" if focus else ""
    user_msg = f"Baseline persona: {baseline_description}{focus_line}\nLOB: {lob}\n\nGenerate the variant list."
    raw = _call_ai(_VARIANT_SYSTEM_PROMPT, user_msg, max_tokens=3000)
    cleaned = _strip_json(raw)
    start, end = cleaned.find("["), cleaned.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"AI did not return a JSON array. Response: {raw[:300]}")
    items = json.loads(cleaned[start:end + 1])
    variants = []
    for item in items:
        variants.append(RegressionVariant(
            label=item["label"],
            persona_description=item["persona_description"],
            field_mutated=item.get("field_mutated", ""),
            category=item.get("category", "risk_adding"),
            expected_direction=item["expected_direction"],
            min_delta_pct=item.get("min_delta_pct"),
            max_delta_pct=item.get("max_delta_pct"),
        ))
    return variants


# ---------------------------------------------------------------------------
# Phase 2/3 — Replay runner + rule assertions
# ---------------------------------------------------------------------------

def _run_persona(description: str, lob: str) -> tuple[dict, dict]:
    raw = generate_persona(lob, description)
    persona = json.loads(raw)
    if "error" in persona:
        raise ValueError(f"Persona generation failed: {persona['error']}")
    client = OneShieldApiReplay()
    try:
        flow = client.run_captured_auto_flow(persona, stop_after="rating-detail", fast_mode=True)
    finally:
        client.close()
    return persona, flow


def _assert_variant(
    variant: RegressionVariant,
    actual_premium: float | None,
    baseline_premium: float | None,
    blocked: bool,
    uw_conditions: list[str] | None = None,
) -> tuple[bool, bool | None, float | None, str]:
    """Returns (direction_passed, magnitude_passed, delta_pct, message)."""
    messages: list[str] = []
    direction = variant.expected_direction

    if direction == "blocked":
        # UW Referral page counts as blocked — OneShield still computes a premium
        # even for hard-stop profiles, so blocked_reason alone is insufficient.
        direction_passed = blocked or bool(uw_conditions)
        if not direction_passed:
            p = f"${actual_premium:,.2f}" if actual_premium else "no premium"
            messages.append(f"expected blocked but got {p}")
    elif baseline_premium is None or actual_premium is None:
        direction_passed = False
        messages.append("premium not available for comparison")
    elif direction == "gt":
        direction_passed = actual_premium > baseline_premium
        if not direction_passed:
            messages.append(f"${actual_premium:,.2f} not > baseline ${baseline_premium:,.2f}")
    elif direction == "lt":
        direction_passed = actual_premium < baseline_premium
        if not direction_passed:
            messages.append(f"${actual_premium:,.2f} not < baseline ${baseline_premium:,.2f}")
    else:
        direction_passed = False
        messages.append(f"unknown direction '{direction}'")

    delta_pct: float | None = None
    if baseline_premium and actual_premium:
        delta_pct = ((actual_premium - baseline_premium) / baseline_premium) * 100

    magnitude_passed: bool | None = None
    if variant.min_delta_pct is not None or variant.max_delta_pct is not None:
        if delta_pct is None:
            magnitude_passed = False
            messages.append("delta not computable")
        else:
            abs_delta = abs(delta_pct)
            magnitude_passed = True
            if variant.min_delta_pct is not None and abs_delta < variant.min_delta_pct:
                magnitude_passed = False
                messages.append(f"delta {abs_delta:.1f}% below min {variant.min_delta_pct}%")
            if variant.max_delta_pct is not None and abs_delta > variant.max_delta_pct:
                magnitude_passed = False
                messages.append(f"delta {abs_delta:.1f}% above max {variant.max_delta_pct}%")

    return direction_passed, magnitude_passed, delta_pct, "; ".join(messages)


def _run_variant_task(
    variant: RegressionVariant,
    lob: str,
    baseline_premium: float | None,
    baseline_persona: dict[str, Any] | None = None,
) -> VariantResult:
    try:
        persona, flow = _run_persona(variant.persona_description, lob)
    except Exception as exc:
        return VariantResult(
            variant=variant, run_id="", persona={},
            actual_premium=None, delta_pct=None, uw_conditions=[],
            blocked=False, blocked_reason="",
            direction_passed=False, magnitude_passed=None,
            passed=False, message="", error=str(exc)[:200],
        )

    run_id = snapshot_store.save(persona, flow, lob=lob, persona_desc=variant.label)
    actual_premium = _extract_premium(flow)
    uw_conditions = _extract_uw_conditions(flow)
    blocked = bool(flow.get("blocked_reason"))
    blocked_reason = flow.get("blocked_reason", "")

    # Skip direction/magnitude comparison when the variant mutates a field that
    # already has the same value in the baseline persona — comparing a persona
    # against itself always produces delta=0 and will trivially fail gt/lt checks.
    field = variant.field_mutated
    if (
        baseline_persona
        and field
        and field in persona
        and field in baseline_persona
        and str(persona[field]).strip().lower() == str(baseline_persona[field]).strip().lower()
    ):
        delta_pct: float | None = None
        if baseline_premium and actual_premium:
            delta_pct = ((actual_premium - baseline_premium) / baseline_premium) * 100
        return VariantResult(
            variant=variant,
            run_id=run_id,
            persona=persona,
            actual_premium=actual_premium,
            delta_pct=delta_pct,
            uw_conditions=uw_conditions,
            blocked=blocked,
            blocked_reason=blocked_reason,
            direction_passed=True,
            magnitude_passed=None,
            passed=True,
            message=f"skipped — {field}={persona[field]!r} matches baseline (same value)",
        )

    direction_passed, magnitude_passed, delta_pct, message = _assert_variant(
        variant, actual_premium, baseline_premium, blocked, uw_conditions
    )
    passed = direction_passed and (magnitude_passed is None or magnitude_passed)

    return VariantResult(
        variant=variant,
        run_id=run_id,
        persona=persona,
        actual_premium=actual_premium,
        delta_pct=delta_pct,
        uw_conditions=uw_conditions,
        blocked=blocked,
        blocked_reason=blocked_reason,
        direction_passed=direction_passed,
        magnitude_passed=magnitude_passed,
        passed=passed,
        message=message,
    )


_COVERAGE_RANK = {"bronze": 0, "silver": 1, "gold": 2, "platinum": 3}


def _check_ladder_monotonic(results: list[VariantResult]) -> list[str]:
    """Checks that ladder-category variants are monotonically increasing in premium."""
    ladder = [r for r in results if r.variant.category == "ladder" and r.actual_premium is not None]
    # Sort by coverage tier if this is a coverage ladder; otherwise preserve result order
    def _sort_key(r: VariantResult) -> int:
        label_lower = r.variant.label.lower()
        for tier, rank in _COVERAGE_RANK.items():
            if tier in label_lower:
                return rank
        return 999
    if any(_sort_key(r) < 999 for r in ladder):
        ladder = sorted(ladder, key=_sort_key)
    violations = []
    for i in range(len(ladder) - 1):
        lo, hi = ladder[i], ladder[i + 1]
        if (lo.actual_premium or 0) > (hi.actual_premium or 0):
            violations.append(
                f"{lo.variant.label} (${lo.actual_premium:,.2f}) > "
                f"{hi.variant.label} (${hi.actual_premium:,.2f}) — expected non-decreasing"
            )
    return violations


# ---------------------------------------------------------------------------
# Phase 4 — AI post-sweep analysis
# ---------------------------------------------------------------------------

_ANALYSIS_SYSTEM_PROMPT = """\
You are a QA analyst reviewing an auto insurance premium regression sweep.

Analyze the full results table and identify cross-row patterns that rule-based
assertions cannot detect — e.g. suspiciously flat surcharges, inverted ladders,
discounts that don't apply, hard stops that let through.

Return ONLY a JSON object with exactly these keys:
{
  "patterns": ["pattern finding 1", "pattern finding 2"],
  "root_causes": ["likely root cause 1", "likely root cause 2"],
  "follow_up_variants": [
    {
      "label": "...",
      "persona_description": "...",
      "field_mutated": "...",
      "category": "risk_adding | discount | hard_stop | ladder",
      "expected_direction": "gt | lt | blocked",
      "min_delta_pct": <number or null>,
      "max_delta_pct": <number or null>
    }
  ]
}

Keep each finding to one concise sentence. Only suggest follow-up variants for anomalies
that warrant further probing. If no issues found, return empty arrays for all keys.
"""


def _format_results_for_analysis(sweep: SweepResult) -> str:
    base_str = f"${sweep.baseline_premium:,.2f}" if sweep.baseline_premium else "N/A"
    lines = [
        f"Baseline: {sweep.baseline_description}",
        f"Baseline premium: {base_str}",
        "",
        "| label | category | actual | delta% | dir | mag | pass | message |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in sweep.results:
        if r.error:
            lines.append(f"| {r.variant.label} | {r.variant.category} | ERROR | — | — | — | ❌ | {r.error[:60]} |")
            continue
        actual = f"${r.actual_premium:,.2f}" if r.actual_premium else ("blocked" if r.blocked else "N/A")
        delta = f"{r.delta_pct:+.1f}%" if r.delta_pct is not None else "N/A"
        dir_ok = "✅" if r.direction_passed else "❌"
        mag_ok = "✅" if r.magnitude_passed else ("—" if r.magnitude_passed is None else "❌")
        ok = "✅" if r.passed else "❌"
        msg = r.message[:60] if r.message else ""
        lines.append(f"| {r.variant.label} | {r.variant.category} | {actual} | {delta} | {dir_ok} | {mag_ok} | {ok} | {msg} |")

    ladder_violations = _check_ladder_monotonic(sweep.results)
    if ladder_violations:
        lines += ["", "Ladder violations:"] + [f"  - {v}" for v in ladder_violations]

    return "\n".join(lines)


def _parse_analysis(raw: str) -> SweepAnalysis:
    cleaned = _strip_json(raw)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        return SweepAnalysis(patterns=[raw[:200]], root_causes=[], follow_up_variants=[])
    try:
        data = json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError:
        return SweepAnalysis(patterns=[raw[:200]], root_causes=[], follow_up_variants=[])

    follow_ups = []
    for item in data.get("follow_up_variants", []):
        try:
            follow_ups.append(RegressionVariant(
                label=item["label"],
                persona_description=item["persona_description"],
                field_mutated=item.get("field_mutated", ""),
                category=item.get("category", "risk_adding"),
                expected_direction=item["expected_direction"],
                min_delta_pct=item.get("min_delta_pct"),
                max_delta_pct=item.get("max_delta_pct"),
            ))
        except KeyError:
            pass

    return SweepAnalysis(
        patterns=data.get("patterns", []),
        root_causes=data.get("root_causes", []),
        follow_up_variants=follow_ups,
    )


def analyze_sweep(sweep: SweepResult) -> SweepAnalysis:
    table = _format_results_for_analysis(sweep)
    raw = _call_ai(_ANALYSIS_SYSTEM_PROMPT, table, max_tokens=2048)
    return _parse_analysis(raw)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_sweep(
    baseline_description: str,
    lob: str = "auto",
    focus: str | None = None,
) -> SweepResult:
    """
    Full regression sweep — four phases:
      1. AI generates variant list from baseline_description
      2. Baseline snapshot captured
      3. All variants run in parallel (max 6 workers)
      4. AI reads full result table → pattern analysis + follow-up suggestions

    Args:
        baseline_description: NL description of the clean baseline persona.
        lob:                  Line of business (default "auto").
        focus:                Optional category filter: "risk_adding", "discount",
                              "hard_stop", "ladder", or None for all.

    Returns:
        SweepResult with per-variant assertions and AI analysis.
    """
    sweep_id = str(uuid.uuid4())[:8]

    # Phase 1 + 2: Generate variants and run baseline concurrently
    with ThreadPoolExecutor(max_workers=2) as bootstrap:
        variant_future = bootstrap.submit(_generate_variants, baseline_description, lob, focus)
        baseline_future = bootstrap.submit(_run_persona, baseline_description, lob)
        variants = variant_future.result()
        baseline_persona, baseline_flow = baseline_future.result()

    baseline_premium = _extract_premium(baseline_flow)
    baseline_run_id = snapshot_store.save(
        baseline_persona, baseline_flow, lob=lob,
        persona_desc=f"[baseline] {baseline_description}",
    )

    # Phase 3: Parallel variants — all fire at once (pure I/O, no CPU contention)
    results: list[VariantResult] = [None] * len(variants)  # type: ignore[list-item]
    with ThreadPoolExecutor(max_workers=len(variants)) as pool:
        futures = {
            pool.submit(_run_variant_task, v, lob, baseline_premium, baseline_persona): i
            for i, v in enumerate(variants)
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                results[idx] = VariantResult(
                    variant=variants[idx], run_id="", persona={},
                    actual_premium=None, delta_pct=None, uw_conditions=[],
                    blocked=False, blocked_reason="",
                    direction_passed=False, magnitude_passed=None,
                    passed=False, message="", error=str(exc)[:200],
                )

    sweep = SweepResult(
        sweep_id=sweep_id,
        baseline_description=baseline_description,
        baseline_premium=baseline_premium,
        baseline_run_id=baseline_run_id,
        baseline_persona=baseline_persona,
        variants=variants,
        results=results,
    )

    # Phase 4: AI pattern analysis
    sweep.analysis = analyze_sweep(sweep)

    return sweep
