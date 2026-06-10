# SandboxPlaywrightMCP

A BDD-driven end-to-end test automation framework for the **OneShield** insurance platform, with an AI-powered policy flow generator, underwriting rules validator, and a React dashboard — all wired together via MCP (Model Context Protocol) tool servers.

---

## What This Is

This framework has two distinct layers that share a single Python environment:

1. **Playwright Test Suite** — BDD tests written in Gherkin, executed with `pytest-bdd` + Playwright against the OneShield application.
2. **MCP Tools Layer** — AI-powered MCP servers that generate test scenarios, validate underwriting rules, record new test flows, audit forms, and check accessibility — callable from Claude Code or the dashboard.

A **React + FastAPI dashboard** wraps the MCP tools as a web UI with async job tracking.

---

## Lines of Business (LOBs)

Tests exist for the following insurance lines:

| LOB | Marker |
|-----|--------|
| Personal Auto | `auto` |
| Homeowner | `homeowner` |
| Cyber | `cyber` |
| General Liability | `gl` |
| Underwriting Rules | `uw` |

---

## Project Structure

```
SandboxPlaywrightMCP/
├── ui/
│   ├── features/          # Gherkin .feature files (one subdirectory per LOB)
│   ├── pages/             # Page objects (common/, auto/, cyber/, homeowner/, gl/)
│   ├── steps/             # Step definitions (common/ + per-LOB files)
│   ├── tests/             # Thin pytest-bdd @scenario entry points
│   └── fixtures.py        # All page object @pytest.fixture definitions
├── mcp_tools/             # MCP server implementations
│   ├── policy_flow_generator/   # Multi-LOB persona + full policy flows
│   ├── uw_rules_validator/      # Underwriting edge-case registry
│   ├── smart_assertions/        # AI-based assertion helpers
│   └── local_inference/         # Local model inference utilities
├── testdata/
│   ├── static/            # JSON test data files per LOB
│   ├── factories/         # Data factory helpers
│   └── user_stories/      # User story references
├── dashboard/
│   ├── backend/           # FastAPI backend (main.py) — http://localhost:8000
│   └── frontend/          # React 18 + Vite + Tailwind — http://localhost:5173
├── utils/                 # Logger, data readers, email generator, CSV writer
├── api_tests/             # API-level test suite
├── tools/                 # Scaffolding and utility scripts
├── conftest.py            # Browser/context/page fixtures + pytest_plugins registry
├── pytest.ini             # Pytest + Playwright configuration
└── requirements.txt       # Python dependencies
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+ (for the dashboard frontend)
- Playwright browsers installed

### 1. Clone and set up

```bash
git clone <repo-url>
cd SandboxPlaywrightMCP
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
playwright install
```

### 2. Configure credentials

Create a `.env` file in the project root (never commit this):

```env
PARTNER_NUM=0
USERNAMEE=your_username   # double-E is intentional — avoids Windows USERNAME clash
PASSWORD=your_password
OPENAI_API_KEY=sk-...     # or ANTHROPIC_API_KEY for Anthropic models
```

### 3. Run the tests

```bash
# All tests (headed browser, default)
pytest

# Headless
pytest --headed=false

# By LOB
pytest -m auto
pytest -m homeowner
pytest -m cyber
pytest -m uw

# Single test file
pytest ui/tests/test_cyber.py -v

# Single scenario
pytest "ui/tests/test_cyber.py::test_cyber_workflow[TC_ID_0001]" --headed -s

# Parallel (4 workers)
pytest -m auto -n 4

# With Playwright trace (saved to reports/traces/)
pytest --pw-trace=on
```

### 4. View reports

```bash
# HTML report — auto-generated at reports/pytest_report.html
open reports/pytest_report.html

# Allure report
allure serve allure-results
```

### 5. Run the dashboard

```bash
# Backend (from project root)
python dashboard/backend/main.py      # http://localhost:8000

# Frontend (from dashboard/frontend/)
npm run dev                           # http://localhost:5173
```

---

## Architecture

### Playwright Test Layer

Tests follow the BDD pipeline:

```
Feature File (.feature)
    ↓ parsed by pytest-bdd
Step Definitions (ui/steps/)
    ↓ fixtures injected via DI
Page Objects (ui/pages/)
    ↓ extend BasePage
Playwright Sync API → Browser → OneShield
```

**Fixture lifecycle:**
```
Session: log, playwright, browser
  └── Per-test: context → page → [page objects] → test_data
```

All page object fixtures live in `ui/fixtures.py`. Browser/context/page fixtures are in root `conftest.py`.

**BasePage smart wrappers** handle ExtJS quirks automatically:

| Method | Purpose |
|--------|---------|
| `smart_click(locator)` | Visibility + enabled check, retry, DOM metadata on failure |
| `smart_fill(locator, value)` | Clear → fill → verify |
| `smart_type(locator, value)` | Character-by-character for JS event listeners |
| `answer_question(group, answer)` | ExtJS radio groups via `dispatch_event("click")` |
| `spinner_wait(selector)` | Waits for loading mask to clear |
| `read_summary(label)` | Reads display-only fields by label |

### MCP Tools Layer

Four MCP servers extend Claude with insurance-domain AI capabilities (registered in `.mcp.json`):

| Server | Purpose |
|--------|---------|
| `policy-flow-generator` | Generates persona → runs full multi-LOB policy flow in browser |
| `uw-rules-validator` | Pre-defined edge-case registry + boundary testing |
| `smart-assertions` | AI-based assertion helpers for complex UI state |
| `local-inference` | Local model inference via Ollama (`oneshield-qwen3`) |

**policy-flow-generator** is the primary multi-LOB tool:
1. `generate_persona(lob, description)` — calls AI to produce a JSON persona
2. `flow_runner.run_flow(lob, persona)` — launches browser, routes to LOB-specific runner
3. `result_formatter` — produces a Markdown report

### React Dashboard

FastAPI backend + React SPA wrapping the MCP tools:

- **Backend** (`dashboard/backend/main.py`) — async job dispatch via `BackgroundTasks`, job store with threading lock, endpoints under `/api/policy/` and `/api/uw/`, jobs polled every 2.5s.
- **Frontend** — `PolicyPanel` (policy flow generator) and `UWPanel` (underwriting validator). Results display in a `ReportModal`.

---

## AI Provider Configuration

`persona_generator.py` selects the AI provider at runtime:

1. Set `AI_PROVIDER=openai` or `AI_PROVIDER=anthropic` in `.env` to force a provider
2. Falls back to `ANTHROPIC_API_KEY` → Anthropic (`claude-opus-4-6`)
3. Falls back to `OPENAI_API_KEY` → OpenAI (`gpt-4o`)

> **Windows note:** A stale `ANTHROPIC_API_KEY` in the Windows system environment will shadow `.env` even with `load_dotenv(override=True)`. The dashboard backend actively removes it on startup if not present in `.env`. Restart the backend after any `.env` changes. On startup it logs `[INFO] AI provider: openai` or `[INFO] AI provider: anthropic` to confirm which key is active.

---

## Test Data

Each LOB has a JSON data file in `testdata/static/`. Every file must include:

| Field | Format |
|-------|--------|
| `FirstName`, `LastName` | string |
| `DOB` | `MM/DD/YYYY` |
| `Email` | `name_{timestamp}@domain.com` for uniqueness |
| `PhoneNum` | `555-123-4567` |
| `CustomerType` | e.g. `"Individual"` |
| `ZIP`, `Address`, `City` | string |
| `Producer` | string |
| `Program` | exact dropdown option text |
| `EffectiveDate` | `MM/DD/YYYY` (omit to default to tomorrow) |
| `PaymentPlan` | e.g. `"Pay In Full"` |

---

## Adding a New LOB

Use the `lob-recorder` MCP server to auto-generate the scaffold (`start_recording` → interact → `scan_page` per page → `generate_scaffold_files`), or create manually:

1. **Page objects** — `ui/pages/<lob>/` extending `BasePage`
2. **Feature file** — `ui/features/<lob>/<lob>_creation.feature`
3. **Step definitions** — `ui/steps/<lob>_steps.py`
4. **Test entry point** — `ui/tests/test_<lob>.py` with `@scenario`
5. **Test data** — `testdata/static/<Lob>Data.json`
6. Register step module in `conftest.py:pytest_plugins`
7. Register page fixtures in `ui/fixtures.py`

---

## Docker

```bash
# Build and run
docker-compose up --build

# Windows-specific compose
docker-compose -f docker-compose.windows.yml up
```

See `DOCKER_GUIDE.md` for full details.

---

## Code Quality

```bash
flake8 .
```

---

## Security

See `SECURITY.md` for the security policy and responsible disclosure process.

---

## Related Docs

| File | Contents |
|------|---------|
| `CLAUDE.md` | Detailed guidance for AI coding agents working in this repo |
| `FRAMEWORK_GUIDE.md` | In-depth framework patterns and examples |
| `MCP_TOOLS_OVERVIEW.md` | MCP server reference |
| `DOCKER_GUIDE.md` | Docker setup and deployment |
| `DASHBOARD_DIRECT_ASSERT_GUIDE.md` | Direct assertion patterns for the dashboard |
