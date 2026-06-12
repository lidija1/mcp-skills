"""Call the LLM and parse the structured review response."""
import json
import re
from dataclasses import dataclass
from typing import Optional

from .config import ReviewConfig
from .diff_fetcher import PRContext
from .llm_provider import call_llm
from .prompt_builder import SYSTEM_PROMPT, build_user_prompt

_SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


@dataclass
class Finding:
    file: str
    line: int
    severity: str
    category: str
    message: str
    suggestion: str


@dataclass
class ReviewResult:
    summary: str
    health_score: int
    findings: list[Finding]

    def filtered(self, min_severity: str) -> list[Finding]:
        cutoff = _SEVERITY_ORDER.get(min_severity, 1)
        return [f for f in self.findings if _SEVERITY_ORDER.get(f.severity, 99) <= cutoff]


def _extract_json(text: str) -> dict:
    """Strip markdown fences if the model wrapped the JSON anyway."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def run_review(pr: PRContext, config: ReviewConfig) -> ReviewResult:
    user_prompt = build_user_prompt(pr, config)
    raw = call_llm(SYSTEM_PROMPT, user_prompt, config)

    try:
        data = _extract_json(raw)
    except json.JSONDecodeError as e:
        print(f"[ai-review] WARNING: LLM returned non-JSON. Raw output:\n{raw[:500]}")
        return ReviewResult(
            summary="Review could not be parsed — LLM returned non-JSON output.",
            health_score=0,
            findings=[],
        )

    findings = [
        Finding(
            file=f.get("file", ""),
            line=int(f.get("line", 0)),
            severity=f.get("severity", "info"),
            category=f.get("category", "style"),
            message=f.get("message", ""),
            suggestion=f.get("suggestion", ""),
        )
        for f in data.get("findings", [])
    ]

    return ReviewResult(
        summary=data.get("summary", ""),
        health_score=int(data.get("health_score", 0)),
        findings=findings,
    )
