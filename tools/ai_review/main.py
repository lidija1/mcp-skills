"""Entry point for the AI code review bot."""
import argparse
import json
import sys

from .config import ReviewConfig
from .diff_fetcher import fetch_pr_context
from .github_poster import post_review
from .reviewer import run_review


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Code Review Bot")
    parser.add_argument("--dry-run", action="store_true", help="Print findings without posting to GitHub")
    args = parser.parse_args()

    config = ReviewConfig.from_env()
    if args.dry_run:
        config.dry_run = True

    print("[ai-review] Fetching PR context...")
    pr = fetch_pr_context(config)

    reviewable = [f for f in pr.files if not f.skipped]
    skipped = [f for f in pr.files if f.skipped]
    print(f"[ai-review] Files to review: {len(reviewable)} | Skipped: {len(skipped)} | Total diff lines: {pr.total_lines}")

    if skipped:
        for s in skipped:
            print(f"  SKIP {s.path}: {s.skip_reason}")

    if pr.total_lines > config.max_total_lines:
        msg = (
            f"This PR changes {pr.total_lines} lines, which exceeds the review limit of "
            f"{config.max_total_lines}. Please split it into smaller PRs for an AI review."
        )
        print(f"[ai-review] PR too large — {msg}")
        if not config.dry_run:
            from .github_poster import _post_or_update_summary, _build_summary_body, _BOT_MARKER
            import os, requests
            token = os.environ["GITHUB_TOKEN"]
            body = f"{_BOT_MARKER}\n## 🤖 AI Code Review\n\n⚠️ {msg}"
            from .github_poster import _find_existing_bot_comment, _gh_headers, _base_url
            existing_id = _find_existing_bot_comment(pr, token)
            if existing_id:
                url = f"{_base_url(pr)}/issues/comments/{existing_id}"
                requests.patch(url, json={"body": body}, headers=_gh_headers(token), timeout=20)
            else:
                url = f"{_base_url(pr)}/issues/{pr.number}/comments"
                requests.post(url, json={"body": body}, headers=_gh_headers(token), timeout=20)
        sys.exit(0)

    if not reviewable:
        print("[ai-review] No reviewable files after filtering. Nothing to do.")
        sys.exit(0)

    print(f"[ai-review] Running review (focus: {config.review_focus}, min_severity: {config.min_severity})...")
    result = run_review(pr, config)

    findings = result.filtered(config.min_severity)
    print(f"[ai-review] Health score: {result.health_score}/10")
    print(f"[ai-review] Findings (after filter): {len(findings)}")

    if config.dry_run:
        print("\n--- DRY RUN: findings ---")
        print(f"Summary: {result.summary}\n")
        for f in findings:
            print(f"  [{f.severity.upper()}] {f.file}:{f.line} [{f.category}] {f.message}")
            if f.suggestion:
                print(f"    -> {f.suggestion}")
        print("--- end dry run ---")
        return

    post_review(pr, result, config)
    print("[ai-review] Done.")


if __name__ == "__main__":
    main()
