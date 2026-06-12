"""Fetch PR diff from GitHub API and parse into per-file chunks."""
import fnmatch
import json
import os
import re
from dataclasses import dataclass
from typing import Optional

import requests

from .config import ReviewConfig


@dataclass
class FileDiff:
    path: str
    additions: int
    deletions: int
    patch: str           # raw unified diff for this file
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class PRContext:
    number: int
    title: str
    body: str
    base_sha: str
    head_sha: str
    owner: str
    repo: str
    files: list[FileDiff]
    total_lines: int


def _gh_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _matches_skip(path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
        # also match basename
        if fnmatch.fnmatch(os.path.basename(path), pattern):
            return True
    return False


def fetch_pr_context(config: ReviewConfig) -> PRContext:
    token = os.environ["GITHUB_TOKEN"]
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")

    with open(event_path) as f:
        event = json.load(f)

    pr = event["pull_request"]
    repo_full = event["repository"]["full_name"]
    owner, repo = repo_full.split("/", 1)
    number = pr["number"]
    base_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}"

    # Fetch changed files
    files_resp = requests.get(f"{base_url}/files", headers=_gh_headers(token), timeout=30)
    files_resp.raise_for_status()
    raw_files = files_resp.json()

    file_diffs: list[FileDiff] = []
    total_lines = 0

    for f in raw_files:
        path = f["filename"]
        additions = f.get("additions", 0)
        deletions = f.get("deletions", 0)
        patch = f.get("patch", "")
        line_count = additions + deletions

        if _matches_skip(path, config.skip_paths):
            file_diffs.append(FileDiff(path, additions, deletions, "", skipped=True, skip_reason="path filter"))
            continue

        if f.get("status") == "removed":
            file_diffs.append(FileDiff(path, 0, deletions, patch, skipped=True, skip_reason="deleted file"))
            continue

        if not patch:
            file_diffs.append(FileDiff(path, additions, deletions, "", skipped=True, skip_reason="binary or no diff"))
            continue

        if line_count > config.max_diff_lines:
            file_diffs.append(
                FileDiff(path, additions, deletions, patch[:500], skipped=True,
                         skip_reason=f"too large ({line_count} lines > {config.max_diff_lines})")
            )
            continue

        total_lines += line_count
        file_diffs.append(FileDiff(path, additions, deletions, patch))

    return PRContext(
        number=number,
        title=pr["title"],
        body=pr.get("body") or "",
        base_sha=pr["base"]["sha"],
        head_sha=pr["head"]["sha"],
        owner=owner,
        repo=repo,
        files=file_diffs,
        total_lines=total_lines,
    )
