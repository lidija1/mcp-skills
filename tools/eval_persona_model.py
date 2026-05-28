from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "mcp_tools" / "policy_flow_generator" / "persona_eval_cases.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate local persona JSON generation against prompt expectations."
    )
    parser.add_argument("--cases", default=str(DEFAULT_CASES), help="Path to eval cases JSON.")
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "qwen3:8b"), help="Ollama model name.")
    parser.add_argument("--base-url", default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"), help="Ollama base URL.")
    parser.add_argument("--out", default="", help="Optional JSON report output path.")
    return parser.parse_args()


def _load_cases(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError("Cases file must contain a JSON array.")
    return data


def _evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    from mcp_tools.policy_flow_generator.persona_generator import generate_persona

    started = time.perf_counter()
    raw = generate_persona(str(case["lob"]), str(case["prompt"]))
    elapsed_ms = round((time.perf_counter() - started) * 1000)

    try:
        persona = json.loads(raw)
        valid_json = isinstance(persona, dict)
    except json.JSONDecodeError as exc:
        persona = {"error": f"invalid json: {exc}", "raw": raw}
        valid_json = False

    mismatches = []
    for key, expected in dict(case.get("expect", {})).items():
        actual = persona.get(key) if isinstance(persona, dict) else None
        if actual != expected:
            mismatches.append({"field": key, "expected": expected, "actual": actual})

    provider = persona.get("_provider") if isinstance(persona, dict) else None
    return {
        "id": case.get("id"),
        "lob": case.get("lob"),
        "prompt": case.get("prompt"),
        "ok": valid_json and not mismatches and "error" not in persona,
        "valid_json": valid_json,
        "provider": provider,
        "elapsed_ms": elapsed_ms,
        "mismatches": mismatches,
        "error": persona.get("error") if isinstance(persona, dict) else None,
        "validation_errors": persona.get("validation_errors") if isinstance(persona, dict) else None,
        "persona": persona,
    }


def main() -> int:
    args = _parse_args()
    os.environ["AI_PROVIDER"] = "ollama"
    os.environ["OLLAMA_MODEL"] = args.model
    os.environ["OLLAMA_BASE_URL"] = args.base_url

    cases = _load_cases(Path(args.cases))
    results = [_evaluate_case(case) for case in cases]

    total = len(results)
    passed = sum(1 for result in results if result["ok"])
    validation_error_count = sum(1 for result in results if result.get("validation_errors"))
    avg_ms = round(sum(result["elapsed_ms"] for result in results) / total) if total else 0

    report = {
        "model": args.model,
        "base_url": args.base_url,
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "validation_error_count": validation_error_count,
        "avg_ms": avg_ms,
        "results": results,
    }

    print(
        f"model={args.model} passed={passed}/{total} "
        f"validation_errors={validation_error_count} avg_ms={avg_ms}"
    )
    for result in results:
        status = "OK" if result["ok"] else "FAIL"
        print(f"{status} {result['id']} provider={result['provider']} elapsed_ms={result['elapsed_ms']}")
        for mismatch in result["mismatches"]:
            print(
                f"  {mismatch['field']}: expected {mismatch['expected']!r}, "
                f"actual {mismatch['actual']!r}"
            )
        if result.get("error"):
            print(f"  error: {result['error']}")
        if result.get("validation_errors"):
            for validation_error in result["validation_errors"]:
                print(f"  validation: {validation_error}")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
