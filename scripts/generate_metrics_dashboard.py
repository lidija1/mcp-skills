"""
Automation Metrics Dashboard Generator

Reads:  reports/metrics/execution_metrics.jsonl
Writes: reports/metrics/automation_dashboard.html

Run manually:
    python scripts/generate_metrics_dashboard.py

Also called automatically by conftest.py after every pytest session.
"""

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

METRICS_FILE = Path("reports") / "metrics" / "execution_metrics.jsonl"
OUTPUT_FILE = Path("reports") / "metrics" / "automation_dashboard.html"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_metrics() -> list[dict]:
    if not METRICS_FILE.exists():
        return []
    records = []
    with open(METRICS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def _count_status(records: list[dict], status: str) -> int:
    return sum(1 for r in records if r.get("status") == status)


def _safe_float(val) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def build_summary(records: list[dict]) -> dict:
    total = len(records)
    passed = _count_status(records, "passed")
    failed = _count_status(records, "failed")
    skipped = _count_status(records, "skipped")
    pass_rate = round(passed / total * 100, 1) if total else 0.0
    total_time = sum(_safe_float(r.get("duration_seconds")) for r in records)
    avg_time = round(total_time / total, 2) if total else 0.0
    policies = sum(1 for r in records if r.get("policy_created") or r.get("policy_number"))
    direct_asserts = sum(1 for r in records if r.get("validation_type") == "direct_assert")
    reg_sweeps = sum(1 for r in records if r.get("validation_type") == "regression_sweep")
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "pass_rate": pass_rate,
        "total_time": round(total_time, 1),
        "avg_time": avg_time,
        "policies": policies,
        "direct_asserts": direct_asserts,
        "reg_sweeps": reg_sweeps,
    }


def latest_failed(records: list[dict], n: int = 10) -> list[dict]:
    failed = [r for r in records if r.get("status") == "failed"]
    failed.sort(key=lambda r: r.get("end_time", ""), reverse=True)
    return failed[:n]


def slowest_tests(records: list[dict], n: int = 10) -> list[dict]:
    ranked = sorted(records, key=lambda r: _safe_float(r.get("duration_seconds")), reverse=True)
    return ranked[:n]


def by_lob(records: list[dict]) -> list[dict]:
    agg = defaultdict(lambda: {"passed": 0, "failed": 0, "skipped": 0})
    for r in records:
        lob = r.get("lob") or "Unknown"
        agg[lob][r.get("status", "skipped")] += 1
    rows = []
    for lob, counts in sorted(agg.items()):
        total = counts["passed"] + counts["failed"] + counts["skipped"]
        rows.append({
            "lob": lob,
            "passed": counts["passed"],
            "failed": counts["failed"],
            "skipped": counts["skipped"],
            "total": total,
        })
    return rows


def by_validation_type(records: list[dict]) -> list[dict]:
    agg = defaultdict(lambda: {"passed": 0, "failed": 0, "skipped": 0})
    for r in records:
        vtype = r.get("validation_type") or "normal_flow"
        agg[vtype][r.get("status", "skipped")] += 1
    rows = []
    for vtype, counts in sorted(agg.items()):
        total = counts["passed"] + counts["failed"] + counts["skipped"]
        rows.append({
            "type": vtype,
            "passed": counts["passed"],
            "failed": counts["failed"],
            "skipped": counts["skipped"],
            "total": total,
        })
    return rows


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def _escape(val) -> str:
    return str(val).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _status_badge(status: str) -> str:
    colours = {"passed": "#22c55e", "failed": "#ef4444", "skipped": "#f59e0b"}
    colour = colours.get(status, "#6b7280")
    return f'<span style="background:{colour};color:#fff;padding:2px 8px;border-radius:4px;font-size:0.8em">{_escape(status)}</span>'


def _table(headers: list[str], rows: list[list]) -> str:
    th = "".join(f"<th>{h}</th>" for h in headers)
    tbody = ""
    for row in rows:
        td = "".join(f"<td>{cell}</td>" for cell in row)
        tbody += f"<tr>{td}</tr>"
    return f"""
<table>
  <thead><tr>{th}</tr></thead>
  <tbody>{tbody}</tbody>
</table>"""


def generate_html(records: list[dict]) -> str:
    s = build_summary(records)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Chart data
    chart_labels_status = json.dumps(["Passed", "Failed", "Skipped"])
    chart_data_status = json.dumps([s["passed"], s["failed"], s["skipped"]])

    top_slow = slowest_tests(records, 12)
    chart_labels_slow = json.dumps([r.get("test_name", "")[:30] for r in top_slow])
    chart_data_slow = json.dumps([_safe_float(r.get("duration_seconds")) for r in top_slow])

    lob_rows = by_lob(records)
    chart_labels_lob = json.dumps([r["lob"] for r in lob_rows])
    chart_data_lob_pass = json.dumps([r["passed"] for r in lob_rows])
    chart_data_lob_fail = json.dumps([r["failed"] for r in lob_rows])

    # Failed tests table
    failed_table_rows = [
        [
            _escape(r.get("test_name", ""))[:60],
            _escape(r.get("lob", "")),
            _escape(r.get("duration_seconds", "")),
            _escape(r.get("end_time", "")[:19]),
            f'<span title="{_escape(r.get("error_message",""))[:300]}" style="cursor:help">hover</span>',
        ]
        for r in latest_failed(records)
    ]
    failed_table = _table(["Test", "LOB", "Duration (s)", "Time", "Error"], failed_table_rows)

    # Slowest tests table
    slow_table_rows = [
        [
            _escape(r.get("test_name", ""))[:60],
            _status_badge(r.get("status", "")),
            _escape(r.get("lob", "")),
            _escape(r.get("duration_seconds", "")),
        ]
        for r in top_slow
    ]
    slow_table = _table(["Test", "Status", "LOB", "Duration (s)"], slow_table_rows)

    # By LOB table
    lob_table_rows = [
        [_escape(r["lob"]), r["passed"], r["failed"], r["skipped"], r["total"]]
        for r in lob_rows
    ]
    lob_table = _table(["LOB", "Passed", "Failed", "Skipped", "Total"], lob_table_rows)

    # By validation type table
    vtype_rows = [
        [_escape(r["type"]), r["passed"], r["failed"], r["skipped"], r["total"]]
        for r in by_validation_type(records)
    ]
    vtype_table = _table(["Validation Type", "Passed", "Failed", "Skipped", "Total"], vtype_rows)

    no_data_msg = "" if records else '<p style="color:#f59e0b;text-align:center;padding:2rem">No metrics data found. Run pytest to generate metrics.</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Automation Metrics Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}}
  header{{background:#1e293b;padding:1.2rem 2rem;border-bottom:1px solid #334155;display:flex;justify-content:space-between;align-items:center}}
  header h1{{font-size:1.4rem;font-weight:700;color:#38bdf8}}
  header .meta{{font-size:0.78rem;color:#94a3b8}}
  .container{{max-width:1400px;margin:0 auto;padding:1.5rem 2rem}}
  .cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:1rem;margin-bottom:2rem}}
  .card{{background:#1e293b;border-radius:10px;padding:1.1rem 1.3rem;border:1px solid #334155}}
  .card .label{{font-size:0.72rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;margin-bottom:.3rem}}
  .card .value{{font-size:1.8rem;font-weight:700;color:#f1f5f9}}
  .card.green .value{{color:#4ade80}}
  .card.red .value{{color:#f87171}}
  .card.yellow .value{{color:#fbbf24}}
  .card.blue .value{{color:#38bdf8}}
  section{{margin-bottom:2.5rem}}
  section h2{{font-size:1rem;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:.07em;margin-bottom:1rem;border-bottom:1px solid #334155;padding-bottom:.5rem}}
  .charts{{display:grid;grid-template-columns:1fr 2fr 1fr;gap:1.5rem;margin-bottom:2.5rem}}
  .chart-box{{background:#1e293b;border-radius:10px;padding:1.2rem;border:1px solid #334155}}
  .chart-box h3{{font-size:0.82rem;color:#94a3b8;margin-bottom:1rem;text-transform:uppercase;letter-spacing:.05em}}
  table{{width:100%;border-collapse:collapse;background:#1e293b;border-radius:10px;overflow:hidden;border:1px solid #334155}}
  thead tr{{background:#0f172a}}
  th{{padding:.7rem 1rem;text-align:left;font-size:0.75rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em}}
  td{{padding:.65rem 1rem;font-size:0.85rem;border-top:1px solid #1e293b;color:#cbd5e1}}
  tr:hover td{{background:#243047}}
  .tables-grid{{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem}}
  @media(max-width:900px){{.charts{{grid-template-columns:1fr}}.tables-grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header>
  <h1>Automation Metrics Dashboard</h1>
  <span class="meta">Generated: {generated_at}</span>
</header>
<div class="container">
{no_data_msg}
<div class="cards">
  <div class="card"><div class="label">Total Tests</div><div class="value">{s["total"]}</div></div>
  <div class="card green"><div class="label">Passed</div><div class="value">{s["passed"]}</div></div>
  <div class="card red"><div class="label">Failed</div><div class="value">{s["failed"]}</div></div>
  <div class="card yellow"><div class="label">Skipped</div><div class="value">{s["skipped"]}</div></div>
  <div class="card blue"><div class="label">Pass Rate</div><div class="value">{s["pass_rate"]}%</div></div>
  <div class="card"><div class="label">Total Time (s)</div><div class="value">{s["total_time"]}</div></div>
  <div class="card"><div class="label">Avg Duration (s)</div><div class="value">{s["avg_time"]}</div></div>
  <div class="card blue"><div class="label">Policies Created</div><div class="value">{s["policies"]}</div></div>
  <div class="card"><div class="label">Direct Asserts</div><div class="value">{s["direct_asserts"]}</div></div>
  <div class="card"><div class="label">Reg. Sweeps</div><div class="value">{s["reg_sweeps"]}</div></div>
</div>

<div class="charts">
  <div class="chart-box">
    <h3>Pass / Fail / Skipped</h3>
    <canvas id="chartStatus"></canvas>
  </div>
  <div class="chart-box">
    <h3>Slowest Tests (duration seconds)</h3>
    <canvas id="chartSlow"></canvas>
  </div>
  <div class="chart-box">
    <h3>Results by LOB</h3>
    <canvas id="chartLob"></canvas>
  </div>
</div>

<div class="tables-grid">
  <section>
    <h2>Latest Failed Tests</h2>
    {failed_table}
  </section>
  <section>
    <h2>Slowest Tests</h2>
    {slow_table}
  </section>
  <section>
    <h2>Results by LOB</h2>
    {lob_table}
  </section>
  <section>
    <h2>Results by Validation Type</h2>
    {vtype_table}
  </section>
</div>
</div>

<script>
const DARK = '#1e293b';
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = '#334155';

new Chart(document.getElementById('chartStatus'), {{
  type: 'doughnut',
  data: {{
    labels: {chart_labels_status},
    datasets: [{{
      data: {chart_data_status},
      backgroundColor: ['#4ade80','#f87171','#fbbf24'],
      borderWidth: 0
    }}]
  }},
  options: {{plugins:{{legend:{{position:'bottom'}}}}}}
}});

new Chart(document.getElementById('chartSlow'), {{
  type: 'bar',
  data: {{
    labels: {chart_labels_slow},
    datasets: [{{
      label: 'Duration (s)',
      data: {chart_data_slow},
      backgroundColor: '#38bdf8',
      borderRadius: 4,
      borderWidth: 0
    }}]
  }},
  options: {{
    indexAxis: 'y',
    plugins: {{legend: {{display: false}}}},
    scales: {{
      x: {{grid: {{color: '#334155'}}}},
      y: {{grid: {{color: '#334155'}}, ticks: {{font: {{size: 10}}}}}}
    }}
  }}
}});

new Chart(document.getElementById('chartLob'), {{
  type: 'bar',
  data: {{
    labels: {chart_labels_lob},
    datasets: [
      {{label: 'Passed', data: {chart_data_lob_pass}, backgroundColor: '#4ade80', borderRadius: 3, borderWidth: 0}},
      {{label: 'Failed', data: {chart_data_lob_fail}, backgroundColor: '#f87171', borderRadius: 3, borderWidth: 0}}
    ]
  }},
  options: {{
    plugins: {{legend: {{position: 'bottom'}}}},
    scales: {{
      x: {{stacked: true, grid: {{color: '#334155'}}}},
      y: {{stacked: true, grid: {{color: '#334155'}}}}
    }}
  }}
}});
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    records = load_metrics()
    html = generate_html(records)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"[METRICS] Dashboard written: {OUTPUT_FILE}  ({len(records)} records)")


if __name__ == "__main__":
    main()
