# Playwright Automation Framework Guide

**Last updated:** June 15, 2026
**Status:** Active

This project is a QA automation framework for the OneShield insurance application. It has three main surfaces:

1. A Playwright plus `pytest-bdd` test suite under `ui/` and `api_tests/`.
2. AI and MCP-style automation tools under `mcp_tools/`.
3. A React plus FastAPI dashboard under `dashboard/` that runs those tools as background jobs and stores history in SQLite.

Use this guide when you are adding or debugging tests. For a deeper system map, read `TECHNICAL_OVERVIEW.md`.

---

## 1. What This Project Does

The framework automates insurance policy workflows in OneShield:

| Area | What it does | Main files |
|---|---|---|
| UI tests | Runs browser tests through OneShield pages using Playwright | `ui/features/`, `ui/steps/`, `ui/pages/`, `ui/tests/` |
| API and replay tests | Replays captured OneShield API flows and checks business assertions | `api_tests/`, `dashboard/backend/api_assertions/` |
| AI persona generation | Turns plain English risk descriptions into structured test data | `mcp_tools/policy_flow_generator/persona_generator.py` |
| Policy flow runner | Opens a browser and runs an AI/static persona through Auto or Homeowner flows | `mcp_tools/policy_flow_generator/flow_runner.py` |
| Underwriting validation | Runs known edge cases and validates expected UW outcomes | `mcp_tools/uw_rules_validator/` |
| Dashboard | Web UI for jobs, reports, chat, policy flows, and validation tests | `dashboard/backend/main.py`, `dashboard/frontend/src/` |
| Reports | Produces Allure, pytest HTML, policy CSV, screenshots, metrics dashboard, and dashboard job reports | `allure-results/`, `reports/`, `utils/metrics_collector.py` |

Current UI test LOBs:

| LOB | Marker | Key folders/files |
|---|---|---|
| Personal Auto | `auto` | `ui/features/auto/`, `ui/pages/auto/`, `ui/steps/auto/auto_workflow_steps.py` |
| Homeowner | `homeowner` | `ui/features/homeowner/`, `ui/pages/homeowner/`, `ui/steps/homeowner_steps.py` |
| Cyber | `cyber` | `ui/features/cyber/`, `ui/pages/cyber/`, `ui/steps/cyber_steps.py` |
| General Liability | `gl` | `ui/features/gl/`, `ui/pages/gl/`, `ui/steps/gl_steps.py` |
| Underwriting rules | `uw`, `uw_rules` | `ui/tests/auto_uw_rules/`, `mcp_tools/uw_rules_validator/` |

---

## 2. Repository Map

```text
sendbox-playwright/
  conftest.py                         Global pytest fixtures, CLI options, screenshots, metrics
  pytest.ini                          Test discovery, markers, default reports, default browser
  requirements.txt                    Python test and dashboard dependencies
  README.md                           Quick project summary
  FRAMEWORK_GUIDE.md                  This testing guide
  TECHNICAL_OVERVIEW.md               Architecture and system flow guide

  ui/
    features/                         Gherkin feature files by LOB
    steps/                            pytest-bdd step definitions
    pages/                            Page Object Model classes
    tests/                            Thin pytest scenario entry points
    fixtures.py                       Page object fixture registration

  api_tests/
    conftest.py                       API test options and OneShield API session fixture
    oneshield_api_replay.py           Browserless replay client for captured Auto API flow
    rating_assertions.py              Rating assertion helpers
    test_*.py                         API and premium extraction tests

  mcp_tools/
    policy_flow_generator/            AI persona and policy flow tools
    uw_rules_validator/               UW rule registry, validation, and reports
    smart_assertions/                 AI-assisted assertion helpers
    local_inference/                  Local Ollama inference MCP server

  dashboard/
    backend/
      main.py                         FastAPI app and job endpoints
      auth.py                         Login/register/session routes
      dashboard_db.py                 SQLite tables and persistence helpers
      job_store.py                    In-memory plus persisted job state
      chat/                           Chat router, intent parser, provider, tool registry
      api_assertions/                 Plain-English assertion parsing and execution
    frontend/
      src/App.jsx                     React routes, auth shell, job polling, chat sidebar
      src/utils/api.js                Frontend API client
      src/components/                 Dashboard panels and report rendering

  testdata/
    static/auto/AutoData.json
    static/homeowner/HomeData.json
    static/cyber/CyberData.json
    static/gl/GLData.json
    user_stories/auto_user_stories.json

  reports/
    pytest_report.html                pytest-html output
    screenshots/                      Flow failure screenshots
    metrics/execution_metrics.jsonl   JSONL metrics from pytest hooks
    metrics/automation_dashboard.html Generated metrics dashboard

  allure-results/                     Raw Allure result files
  allure-report/                      Generated Allure static site
  logs/                               Runtime logs
  tools/                              Discovery, probing, and scaffolding utilities
  scripts/generate_metrics_dashboard.py
```

---

## 3. Technology Stack

| Layer | Technology | Where used |
|---|---|---|
| Browser automation | `playwright` sync API | `conftest.py`, `ui/pages/`, `mcp_tools/policy_flow_generator/` |
| Test runner | `pytest` | Root test execution |
| BDD | `pytest-bdd` | `.feature` files and `ui/steps/` |
| Reporting | `allure-pytest`, `pytest-html` | `pytest.ini`, `conftest.py` |
| API tests | `requests` | `api_tests/` |
| Dashboard backend | FastAPI | `dashboard/backend/main.py` |
| Dashboard frontend | React 18, Vite, Tailwind, lucide-react | `dashboard/frontend/` |
| Database | SQLite | `dashboard/backend/dashboard_db.py` |
| AI providers | OpenAI, Anthropic, DeepSeek, Ollama depending on module/env | `mcp_tools/policy_flow_generator/persona_generator.py`, `dashboard/backend/chat/llm_provider.py` |
| MCP servers | Python modules launched from `.mcp.json` | `mcp_tools/*/server.py` |

---

## 4. Setup

### Prerequisites

- Python 3.10+
- Node.js 18+ for the dashboard frontend
- Playwright browser binaries
- Allure CLI if you want local Allure HTML reports

### Python setup

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
playwright install
```

### Frontend setup

```powershell
cd dashboard/frontend
npm install
```

### Environment variables

Create `.env` in the project root. It is intentionally git-ignored.

```env
ENV=sandbox
PARTNER_NUM=0
USERNAMEE=your_oneshield_username
PASSWORD=your_oneshield_password
OPENAI_API_KEY=sk-...
AI_PROVIDER=openai
DASHBOARD_DB_PATH=dashboard/backend/data/dashboard.db
```

Important notes:

- `USERNAMEE` has a double `E` to avoid conflict with the Windows `USERNAME` environment variable.
- `dashboard/backend/main.py` loads `.env` before importing AI tools.
- If `OPENAI_API_KEY` exists in `.env`, the backend sets `AI_PROVIDER=openai` unless `AI_PROVIDER` is already set.
- If `ANTHROPIC_API_KEY` is not in `.env`, the backend removes a stale process-level `ANTHROPIC_API_KEY` so Windows system variables do not accidentally win.

---

## 5. Running Tests

The defaults in `pytest.ini` are verbose, headed Chromium, `--slow-mo=50`, `reports/pytest_report.html`, and `allure-results/`.

```powershell
# Run everything
pytest

# Run by marker
pytest -m auto
pytest -m homeowner
pytest -m cyber
pytest -m gl
pytest -m uw
pytest -m api

# Run one file
pytest ui/tests/test_auto_workflow.py -v

# Run one scenario function
pytest ui/tests/test_auto_workflow.py::test_personal_auto_workflow -v

# Useful debugging options
pytest -m auto --headed --slow-mo=150
pytest -m auto --pw-trace=on
pytest ui/tests/test_login.py --browser=chrome
pytest ui/tests/test_login.py --browser=msedge
```

Custom pytest options are registered in `conftest.py`:

| Option | Purpose |
|---|---|
| `--env` | Target environment label. CLI wins over `ENV` in `.env`; default is `sandbox`. |
| `--browser` | `chromium`, `firefox`, `webkit`, `chrome`, or `msedge`. |
| `--headed` | Shows the browser. |
| `--slow-mo` | Adds delay to browser actions. |
| `--pw-trace` | `on` saves Playwright traces to `reports/traces/`. |
| `--api-flow-map` | Writes captured UI network traffic to a JSON file through `utils/api_flow_recorder.py`. |
| `--api-flow-include-static` | Includes static resources in the API flow map. |
| `--update-premium-baselines` | Updates premium baselines instead of asserting them. |

---

## 6. UI Test Architecture

UI tests follow this flow:

```text
ui/features/<lob>/*.feature
  -> parsed by pytest-bdd
ui/tests/test_<lob>.py
  -> declares @scenario entry points
ui/steps/<lob>_steps.py
  -> maps Gherkin text to Python functions
ui/fixtures.py
  -> injects page object fixtures
ui/pages/<lob>/*.py
  -> performs Playwright interactions through BasePage helpers
conftest.py
  -> creates browser, context, page, logging, screenshots, metrics
```

Example entry point pattern:

```python
from pytest_bdd import scenario

@scenario("../features/auto/personal_auto.feature", "Create a new personal auto policy")
def test_personal_auto_workflow():
    pass
```

The function body is empty because the step definitions do the work.

### Fixture lifecycle

```text
Session:
  log
  playwright
  browser

Each test:
  context
  page
  api_flow_recorder
  page object fixtures from ui/fixtures.py
  test_data from ui/steps/common/data_steps.py
```

`conftest.py` registers these step modules through `pytest_plugins`:

```python
pytest_plugins = [
    "ui.fixtures",
    "ui.steps.common.auth_steps",
    "ui.steps.common.login_validation_steps",
    "ui.steps.common.data_steps",
    "ui.steps.common.field_steps",
    "ui.steps.auto.auto_workflow_steps",
    "ui.steps.homeowner_steps",
    "ui.steps.cyber_steps",
    "ui.steps.gl_steps",
    "ui.steps.common.customer_validation_steps",
]
```

If you create a new step module, add it here or pytest-bdd will not find the steps.

---

## 7. Page Objects and BasePage

All page objects should inherit from `ui/pages/common/base_page.py`.

Important `BasePage` helpers:

| Method | Use it for |
|---|---|
| `smart_click(target)` | Clicks with visibility, enabled, stability, retry, and Allure metadata on failure. |
| `smart_fill(target, value)` | Fills inputs with checks and optional verification. |
| `smart_type(target, value)` | Types character by character for ExtJS or JS-listener fields. |
| `answer_question(group_name, answer)` | Selects radio answers inside OneShield radiogroups. |
| `read_summary(label_text)` | Reads display fields such as Policy Number and Total Policy Premium. |
| `spinner_wait(selector)` | Waits for a loading spinner or mask to disappear. |
| `wait_for_app_ready()` | Waits for common OneShield loading masks. |
| `select_extjs_option(locator, value)` | Selects exact visible text from ExtJS dropdown lists. |
| `collect_extjs_options(locator)` | Discovers visible ExtJS dropdown options. |
| `with_optional_oneshield_response(action)` | Runs an action and observes a matching OneShield network response if one occurs. |

When a smart wrapper fails, `_capture_failure_metadata()` attaches selector, DOM state, attributes, computed style, and bounding box information to Allure.

Page object examples:

| Flow area | File | Important method |
|---|---|---|
| Login | `ui/pages/common/login_page.py` | `fill_credentials_from_env()` |
| New Quote | `ui/pages/common/new_quote_page.py` | `new_quote_steps()` |
| Customer | `ui/pages/common/customer_page.py` | `customer_steps(data)` |
| Quote Registration | `ui/pages/common/quote_registration_page.py` | `quote_registration_steps(data)` |
| Auto Quote Summary | `ui/pages/auto/quote_summary_page.py` | `summary_steps(data)` |
| Auto Driver | `ui/pages/auto/driver_info_page.py` | `fill_driver_info(data)` |
| Auto Vehicle | `ui/pages/auto/vehicle_info_page.py` | `fill_vehicle_info(data)` |
| Auto Policy Term | `ui/pages/auto/policy_term_page.py` | `policy_term_steps(data)` |
| UW Referral | `ui/pages/auto/uw_referral_page.py` | `is_visible()`, `capture_conditions()`, `override_all_and_accept()` |
| Policy Summary | `ui/pages/common/policy_summary_page.py` | `extract_details(test_data)`, `save_lob_report(details)` |

---

## 8. Test Data

Primary test data is JSON under `testdata/static/`.

| LOB | File |
|---|---|
| Personal Auto | `testdata/static/auto/AutoData.json` |
| Auto discovery | `testdata/static/auto/AutoDiscoveryData.json` |
| Auto UW rules | `testdata/static/auto/AutoUWRulesData.json` |
| Homeowner | `testdata/static/homeowner/HomeData.json` |
| Homeowner UW rules | `testdata/static/homeowner/HomeownerUWRulesData.json` |
| Homeowner dropdowns | `testdata/static/homeowner/HomeownerDropdownOptionsData.json` |
| Cyber | `testdata/static/cyber/CyberData.json` |
| Cyber discovery | `testdata/static/cyber/CyberDiscoveryData.json` |
| Cyber optional fields | `testdata/static/cyber/CyberOptionalData.json` |
| General Liability | `testdata/static/gl/GLData.json` |

`ui/steps/common/data_steps.py` loads data through these step definitions:

```gherkin
Given the data is loaded "testdata/static/auto/AutoData.json", "TC_ID_0001"
Given the data is loaded "testdata/static/auto/AutoData.xlsx", "Sheet1", "TC_ID_0001"
```

The loader returns one row as the `test_data` fixture. The row is selected by `TC_ID`.

Data conventions:

- Keep field names aligned with page object expectations, for example `TC_ID`, `FirstName`, `LastName`, `DOB`, `Email`, `ZIP`, `Producer`, `Program`, `PolicyCoverage`.
- Keep values as strings when leading zeros or exact dropdown text matter.
- Use `{timestamp}` in emails when a unique value is needed.
- Prefer JSON for new data. Excel is legacy and handled through `utils/excel_reader.py`.

---

## 9. Main UI Flows

### Personal Auto BDD flow

Feature and test entry files:

- `ui/features/auto/personal_auto.feature`
- `ui/features/auto/auto_uw_rules.feature`
- `ui/tests/test_auto_workflow.py`
- `ui/tests/auto_uw_rules/test_auto_uw_rules.py`

Step functions live in `ui/steps/auto/auto_workflow_steps.py`.

Typical flow:

```text
Login
  -> New Quote
  -> Customer
  -> Quote Registration
  -> Quote Summary
  -> Driver Details
  -> Vehicle Details
  -> Policy Term / Coverage and Rate
  -> optional UW Referral handling
  -> Contact Information if needed
  -> Request Issue
  -> Delivery Preferences
  -> Billing Plan
  -> Bind
  -> Policy Summary extraction
```

Important step functions:

- `create_new_quote()`
- `create_new_customer()`
- `provide_quote_registration()`
- `provide_quote_summary()`
- `provide_driver_details()`
- `provide_vehicle_details()`
- `provide_policy_term_details()`
- `assert_uw_referral_condition()`
- `override_all_uw_conditions()`
- `read_extract_summary()`

### Homeowner BDD flow

Feature and test files:

- `ui/features/homeowner/homeowner_creation.feature`
- `ui/features/homeowner/homeowner_uw_rules.feature`
- `ui/features/homeowner/homeowner_additional_elements.feature`
- `ui/tests/test_homeowner.py`
- `ui/tests/test_homeowner_uw_rules.py`
- `ui/tests/test_homeowner_additional_elements.py`

Step functions live in `ui/steps/homeowner_steps.py`.

Typical flow:

```text
Login
  -> New Quote
  -> Customer
  -> Quote Registration
  -> Homeowner Quote Summary
  -> City Information
  -> Coverage
  -> Bind Information
  -> Rate Quote
  -> optional UW Referral
  -> Delivery Preferences
  -> Billing Plan
  -> Verify Billing
  -> Policy Summary
```

### Cyber and General Liability flows

Cyber:

- Feature: `ui/features/cyber/cyber_creation.feature`
- Test: `ui/tests/test_cyber.py`
- Steps: `ui/steps/cyber_steps.py`
- Pages: `ui/pages/cyber/`

General Liability:

- Feature: `ui/features/gl/gl_creation.feature`
- Test: `ui/tests/test_gl.py`
- Steps: `ui/steps/gl_steps.py`
- Pages: `ui/pages/gl/`

---

## 10. MCP and AI Tools

MCP server configuration is in `.mcp.json`. The configured server names are:

| Server | Module | Purpose |
|---|---|---|
| `policy-flow-generator` | `mcp_tools.policy_flow_generator.server` | Generate personas and run Auto/Homeowner flows. |
| `uw-rules-validator` | `mcp_tools.uw_rules_validator.server` | Run registered underwriting rule cases and audits. |
| `smart-assertions` | `mcp_tools.smart_assertions.server` | AI-assisted assertion helpers. |
| `local-inference` | `mcp_tools.local_inference.server` | Local Ollama model calls with `OLLAMA_MODEL=oneshield-qwen3`. |

If you move this repo, check `.mcp.json`: it contains absolute paths in the current file.

### Policy flow generator

Main files:

- `mcp_tools/policy_flow_generator/persona_generator.py`
- `mcp_tools/policy_flow_generator/flow_runner.py`
- `mcp_tools/policy_flow_generator/runners/auto_runner.py`
- `mcp_tools/policy_flow_generator/runners/homeowner_runner.py`
- `mcp_tools/policy_flow_generator/result_formatter.py`
- `mcp_tools/policy_flow_generator/business_reports.py`

Important functions:

| Function | What it does |
|---|---|
| `generate_persona(lob, description)` | Calls AI and returns a persona JSON string. |
| `generate_persona_variations(lob, base_description, count)` | Creates multiple AI personas. |
| `generate_batch_personas(scenarios)` | Generates personas for a list of scenarios. |
| `run_flow(lob, persona, progress_callback=None, job_id=None)` | Launches Playwright and routes to the LOB runner. |
| `run_auto_flow(page, persona, steps, progress_callback=None)` | Executes Personal Auto browser flow. |
| `run_homeowner_flow(page, persona, steps, progress_callback=None)` | Executes Homeowner browser flow. |
| `format_result(result)` | Converts a flow result dict into Markdown for reports. |
| `format_batch_summary(results)` | Creates a batch Markdown summary. |

`flow_runner.py` currently supports `auto` and `homeowner` through `_LOB_RUNNERS`.

### Underwriting validator

Main files:

- `mcp_tools/uw_rules_validator/rule_registry.py`
- `mcp_tools/uw_rules_validator/validator.py`
- `mcp_tools/uw_rules_validator/report_formatter.py`
- `mcp_tools/uw_rules_validator/server.py`

Important functions:

| Function | File | What it does |
|---|---|---|
| `validate_case(case, result)` | `validator.py` | Compares expected UW outcome and conditions to the actual flow result. |
| `format_audit_report(...)` | `report_formatter.py` | Builds Markdown audit reports. |
| `format_boundary_report(...)` | `report_formatter.py` | Builds Markdown for one custom boundary test. |
| `run_uw_audit(lob)` | `server.py` | MCP tool for all registered cases in one LOB. |
| `run_rule_cases(lob, rule_id)` | `server.py` | MCP tool for a single rule. |
| `run_full_audit()` | `server.py` | MCP tool across all supported LOBs. |

---

## 11. Dashboard

Run the backend:

```powershell
python dashboard/backend/main.py
```

Backend URL: `http://localhost:8000`

Run the frontend:

```powershell
cd dashboard/frontend
npm run dev
```

Frontend URL: `http://localhost:5173`

### Backend files

| File | Responsibility |
|---|---|
| `dashboard/backend/main.py` | FastAPI app, CORS, auth middleware, static Allure/screenshots, job endpoints, policy endpoints, UW endpoints, API assertion endpoints. |
| `dashboard/backend/auth.py` | `/api/register`, `/api/login`, `/api/auth/login`, `/api/auth/me`, `/api/auth/logout`. |
| `dashboard/backend/dashboard_db.py` | SQLite connection, table creation, users, sessions, executions, saved suites, assertion results, chat sessions/messages. |
| `dashboard/backend/job_store.py` | Creates, updates, completes, fails, cancels, lists, and deletes jobs. Persists jobs through `dashboard_db.py`. |
| `dashboard/backend/chat/chat_router.py` | Chat endpoints, streaming ask endpoint, tool dispatch into background jobs. |
| `dashboard/backend/chat/tool_registry.py` | Whitelisted chat tools and parameter validation. |
| `dashboard/backend/api_assertions/` | Plain-English parser, assertion engine, comparative tests, ladder tests, regression sweep, snapshot cache. |

### Frontend files

| File | Responsibility |
|---|---|
| `dashboard/frontend/src/App.jsx` | Top-level routes, auth gate, nav, job polling every 2.5 seconds, chat sidebar, report modal. |
| `dashboard/frontend/src/utils/api.js` | All frontend API calls. |
| `dashboard/frontend/src/components/OverviewPanel.jsx` | Dashboard summary and live activity feed. |
| `dashboard/frontend/src/components/PolicyPanel.jsx` | Quick policy test, build customer profile, run policy journey. |
| `dashboard/frontend/src/components/ApiAssertionsPanel.jsx` | Regression sweep, direct assert flow, assertion history. |
| `dashboard/frontend/src/components/JobsPanel.jsx` | Job history, cancel, rerun, delete. |
| `dashboard/frontend/src/components/ChatPanel.jsx` | Ask mode, tool mode, sessions, streaming responses. |
| `dashboard/frontend/src/components/ReportModal.jsx` | Markdown and structured report rendering. |

### Key backend endpoints

Health and auth:

- `GET /api/health`
- `GET /api/config`
- `POST /api/register`
- `POST /api/login`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`

Jobs:

- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `DELETE /api/jobs/{job_id}`
- `POST /api/jobs/{job_id}/cancel`
- `POST /api/jobs/{job_id}/rerun`

Policy flows:

- `GET /api/policy/archetypes`
- `POST /api/policy/create-persona`
- `POST /api/policy/run-flow`
- `POST /api/policy/quick-run`
- `POST /api/policy/batch-run`

API assertions and validation:

- `POST /api/api-tests/plain-assert`
- `POST /api/api-tests/compare`
- `POST /api/api-tests/ladder`
- `POST /api/api-tests/ai-assert`
- `POST /api/api-tests/assert-flow`
- `POST /api/api-tests/regression-sweep`
- `GET /api/api-tests/results`
- `DELETE /api/api-tests/results/{result_id}`
- `POST /api/api-tests/explain`
- `GET /api/api-tests/snapshot/{run_id}`

Underwriting:

- `GET /api/uw/rules`
- `POST /api/uw/audit`
- `POST /api/uw/rule-cases`
- `POST /api/uw/custom-boundary`
- `POST /api/uw/full-audit`

Chat:

- `GET /api/chat/greeting`
- `GET /api/chat/provider`
- `GET /api/chat/sessions`
- `POST /api/chat/sessions`
- `GET /api/chat/sessions/{session_id}`
- `DELETE /api/chat/sessions/{session_id}`
- `POST /api/chat/ask`
- `POST /api/chat/ask/stream`
- `POST /api/chat/message`

---

## 12. Jobs and Database

The dashboard job flow is:

```text
Frontend component
  -> dashboard/frontend/src/utils/api.js
  -> FastAPI endpoint in dashboard/backend/main.py
  -> job_store.new_job(...)
  -> dashboard_db.create_execution(...)
  -> FastAPI BackgroundTasks runs automation
  -> job_store.update_job_status(...) while running
  -> job_store.complete_job(...) or fail_job(...)
  -> dashboard_db.finish_execution(...)
  -> App.jsx polls GET /api/jobs/{job_id}
  -> ReportModal.jsx renders result
```

`dashboard/backend/dashboard_db.py` owns the actual SQLite schema. Default database path is:

```text
dashboard/backend/data/dashboard.db
```

You can override it with `DASHBOARD_DB_PATH`.

Tables created by `init_db()`:

| Table | Purpose |
|---|---|
| `users` | Dashboard accounts. First registered user becomes admin. |
| `sessions` | Hashed session tokens for the `dashboard_session` cookie. |
| `executions` | Job history, status, logs, result Markdown/JSON, metadata. |
| `saved_suites` | Saved prompt suites. |
| `assertion_results` | Validation history for direct asserts and sweeps. |
| `chat_sessions` | Chat session headers. |
| `chat_messages` | Stored chat messages. |

`dashboard/backend/database.py` defines a SQLAlchemy engine, but the active dashboard persistence path is the plain SQLite helper in `dashboard/backend/dashboard_db.py`.

---

## 13. Reports and Artifacts

| Artifact | Location | How it is produced |
|---|---|---|
| pytest HTML | `reports/pytest_report.html` | `pytest.ini` addopts |
| Allure raw data | `allure-results/` | `pytest.ini` addopts |
| Allure static site | `allure-report/` | `/api/allure/generate` or Allure CLI |
| Playwright traces | `reports/traces/` | `--pw-trace=on` |
| Flow screenshots | `reports/screenshots/` | `flow_runner.py` and LOB runners on failures |
| Failure screenshots in Allure | Allure attachments | `pytest_runtest_makereport()` in `conftest.py` |
| Policy summary CSV | `reports/` subpaths from `utils/file_writer.py` | `PolicySummary.save_lob_report()` |
| Metrics JSONL | `reports/metrics/execution_metrics.jsonl` | `utils/metrics_collector.write_metric()` from pytest hook |
| Metrics HTML | `reports/metrics/automation_dashboard.html` | `scripts/generate_metrics_dashboard.py` at pytest session finish |
| Dashboard job reports | SQLite `executions.result` | `job_store.complete_job()` |

Allure can be viewed with:

```powershell
allure serve allure-results
```

The dashboard can generate and serve the static Allure report through:

- `GET /api/allure/status`
- `POST /api/allure/generate`
- Static site: `http://localhost:8000/allure/`

---

## 14. Adding a New UI Feature

Use this path when adding normal BDD browser coverage.

1. Add or update test data in `testdata/static/<lob>/`.
2. Add or update a feature in `ui/features/<lob>/`.
3. Add a scenario entry point in `ui/tests/test_<lob>.py`.
4. Add step functions in `ui/steps/<lob>_steps.py` or a new step file.
5. If you create a new step file, register it in `conftest.py` under `pytest_plugins`.
6. Add or update page objects under `ui/pages/<lob>/` or `ui/pages/common/`.
7. Register new page object fixtures in `ui/fixtures.py`.
8. Run the smallest relevant test first, then the marker group.

Example command:

```powershell
pytest ui/tests/test_gl.py -v --headed --slow-mo=150
pytest -m gl
```

Where to change things:

| Change needed | Go to |
|---|---|
| New screen interaction | `ui/pages/<lob>/<page>_page.py` |
| New Gherkin phrase | `ui/steps/<lob>_steps.py` |
| New scenario | `ui/features/<lob>/*.feature` and `ui/tests/test_<lob>.py` |
| New reusable fixture | `ui/fixtures.py` |
| New CLI option or fixture lifecycle | `conftest.py` |
| New marker | `pytest.ini` |
| New static data | `testdata/static/<lob>/` |

---

## 15. Adding a New Dashboard Feature

Use this path when the feature is visible in the React dashboard.

1. Add backend request/response logic in `dashboard/backend/main.py`, or a small helper module if the logic is large.
2. If it is long-running, create a job with `_new_job(...)`, schedule work with `BackgroundTasks`, and finish with `_done(jid, result)` or `_fail(jid, error)`.
3. Persist history in `dashboard/backend/dashboard_db.py` if the result must survive restart.
4. Add frontend API wrapper in `dashboard/frontend/src/utils/api.js`.
5. Add or update the panel component under `dashboard/frontend/src/components/`.
6. If it creates a report, make sure `ReportModal.jsx` can render the returned Markdown or JSON shape.
7. If jobs need rerun support, update the rerun logic around `POST /api/jobs/{job_id}/rerun` in `dashboard/backend/main.py`.

Where to change things:

| Change needed | Go to |
|---|---|
| New endpoint | `dashboard/backend/main.py` |
| New auth/session behavior | `dashboard/backend/auth.py` and `dashboard/backend/dashboard_db.py` |
| New persisted table or column | `dashboard/backend/dashboard_db.py` |
| New job lifecycle behavior | `dashboard/backend/job_store.py` |
| New API call from React | `dashboard/frontend/src/utils/api.js` |
| New page route | `dashboard/frontend/src/App.jsx` |
| New UI panel | `dashboard/frontend/src/components/` |
| New report parser/view | `dashboard/frontend/src/components/ReportModal.jsx` |
| New chat tool | `dashboard/backend/chat/tool_registry.py` and dispatch in `dashboard/backend/chat/chat_router.py` |

---

## 16. Adding a New AI or MCP Flow

Use this path when adding a new natural-language or automated policy flow.

1. Add persona schema/prompt support in `mcp_tools/policy_flow_generator/persona_generator.py`.
2. Add the browser runner under `mcp_tools/policy_flow_generator/runners/`.
3. Register the runner in `_LOB_RUNNERS` inside `mcp_tools/policy_flow_generator/flow_runner.py`.
4. Add report formatting support in `mcp_tools/policy_flow_generator/result_formatter.py` if the result shape changes.
5. Add dashboard endpoints in `dashboard/backend/main.py`.
6. Add frontend support in `dashboard/frontend/src/components/PolicyPanel.jsx` and `dashboard/frontend/src/utils/api.js`.
7. If chat should run it, add a tool schema in `dashboard/backend/chat/tool_registry.py` and dispatch handling in `dashboard/backend/chat/chat_router.py`.
8. If it should be available as an MCP server tool, expose it in the relevant `mcp_tools/*/server.py`.

---

## 17. Adding a New Underwriting Rule

1. Add rule metadata and cases in `mcp_tools/uw_rules_validator/rule_registry.py`.
2. Make sure each case has a persona, expected outcome, and expected condition text.
3. Update `mcp_tools/uw_rules_validator/validator.py` only if the comparison rules need new behavior.
4. Update `mcp_tools/policy_flow_generator/result_formatter.py` if you want a known rule name shown in policy flow reports.
5. Run the rule from the dashboard with `POST /api/uw/rule-cases` or through the Validation Tests UI.

Useful files:

| File | Purpose |
|---|---|
| `rule_registry.py` | Source of registered rules and cases. |
| `validator.py` | Expected vs actual result comparison. |
| `report_formatter.py` | Markdown reports for audits and boundaries. |
| `ui/pages/auto/uw_referral_page.py` | Captures visible UW grid conditions. |

---

## 18. Troubleshooting

### Dashboard says backend is not reachable

Start the backend from the project root:

```powershell
python dashboard/backend/main.py
```

Then refresh the frontend at `http://localhost:5173`.

### Dashboard API returns 401

Most `/api/*` routes are protected by `dashboard_auth_middleware()` in `dashboard/backend/main.py`. Log in through the dashboard or call `POST /api/login` first. Public API paths include `/api/health`, `/api/config`, `/api/login`, `/api/register`, `/api/auth/login`, `/api/auth/me`, and `/api/auth/logout`.

### A job stays running

Check:

- `GET /api/jobs/{job_id}`
- `dashboard/backend/job_store.py`
- `dashboard/backend/dashboard_db.py`, table `executions`
- `logs/`

Cancel from the UI or call `POST /api/jobs/{job_id}/cancel`.

### A step is not found

Check that the step definition module is listed in `pytest_plugins` in `conftest.py`, and that the Gherkin text exactly matches the parser in `ui/steps/`.

### Test data is not found

Check that the feature file uses the right path and `TC_ID`, and that the JSON has a top-level `testCases` list. The lookup code is in `ui/steps/common/data_steps.py`.

### A dropdown option is flaky

Prefer `BasePage.select_extjs_option(locator, value)` over raw clicks. It waits for visible ExtJS bound list items, clicks exact text, closes floating dropdowns, and retries.

### Failure screenshot is missing

The pytest failure hook skips tests marked `api`. For UI tests, confirm the test uses the `page` fixture. Flow-runner screenshots are written separately under `reports/screenshots/`.

### Allure report does not show the latest run

Raw Allure files are in `allure-results/`. Regenerate static HTML:

```powershell
allure generate allure-results --clean -o allure-report
```

Or use the dashboard endpoint `POST /api/allure/generate`.

### Metrics dashboard has no data

Run pytest first. Metrics are written by `pytest_runtest_makereport()` in `conftest.py` to `reports/metrics/execution_metrics.jsonl`, then `scripts/generate_metrics_dashboard.py` creates `reports/metrics/automation_dashboard.html` at session finish.
