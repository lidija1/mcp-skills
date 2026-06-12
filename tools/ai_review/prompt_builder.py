"""Build system and user prompts for the code review LLM call."""
import json
from .config import ReviewConfig
from .diff_fetcher import PRContext, FileDiff

_FOCUS_DESCRIPTIONS = {
    "bugs": "logic errors, off-by-one errors, null/undefined handling, incorrect conditions, unreachable code",
    "security": "injection vulnerabilities, secrets/credentials in code, auth/authz flaws, unsafe deserialization, OWASP Top 10",
    "performance": "N+1 queries, unnecessary allocations, blocking calls in async contexts, missing indexes, inefficient loops",
    "style": "naming conventions, excessive complexity, dead code, missing error handling at boundaries, poor readability",
}

SYSTEM_PROMPT = """\
You are a senior software engineer performing a pull request code review.
Your job is to find real, actionable issues — not stylistic nitpicks unless they indicate a real problem.

Rules:
- Only review the changed lines shown in the diff (lines starting with +).
- Do not flag issues in removed lines (starting with -) or context lines.
- Be concise. One clear sentence per finding is enough.
- If you have no findings for a file, omit it entirely.
- Do not invent problems. Only flag what you can see.
- Assign severity: "error" (must fix before merge), "warning" (should fix), "info" (minor suggestion).

Output ONLY a JSON object in this exact shape — no prose, no markdown fences:
{
  "summary": "2-3 sentence overall assessment of the PR",
  "health_score": <integer 0-10>,
  "findings": [
    {
      "file": "<relative file path>",
      "line": <line number in the new file, or 0 if file-level>,
      "severity": "error" | "warning" | "info",
      "category": "bug" | "security" | "performance" | "style",
      "message": "<concise description of the issue>",
      "suggestion": "<concrete fix suggestion>"
    }
  ]
}
"""


def build_user_prompt(pr: PRContext, config: ReviewConfig) -> str:
    focus_lines = "\n".join(
        f"- **{area}**: {_FOCUS_DESCRIPTIONS[area]}"
        for area in config.review_focus
        if area in _FOCUS_DESCRIPTIONS
    )

    parts = [
        f"## PR #{pr.number}: {pr.title}",
    ]
    if pr.body.strip():
        parts.append(f"**Description:** {pr.body[:1000]}")

    parts.append(f"\n## Review focus areas\n{focus_lines}")
    parts.append("\n## Changed files\n")

    for fd in pr.files:
        if fd.skipped:
            parts.append(f"### `{fd.path}` — SKIPPED ({fd.skip_reason})\n")
            continue
        parts.append(f"### `{fd.path}` (+{fd.additions} / -{fd.deletions})\n```diff\n{fd.patch}\n```\n")

    return "\n".join(parts)
