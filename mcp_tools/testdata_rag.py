"""Fast local RAG for OneShield JSON test-data generation.

This module intentionally avoids embedding models and external vector stores.
It builds a small SQLite FTS index over existing JSON test data, UW-rule data,
dropdown-option data, selected docs, and Graphify output. Generation uses the
retrieved examples as a base record and asks the local model for field overrides
only, which is much faster and more reliable on 4B-class models than asking for
a complete record from scratch.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from mcp_tools.policy_flow_generator.persona_validator import (
    PersonaValidationError,
    validate_persona,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = PROJECT_ROOT / ".cache" / "testdata_rag.sqlite"

LOB_ALIASES = {
    "personal-auto": "auto",
    "personal_auto": "auto",
    "personal auto": "auto",
    "pa": "auto",
    "auto": "auto",
    "ho": "homeowner",
    "home": "homeowner",
    "homeowner": "homeowner",
    "cyber": "cyber",
    "gl": "general_liability",
    "general liability": "general_liability",
    "general_liability": "general_liability",
    "wc": "wc",
    "workers comp": "wc",
    "workers compensation": "wc",
}

LOB_FILES = {
    "auto": [
        "testdata/static/auto/AutoData.json",
        "testdata/static/auto/AutoUWRulesData.json",
    ],
    "homeowner": [
        "testdata/static/homeowner/HomeData.json",
        "testdata/static/homeowner/HomeUWData.json",
        "testdata/static/homeowner/HomeownerUWRulesData.json",
        "testdata/static/homeowner/HomeownerDropdownOptionsData.json",
    ],
    "cyber": [
        "testdata/static/cyber/CyberData.json",
    ],
    "general_liability": [
        "testdata/static/general_liability/GeneralLiabilityData.json",
        "testdata/static/general_liability/GeneralLiabilityDropdownOptionsData.json",
    ],
    "wc": [
        "testdata/static/wc/WCData.json",
    ],
}

DOC_FILES = [
    "README.md",
    "CLAUDE.md",
    "FRAMEWORK_GUIDE.md",
    "MCP_TOOLS_OVERVIEW.md",
    "docs/ONESHIELD_APP_KNOWLEDGE.md",
    "graphify-out/GRAPH_REPORT.md",
]


@dataclass(frozen=True)
class RetrievedDoc:
    lob: str
    kind: str
    source: str
    tc_id: str
    title: str
    text: str
    payload: dict[str, Any] | None


def normalize_lob(lob: str) -> str:
    key = str(lob or "").strip().lower().replace("-", " ")
    return LOB_ALIASES.get(key, key.replace(" ", "_"))


def build_index(index_path: Path = INDEX_PATH) -> dict[str, int]:
    """Rebuild the SQLite FTS index from repo-local knowledge sources."""
    index_path.parent.mkdir(parents=True, exist_ok=True)
    if index_path.exists():
        index_path.unlink()

    conn = sqlite3.connect(index_path)
    try:
        conn.executescript(
            """
            CREATE TABLE docs (
                id INTEGER PRIMARY KEY,
                lob TEXT NOT NULL,
                kind TEXT NOT NULL,
                source TEXT NOT NULL,
                tc_id TEXT NOT NULL,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                payload_json TEXT
            );
            CREATE VIRTUAL TABLE docs_fts USING fts5(
                title,
                text,
                content='docs',
                content_rowid='id',
                tokenize='unicode61'
            );
            """
        )

        count_by_kind: dict[str, int] = {}
        for lob, rel_paths in LOB_FILES.items():
            for rel_path in rel_paths:
                path = PROJECT_ROOT / rel_path
                if not path.exists():
                    continue
                for row in _json_records(path):
                    kind = _classify_json_doc(path, row)
                    tc_id = str(row.get("TC_ID") or row.get("Rule_ID") or row.get("id") or "")
                    title = " ".join(
                        str(row.get(key, ""))
                        for key in ("TC_ID", "UW_Description", "Description", "Program", "PolicyCoverage", "PolicyCoverageOption")
                        if row.get(key)
                    ) or path.stem
                    text = _record_text(row)
                    _insert_doc(conn, lob, kind, rel_path, tc_id, title, text, row)
                    count_by_kind[kind] = count_by_kind.get(kind, 0) + 1

        for rel_path in DOC_FILES:
            path = PROJECT_ROOT / rel_path
            if not path.exists():
                continue
            for title, text in _markdown_sections(path):
                _insert_doc(conn, "framework", "framework", rel_path, "", title, text, None)
                count_by_kind["framework"] = count_by_kind.get("framework", 0) + 1

        conn.execute(
            "INSERT INTO docs_fts(rowid, title, text) SELECT id, title, text FROM docs"
        )
        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
        return {"total": total, **count_by_kind}
    finally:
        conn.close()


def retrieve(
    query: str,
    lob: str = "",
    *,
    top_k: int = 8,
    index_path: Path = INDEX_PATH,
) -> list[RetrievedDoc]:
    """Return the highest-ranked local context rows for a query."""
    if not index_path.exists():
        build_index(index_path)

    normalized_lob = normalize_lob(lob) if lob else ""
    terms = _fts_query(query)
    conn = sqlite3.connect(index_path)
    conn.row_factory = sqlite3.Row
    try:
        params: list[Any] = []
        where = []
        if normalized_lob:
            where.append("(docs.lob = ? OR docs.lob = 'framework')")
            params.append(normalized_lob)
        if terms:
            where.append("docs_fts MATCH ?")
            params.append(terms)

        where_sql = "WHERE " + " AND ".join(where) if where else ""
        if terms:
            sql = f"""
                SELECT docs.*, bm25(docs_fts) AS rank
                FROM docs_fts
                JOIN docs ON docs_fts.rowid = docs.id
                {where_sql}
                ORDER BY rank
                LIMIT ?
            """
        else:
            sql = f"""
                SELECT docs.*, 0 AS rank
                FROM docs
                {where_sql}
                ORDER BY id
                LIMIT ?
            """
        params.append(top_k)
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_doc(row) for row in rows]
    finally:
        conn.close()


def generate_test_case(
    lob: str,
    description: str,
    *,
    model: str | None = None,
    top_k: int = 10,
    index_path: Path = INDEX_PATH,
) -> dict[str, Any]:
    """Generate one validated test case using retrieval + JSON overrides."""
    normalized_lob = normalize_lob(lob)
    context = retrieve(description, normalized_lob, top_k=top_k, index_path=index_path)
    base = _select_base_record(context, normalized_lob)
    if not base:
        raise ValueError(f"No base JSON test case found for LOB '{normalized_lob}'.")

    prompt = _generation_prompt(normalized_lob, description, base, context)
    raw = _call_ollama_json(prompt["system"], prompt["user"], model=model)
    parsed = _parse_json_object(raw)
    overrides = parsed.get("overrides", parsed)
    if not isinstance(overrides, dict):
        raise ValueError("Model response must be a JSON object with an 'overrides' object.")

    generated = dict(base)
    generated.update({k: v for k, v in overrides.items() if v is not None})
    generated.update(_heuristic_overrides(normalized_lob, description))
    generated["TC_ID"] = str(overrides.get("TC_ID") or _next_ai_tc_id())
    generated = _clean_generated_record(generated)

    validation_error = None
    try:
        if normalized_lob in {"auto", "homeowner", "cyber"}:
            generated = validate_persona(normalized_lob, generated)
    except PersonaValidationError as exc:
        validation_error = exc.errors

    return {
        "lob": normalized_lob,
        "description": description,
        "base_tc_id": base.get("TC_ID"),
        "model": model or os.getenv("OLLAMA_MODEL", "qwen3:4b"),
        "valid": validation_error is None,
        "validation_errors": validation_error or [],
        "test_case": generated,
        "retrieved": [
            {
                "lob": doc.lob,
                "kind": doc.kind,
                "source": doc.source,
                "tc_id": doc.tc_id,
                "title": doc.title,
            }
            for doc in context
        ],
    }


def append_test_case(lob: str, test_case: dict[str, Any]) -> Path:
    """Append a generated test case to the primary LOB JSON data file."""
    normalized_lob = normalize_lob(lob)
    rel_path = {
        "auto": "testdata/static/auto/AutoData.json",
        "homeowner": "testdata/static/homeowner/HomeData.json",
        "cyber": "testdata/static/cyber/CyberData.json",
        "general_liability": "testdata/static/general_liability/GeneralLiabilityData.json",
        "wc": "testdata/static/wc/WCData.json",
    }.get(normalized_lob)
    if not rel_path:
        raise ValueError(f"Unsupported LOB for append: {normalized_lob}")

    path = PROJECT_ROOT / rel_path
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data.setdefault("testCases", [])
    tc_id = test_case.get("TC_ID")
    if any(row.get("TC_ID") == tc_id for row in records):
        raise ValueError(f"TC_ID already exists in {rel_path}: {tc_id}")
    records.append(test_case)
    _atomic_write_json(path, data)
    return path


def _json_records(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict) and isinstance(data.get("testCases"), list):
        return [row for row in data["testCases"] if isinstance(row, dict)]
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _classify_json_doc(path: Path, row: dict[str, Any]) -> str:
    name = path.name.lower()
    if "dropdown" in name or row.get("DropdownField"):
        return "dropdown"
    if "uw" in name or row.get("UW_Description") or row.get("ExpectedUW"):
        return "uw_rule"
    return "example"


def _record_text(row: dict[str, Any]) -> str:
    parts = []
    for key, value in row.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            parts.append(f"{key}: {value}")
        else:
            parts.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    return "\n".join(parts)


def _markdown_sections(path: Path, max_chars: int = 1800) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    sections: list[tuple[str, str]] = []
    title = path.stem
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("#") and buf:
            body = "\n".join(buf).strip()
            if body:
                sections.append((title, body[:max_chars]))
            title = line.lstrip("#").strip() or path.stem
            buf = []
        else:
            buf.append(line)
    body = "\n".join(buf).strip()
    if body:
        sections.append((title, body[:max_chars]))
    return sections[:80]


def _insert_doc(
    conn: sqlite3.Connection,
    lob: str,
    kind: str,
    source: str,
    tc_id: str,
    title: str,
    text: str,
    payload: dict[str, Any] | None,
) -> None:
    conn.execute(
        """
        INSERT INTO docs(lob, kind, source, tc_id, title, text, payload_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            lob,
            kind,
            source,
            tc_id,
            title[:300],
            text[:8000],
            json.dumps(payload, ensure_ascii=False) if payload is not None else None,
        ),
    )


def _row_to_doc(row: sqlite3.Row) -> RetrievedDoc:
    payload_json = row["payload_json"]
    return RetrievedDoc(
        lob=row["lob"],
        kind=row["kind"],
        source=row["source"],
        tc_id=row["tc_id"],
        title=row["title"],
        text=row["text"],
        payload=json.loads(payload_json) if payload_json else None,
    )


def _fts_query(query: str) -> str:
    words = re.findall(r"[A-Za-z0-9_]{3,}", query.lower())
    words = [word for word in words if word not in {"the", "and", "for", "with", "that", "this"}]
    return " OR ".join(f'"{word}"' for word in words[:12])


def _select_base_record(context: list[RetrievedDoc], lob: str) -> dict[str, Any] | None:
    for doc in context:
        if doc.lob == lob and doc.kind == "uw_rule" and doc.payload and doc.payload.get("TC_ID"):
            return doc.payload
    for doc in context:
        if doc.lob == lob and doc.kind == "example" and doc.payload and doc.payload.get("TC_ID"):
            return doc.payload
    for doc in context:
        if doc.lob == lob and doc.payload and doc.payload.get("TC_ID"):
            return doc.payload
    docs = retrieve("standard clean base policy", lob, top_k=20)
    for doc in docs:
        if doc.lob == lob and doc.kind == "example" and doc.payload and doc.payload.get("TC_ID"):
            return doc.payload
    return None


def _generation_prompt(
    lob: str,
    description: str,
    base: dict[str, Any],
    context: list[RetrievedDoc],
) -> dict[str, str]:
    today = date.today()
    tomorrow = today + timedelta(days=1)
    context_text = "\n\n".join(
        f"[{idx}] {doc.kind} {doc.source} {doc.tc_id}\n{doc.text[:1600]}"
        for idx, doc in enumerate(context, start=1)
    )
    system = (
        "You generate insurance automation test data as JSON field overrides. "
        "You are optimized for small local models: modify the provided base record, "
        "do not create a full object from scratch. Return JSON only."
    )
    user = f"""
LOB: {lob}
Today: {today.isoformat()}
Default EffectiveDate: {tomorrow.strftime('%m/%d/%Y')}

User request:
{description}

Base record to patch:
{json.dumps(base, indent=2)}

Retrieved examples, rules, dropdowns, and framework context:
{context_text}

Return exactly this JSON shape:
{{
  "overrides": {{
    "TC_ID": "AI_YYYYMMDD_NNNNNN",
    "...": "only fields that must change from the base record"
  }}
}}

Rules:
- Use only field names already present in the base record or retrieved examples.
- Preserve required framework constants unless the request explicitly changes them.
- Use exact dropdown values from the retrieved context.
- For auto, if SR22 is "Yes", include SR22FilingState="Massachusetts".
- For auto, if Ownership is "Leased" or "Financed", include matching LossPayeeType and LossPayeeName.
- For auto, if DamageInfo is "Yes", include DescribeDamage.
- Do not include explanation, markdown, comments, or trailing text.
""".strip()
    return {"system": system, "user": user}


def _call_ollama_json(system: str, user: str, *, model: str | None = None) -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    if base_url.endswith("/v1"):
        base_url = base_url[:-3]
    payload = {
        "model": model or os.getenv("OLLAMA_MODEL", "qwen3:4b"),
        "stream": False,
        "think": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {
            "temperature": 0,
            "num_predict": 700,
            "num_ctx": int(os.getenv("TESTDATA_RAG_NUM_CTX", "8192")),
        },
    }
    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 404:
            raise RuntimeError(
                f"Ollama model '{payload['model']}' is not installed. "
                f"Install it with: ollama pull {payload['model']}"
            ) from exc
        raise RuntimeError(f"Ollama HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama is not reachable at {base_url}.") from exc
    message = body.get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Ollama response did not contain message.content.")
    return content.strip()


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Expected model to return a JSON object.")
    return parsed


def _clean_generated_record(record: dict[str, Any]) -> dict[str, Any]:
    record.setdefault("EffectiveDate", (date.today() + timedelta(days=1)).strftime("%m/%d/%Y"))
    record.setdefault("PaymentPlan", "Pay In Full")
    if record.get("RoofType") == "Wood Shake/Shingle":
        record["RoofType"] = "Wood Shake"
    tc_id = str(record.get("TC_ID") or "")
    if not tc_id.startswith("AI_"):
        record["TC_ID"] = _next_ai_tc_id()
    if record.get("SR22") != "Yes":
        record.pop("SR22FilingState", None)
    if record.get("Ownership") == "Owned":
        record.pop("LossPayeeType", None)
        record.pop("LossPayeeName", None)
    if record.get("DamageInfo") != "Yes":
        record.pop("DescribeDamage", None)
    return record


def _heuristic_overrides(lob: str, description: str) -> dict[str, Any]:
    """Apply cheap deterministic constraints for fields small models often miss."""
    text = description.lower()
    out: dict[str, Any] = {}
    if lob == "auto":
        coverage_map = {
            "bronze": "Bronze",
            "silver": "Silver",
            "gold": "Gold",
            "platinum": "Platinum",
        }
        for token, value in coverage_map.items():
            if token in text or (token == "platinum" and "full coverage" in text):
                out["PolicyCoverage"] = value

        if "sr-22" in text or "sr22" in text:
            out["SR22"] = "Yes"
            out["SR22FilingState"] = "Massachusetts"
        if "revoked" in text:
            out["LicenseStatus"] = "Revoked"
        elif "suspended" in text:
            out["LicenseStatus"] = "Suspended"

        if "leased" in text or "lease" in text:
            out["Ownership"] = "Leased"
            out["LossPayeeType"] = "Leased"
            out.setdefault("LossPayeeName", "BMW Financial Services" if "bmw" in text else "Lease Finance Company")
        elif "financed" in text or "finance" in text:
            out["Ownership"] = "Financed"
            out["LossPayeeType"] = "Financed"
            out.setdefault("LossPayeeName", "Auto Finance Company")
        elif "owned" in text:
            out["Ownership"] = "Owned"

        if "damage" in text or "accident" in text:
            out["DamageInfo"] = "Yes"
            out.setdefault("DescribeDamage", "Prior accident damage reported by applicant")

    if lob == "homeowner":
        if "renovation" in text or "renovating" in text:
            out["Renovation"] = "Yes"
        if "declined" in text:
            out["Declined"] = "Yes"
        if "refused" in text or "non-renewed" in text or "nonrenewed" in text:
            out["Refused"] = "Yes"
        if "frame" in text:
            out["ConstructionType"] = "Frame"

    return out


def _next_ai_tc_id() -> str:
    return f"AI_{date.today().strftime('%Y%m%d')}_{int(time.time() * 1000) % 1000000:06d}"


def _atomic_write_json(path: Path, data: Any) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fast local RAG for test data JSON.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("build", help="Rebuild the local SQLite FTS index.")

    search = sub.add_parser("search", help="Retrieve context for a query.")
    search.add_argument("query")
    search.add_argument("--lob", default="")
    search.add_argument("--top-k", type=int, default=8)

    gen = sub.add_parser("generate", help="Generate one test case with Ollama.")
    gen.add_argument("description")
    gen.add_argument("--lob", required=True)
    gen.add_argument("--model", default=None)
    gen.add_argument("--top-k", type=int, default=10)
    gen.add_argument("--append", action="store_true", help="Append valid output to the primary LOB JSON file.")

    args = parser.parse_args(argv)
    if args.command == "build":
        print(json.dumps(build_index(), indent=2))
        return 0
    if args.command == "search":
        docs = retrieve(args.query, args.lob, top_k=args.top_k)
        print(json.dumps([
            {
                "lob": doc.lob,
                "kind": doc.kind,
                "source": doc.source,
                "tc_id": doc.tc_id,
                "title": doc.title,
            }
            for doc in docs
        ], indent=2))
        return 0
    if args.command == "generate":
        result = generate_test_case(args.lob, args.description, model=args.model, top_k=args.top_k)
        if args.append:
            if not result["valid"]:
                raise SystemExit("Generated test case is not valid; refusing to append.")
            result["appended_to"] = str(append_test_case(args.lob, result["test_case"]))
        print(json.dumps(result, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
