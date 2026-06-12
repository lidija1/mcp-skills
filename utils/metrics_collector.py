"""
Metrics collector for pytest test runs.

Usage in tests:
    from utils.metrics_collector import record_metric
    record_metric("policy_number", "POL-123")
    record_metric("premium", 1250.00)
    record_metric("uw_result", "approved")
    record_metric("lob", "Personal Auto")
    record_metric("validation_type", "direct_assert")
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import local

# Thread-local storage for per-test extra data
_store = local()

METRICS_DIR = Path("reports") / "metrics"
METRICS_FILE = METRICS_DIR / "execution_metrics.jsonl"


def _current_extras() -> dict:
    if not hasattr(_store, "extras"):
        _store.extras = {}
    return _store.extras


def record_metric(key: str, value) -> None:
    """Attach extra business data to the currently running test metric record."""
    _current_extras()[key] = value


def _reset_extras() -> dict:
    extras = _current_extras().copy()
    _store.extras = {}
    return extras


def _infer_test_type(item) -> str:
    markers = {m.name for m in item.iter_markers()}
    if "api" in markers:
        return "api"
    if "uw" in markers or "uw_rules" in markers:
        return "uw"
    if "validation" in markers:
        return "validation"
    return "ui"


def _infer_lob(item) -> str:
    markers = {m.name for m in item.iter_markers()}
    lob_map = {
        "auto": "Personal Auto",
        "homeowner": "Homeowner",
        "cyber": "Cyber",
        "gl": "General Liability",
    }
    for marker, lob in lob_map.items():
        if marker in markers:
            return lob
    return ""


def _infer_validation_type(item) -> str:
    name = item.name.lower()
    if "regression_sweep" in name or "regression-sweep" in name:
        return "regression_sweep"
    if "direct_assert" in name or "direct-assert" in name:
        return "direct_assert"
    return "normal_flow"


def build_metric(item, report, start_time: datetime, end_time: datetime, run_id: str) -> dict:
    extras = _reset_extras()

    status = "passed" if report.passed else ("failed" if report.failed else "skipped")
    error_message = ""
    if report.failed and report.longrepr:
        error_message = str(report.longrepr)[-2000:]  # cap to avoid huge records

    scenario_name = ""
    node_id = item.nodeid
    if "::" in node_id:
        parts = node_id.split("::")
        scenario_name = parts[-1] if len(parts) > 1 else ""

    markers = [m.name for m in item.iter_markers()]

    metric = {
        "run_id": run_id,
        "test_id": node_id,
        "test_name": item.name,
        "test_file": str(item.fspath).replace("\\", "/"),
        "test_type": extras.pop("test_type", _infer_test_type(item)),
        "lob": extras.pop("lob", _infer_lob(item)),
        "scenario_name": scenario_name,
        "status": status,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": round((end_time - start_time).total_seconds(), 3),
        "environment": os.getenv("ENV", "sandbox"),
        "browser": os.getenv("BROWSER", "chromium"),
        "build_number": os.getenv("BUILD_NUMBER", ""),
        "triggered_by": os.getenv("BUILD_USER", os.getenv("USERNAME", "")),
        "error_message": error_message,
        "screenshot_path": extras.pop("screenshot_path", ""),
        "policy_number": extras.pop("policy_number", ""),
        "premium": extras.pop("premium", ""),
        "uw_result": extras.pop("uw_result", ""),
        "rating_result": extras.pop("rating_result", ""),
        "mcp_tool": extras.pop("mcp_tool", ""),
        "validation_type": extras.pop("validation_type", _infer_validation_type(item)),
        "tags": markers,
    }
    # Merge any remaining extra keys the test attached
    metric.update(extras)
    return metric


def write_metric(metric: dict) -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    with open(METRICS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(metric) + "\n")
