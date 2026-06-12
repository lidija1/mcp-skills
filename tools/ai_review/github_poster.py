"""Post review findings to the GitHub PR as inline comments + summary."""
import os
import re
from datetime import datetime, timezone

import requests

from .config import ReviewConfig
from .diff_fetcher import PRContext
from .reviewer import Finding, ReviewResult

_SEVERITY_EMOJI = {"error": "🔴", "warning": "🟡", "info": "🔵"}
_BOT_MARKER = "<!-- ai-review-bot -->"


def _gh_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _base_url(pr: PRContext) -> str:
    return f"https://api.github.com/repos/{pr.owner}/{pr.repo}"


def _find_existing_bot_comment(pr: PRContext, token: str) -> int | None:
    url = f"{_base_url(pr)}/issues/{pr.number}/comments"
    resp = requests.get(url, headers=_gh_headers(token), timeout=20)
    resp.raise_for_status()
    for comment in resp.json():
        if _BOT_MARKER in comment.get("body", ""):
            return comment["id"]
    return None


def _build_summary_body(pr: PRContext, result: ReviewResult, findings: list[Finding], config: ReviewConfig) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    score_bar = "█" * result.health_score + "░" * (10 - result.health_score)
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    infos = sum(1 for f in findings if f.severity == "info")

    lines = [
        _BOT_MARKER,
        f"## 🤖 AI Code Review — PR #{pr.number}",
        f"",
        f"> {result.summary}",
        f"",
        f"**Health score:** `{result.health_score}/10` `{score_bar}`",
        f"**Findings:** 🔴 {errors} errors · 🟡 {warnings} warnings · 🔵 {infos} info",
        f"",
    ]

    if not findings:
        lines.append("✅ No issues found at the configured severity threshold.")
    else:
        for sev in ["error", "warning", "info"]:
            group = [f for f in findings if f.severity == sev]
            if not group:
                continue
            emoji = _SEVERITY_EMOJI[sev]
            lines.append(f"### {emoji} {sev.capitalize()}s\n")
            for f in group:
                loc = f"`{f.file}`" + (f" line {f.line}" if f.line else "")
                lines.append(f"- **[{f.category}]** {loc}: {f.message}")
                if f.suggestion:
                    lines.append(f"  > 💡 {f.suggestion}")
            lines.append("")

    lines.append(f"---")
    lines.append(f"_Reviewed by AI · {ts} · min severity: `{config.min_severity}` · focus: `{', '.join(config.review_focus)}`_")
    return "\n".join(lines)


def _post_or_update_summary(pr: PRContext, body: str, token: str) -> None:
    existing_id = _find_existing_bot_comment(pr, token)
    if existing_id:
        url = f"{_base_url(pr)}/issues/comments/{existing_id}"
        resp = requests.patch(url, json={"body": body}, headers=_gh_headers(token), timeout=20)
    else:
        url = f"{_base_url(pr)}/issues/{pr.number}/comments"
        resp = requests.post(url, json={"body": body}, headers=_gh_headers(token), timeout=20)
    resp.raise_for_status()
    print(f"[ai-review] Summary comment {'updated' if existing_id else 'posted'}")


def _compute_position(patch: str, target_line: int) -> int | None:
    """Map a new-file line number to a diff position (1-indexed hunk offset)."""
    position = 0
    current_new_line = 0
    for raw_line in patch.splitlines():
        hunk_match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw_line)
        if hunk_match:
            current_new_line = int(hunk_match.group(1)) - 1
            position += 1
            continue
        if raw_line.startswith("\\"):
            continue
        position += 1
        if not raw_line.startswith("-"):
            current_new_line += 1
        if current_new_line == target_line:
            return position
    return None


def _post_inline_comments(pr: PRContext, findings: list[Finding], token: str) -> None:
    # Build a patch map: path -> patch text
    patch_map = {fd.path: fd.patch for fd in pr.files if not fd.skipped and fd.patch}

    review_comments = []
    file_level: list[Finding] = []

    for f in findings:
        if f.line == 0 or f.file not in patch_map:
            file_level.append(f)
            continue
        position = _compute_position(patch_map[f.file], f.line)
        if position is None:
            file_level.append(f)
            continue
        emoji = _SEVERITY_EMOJI.get(f.severity, "🔵")
        body = (
            f"{emoji} **[{f.category}/{f.severity}]** {f.message}\n\n"
            + (f"> 💡 {f.suggestion}" if f.suggestion else "")
        )
        review_comments.append({
            "path": f.file,
            "position": position,
            "body": body.strip(),
        })

    if review_comments:
        url = f"{_base_url(pr)}/pulls/{pr.number}/reviews"
        payload = {
            "commit_id": pr.head_sha,
            "event": "COMMENT",
            "comments": review_comments,
        }
        resp = requests.post(url, json=payload, headers=_gh_headers(token), timeout=30)
        if not resp.ok:
            print(f"[ai-review] Inline comment batch failed ({resp.status_code}): {resp.text[:300]}")
        else:
            print(f"[ai-review] Posted {len(review_comments)} inline comment(s)")

    return file_level


def post_review(pr: PRContext, result: ReviewResult, config: ReviewConfig) -> None:
    token = os.environ["GITHUB_TOKEN"]
    findings = result.filtered(config.min_severity)
    mode = config.review_mode

    if mode == "summary":
        summary_body = _build_summary_body(pr, result, findings, config)
        _post_or_update_summary(pr, summary_body, token)
    elif mode == "inline":
        file_level_overflow = _post_inline_comments(pr, findings, token)
        # findings that couldn't be placed inline go into a summary comment
        if file_level_overflow:
            summary_body = _build_summary_body(pr, result, file_level_overflow, config)
            _post_or_update_summary(pr, summary_body, token)
    elif mode == "both":
        file_level_overflow = _post_inline_comments(pr, findings, token)
        summary_body = _build_summary_body(pr, result, findings, config)
        _post_or_update_summary(pr, summary_body, token)
    else:
        raise ValueError(f"Unknown REVIEW_MODE: {mode!r}. Use 'inline', 'summary', or 'both'.")
