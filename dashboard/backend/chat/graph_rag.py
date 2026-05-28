"""
Read-only Graph RAG retrieval for dashboard Guidance mode.

This module reads graphify output and selected framework docs, ranks compact
snippets against the user's question, and returns prompt context. It never
executes tools, runs tests, writes files, or reads secrets.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_GRAPH_DIR = _PROJECT_ROOT / "graphify-out"
_GRAPH_JSON = _GRAPH_DIR / "graph.json"
_GRAPH_REPORT = _GRAPH_DIR / "GRAPH_REPORT.md"

_DOC_FILES = [
    "README.md",
    "CLAUDE.md",
    "FRAMEWORK_GUIDE.md",
    "MCP_TOOLS_OVERVIEW.md",
    "conftest.py",
    "ui/fixtures.py",
    "ui/pages/common/base_page.py",
    "ui/steps/common/data_steps.py",
    "dashboard/README.md",
    "dashboard/DASHBOARD_GUIDE.md",
]

_STOPWORDS = {
    "about", "after", "again", "all", "also", "and", "are", "ask", "can",
    "could", "does", "for", "from", "have", "help", "how", "into", "like",
    "need", "our", "that", "the", "this", "use", "using", "what", "when",
    "where", "which", "why", "with", "would", "your",
}

_SYNONYMS = {
    "chat": {"chat", "assistant", "message", "guidance", "ollama", "llm"},
    "dashboard": {"dashboard", "fastapi", "react", "jobs", "panel"},
    "mcp": {"mcp", "tool", "tools", "registry", "dispatch"},
    "workflow": {"workflow", "flow", "journey", "scenario", "feature", "steps"},
    "auto": {"auto", "personal", "driver", "vehicle"},
    "homeowner": {"homeowner", "home", "property"},
    "cyber": {"cyber", "security", "breach"},
    "uw": {"uw", "underwriting", "rule", "rules", "audit", "referral"},
    "page": {"page", "pages", "pom", "object", "basepage", "selector"},
    "fixture": {"fixture", "fixtures", "conftest", "pytest"},
    "data": {"data", "json", "testdata", "tc_id", "persona"},
}


def retrieve_framework_context(question: str, max_chars: int = 9000) -> str:
    terms = _expand_terms(_extract_terms(question))
    sections: list[str] = [
        _static_framework_facts(),
        _doc_context(terms),
        _graph_json_context(terms),
        _graph_report_context(terms),
    ]
    context = "\n\n".join(section for section in sections if section.strip())
    if len(context) <= max_chars:
        return context
    return context[:max_chars].rsplit("\n", 1)[0] + "\n... [context truncated]"


def _extract_terms(text: str) -> set[str]:
    words = {w.lower() for w in re.findall(r"[A-Za-z_][A-Za-z0-9_/-]{2,}", text)}
    terms = {w.strip("_-/") for w in words if w not in _STOPWORDS}
    return {w for w in terms if len(w) >= 3}


def _expand_terms(terms: set[str]) -> set[str]:
    expanded = set(terms)
    for term in list(terms):
        for key, values in _SYNONYMS.items():
            if term == key or term in values:
                expanded.update(values)
    return expanded


def _score_text(text: str, terms: set[str]) -> int:
    haystack = text.lower()
    score = 0
    for term in terms:
        if term in haystack:
            score += 3
        if re.search(rf"\b{re.escape(term)}\b", haystack):
            score += 2
    return score


def _static_framework_facts() -> str:
    return "\n".join([
        "## Framework Facts",
        "- UI tests are BDD-first: feature files -> step definitions -> page objects.",
        "- Feature files live in ui/features/, steps in ui/steps/, page objects in ui/pages/.",
        "- conftest.py registers pytest_plugins; ui/fixtures.py registers page-object fixtures.",
        "- BasePage smart wrappers should be reused for Playwright interactions.",
        "- JSON test data under testdata/static/ is filtered by TC_ID.",
        "- Dashboard chat Tools mode executes only whitelisted registry tools.",
        "- Dashboard Guidance mode is read-only and should explain, not execute.",
        "- Main MCP-backed capabilities include policy flows, persona generation, UW audits, form intelligence, accessibility, and LOB recording.",
    ])


def _graph_report_context(terms: set[str]) -> str:
    if not _GRAPH_REPORT.exists():
        return "## Graph Report\n- graphify-out/GRAPH_REPORT.md not found."
    lines = _GRAPH_REPORT.read_text(encoding="utf-8", errors="replace").splitlines()
    selected: list[str] = []
    capture_headers = {"## Summary", "## God Nodes (most connected - your core abstractions)", "## Hyperedges (group relationships)"}
    capture = False
    for line in lines:
        if line.startswith("## "):
            capture = line in capture_headers
        if capture:
            selected.append(line)
            if len(selected) >= 45:
                break

    scored = [
        line for line in lines
        if line and not line.startswith("[[") and _score_text(line, terms) > 0
    ][:20]
    return "\n".join(["## Graph Report Highlights", *selected, "", "## Matching Graph Report Lines", *scored])


def _load_graph() -> dict[str, Any]:
    if not _GRAPH_JSON.exists():
        return {"nodes": [], "links": [], "hyperedges": []}
    return _load_graph_for_mtime(_GRAPH_JSON.stat().st_mtime)


@lru_cache(maxsize=4)
def _load_graph_for_mtime(mtime: float) -> dict[str, Any]:
    del mtime
    return json.loads(_GRAPH_JSON.read_text(encoding="utf-8", errors="replace"))


def _graph_json_context(terms: set[str]) -> str:
    graph = _load_graph()
    nodes = graph.get("nodes", [])
    links = graph.get("links", [])
    hyperedges = graph.get("hyperedges", [])
    node_by_id = {node.get("id"): node for node in nodes}

    node_rows = []
    for node in nodes:
        text = " ".join(str(node.get(k, "")) for k in ("label", "source_file", "source_location", "community"))
        score = _score_text(text, terms)
        if score:
            node_rows.append((score, node))
    node_rows.sort(key=lambda item: item[0], reverse=True)

    link_rows = []
    for link in links:
        src = node_by_id.get(link.get("source")) or {}
        tgt = node_by_id.get(link.get("target")) or {}
        text = " ".join([
            str(src.get("label", "")),
            str(link.get("relation", "")),
            str(tgt.get("label", "")),
            str(link.get("source_file", "")),
        ])
        score = _score_text(text, terms)
        if score:
            link_rows.append((score, link, src, tgt))
    link_rows.sort(key=lambda item: item[0], reverse=True)

    hyper_rows = []
    for hyper in hyperedges:
        text = " ".join([
            str(hyper.get("label", "")),
            str(hyper.get("relation", "")),
            str(hyper.get("source_file", "")),
            " ".join(str(n) for n in hyper.get("nodes", [])),
        ])
        score = _score_text(text, terms)
        if score:
            hyper_rows.append((score, hyper))
    hyper_rows.sort(key=lambda item: item[0], reverse=True)

    lines = ["## Retrieved Graph Entities"]
    for score, node in node_rows[:12]:
        location = f"{node.get('source_file', '')}:{node.get('source_location', '')}".strip(":")
        lines.append(f"- node: {node.get('label')} ({location}) score={score}")

    lines.append("")
    lines.append("## Retrieved Graph Relationships")
    for score, link, src, tgt in link_rows[:12]:
        source_file = link.get("source_file", "")
        lines.append(
            f"- {src.get('label')} --{link.get('relation')}--> {tgt.get('label')} "
            f"({source_file}) score={score}"
        )

    lines.append("")
    lines.append("## Retrieved Hyperedges")
    for score, hyper in hyper_rows[:5]:
        node_list = ", ".join(str(n) for n in hyper.get("nodes", [])[:8])
        lines.append(f"- {hyper.get('label')}: {node_list} ({hyper.get('source_file', '')}) score={score}")

    return "\n".join(lines)


def _doc_context(terms: set[str]) -> str:
    lines = ["## Retrieved Documentation Snippets"]
    for rel_path in _DOC_FILES:
        path = _PROJECT_ROOT / rel_path
        if not path.exists():
            continue
        snippets = _matching_doc_lines(path, terms)
        if not snippets:
            continue
        lines.append(f"### {rel_path}")
        lines.extend(f"- {snippet}" for snippet in snippets[:8])
    return "\n".join(lines)


def _matching_doc_lines(path: Path, terms: set[str]) -> list[str]:
    raw_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    matches: list[tuple[int, str]] = []
    for idx, line in enumerate(raw_lines, start=1):
        clean = line.strip()
        if not clean or len(clean) > 220:
            continue
        score = _score_text(clean, terms)
        if score:
            matches.append((score, f"L{idx}: {clean}"))
    matches.sort(key=lambda item: item[0], reverse=True)
    return [line for _, line in matches[:10]]
