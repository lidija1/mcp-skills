# Technical Overview

**Last updated:** June 15, 2026
**Audience:** New QA engineers and automation contributors

This document explains how the frontend, backend, MCP/AI tools, Playwright, database, background jobs, and reports connect in this project.

For testing patterns and day-to-day commands, also read `FRAMEWORK_GUIDE.md`.

---

## 1. One Sentence Summary

This project automates OneShield insurance workflows with Playwright, lets QA engineers run those workflows from tests or a dashboard, uses AI to generate customer personas and assertions, and stores dashboard job/report history in SQLite.

---

## 2. Big Picture Architecture

```text
QA engineer
  |
  | uses either
  |
  +-- pytest CLI
  |     |
  |     +-- conftest.py
  |     +-- ui/features/*.feature
  |     +-- ui/steps/*.py
  |     +-- ui/pages/*.py
  |     +-- Playwright browser
  |     +-- OneShield
  |     +-- reports/allure-results/logs/metrics
  |
  +-- React dashboard
        |
        +-- dashboard/frontend/src/utils/api.js
        +-- FastAPI backend in dashboard/backend/main.py
        +-- job_store.py
        +-- dashboard_db.py SQLite
        +-- mcp_tools/* and api_assertions/*
        +-- Playwright browser or API replay
        +-- OneShield
        +-- dashboard job report
```

The same automation logic is reused in multiple ways:

- BDD tests call page objects directly through step definitions.
- Dashboard policy jobs call `mcp_tools/policy_flow_generator/flow_runner.py`, which also uses page objects.
- Dashboard API assertion jobs call `api_tests/oneshield_api_replay.py` and `dashboard/backend/api_assertions/`.
- Chat tools call the same dashboard backend endpoints or dispatch logic.

---

## 3. Main Runtime Modes

### A. Pytest mode

You run:

```powershell
pytest -m auto
```

Flow:

```text
pytest.ini
  -> conftest.py creates browser/context/page
  -> ui/tests/test_auto_workflow.py declares scenario
  -> ui/features/auto/personal_auto.feature supplies Gherkin steps
  -> ui/steps/auto/auto_workflow_steps.py maps steps to Python
  -> ui/fixtures.py injects page objects
  -> ui/pages/* performs browser actions
  -> conftest.py writes screenshots, Allure attachments, and metrics
```

### B. Dashboard policy-flow mode

You click "Quick Policy Test" or "Run Policy Journey" in the dashboard.

Flow:

```text
PolicyPanel.jsx
  -> api.quickRun(), api.createPersona(), or api.runFlow()
  -> POST /api/policy/quick-run, /create-persona, or /run-flow
  -> dashboard/backend/main.py creates a job
  -> job_store.new_job()
  -> dashboard_db.create_execution()
  -> BackgroundTasks runs AI and/or Playwright
  -> mcp_tools/policy_flow_generator/persona_generator.py
  -> mcp_tools/policy_flow_generator/flow_runner.py
  -> auto_runner.py or homeowner_runner.py
  -> result_formatter.py creates Markdown
  -> job_store.complete_job()
  -> App.jsx polls /api/jobs/{job_id}
  -> ReportModal.jsx renders the report
```

### C. Dashboard validation mode

You run a regression sweep or direct assert in the Validation Tests page.

Flow:

```text
ApiAssertionsPanel.jsx
  -> api.runRegressionSweep() or api.runAssertFlow()
  -> /api/api-tests/regression-sweep or /api/api-tests/assert-flow
  -> dashboard/backend/main.py creates a job
  -> dashboard/backend/api_assertions/*
  -> AI persona generation when needed
  -> api_tests/oneshield_api_replay.py for browserless Auto replay
  -> assertion_engine.py evaluates expected vs actual
  -> dashboard_db.save_assertion_result()
  -> ReportModal.jsx and assertion history render results
```

### D. Chat mode

You ask the dashboard chat to explain or run supported tools.

Flow:

```text
ChatPanel.jsx
  -> /api/chat/ask, /api/chat/ask/stream, or /api/chat/message
  -> dashboard/backend/chat/chat_router.py
  -> intent_parser.py and llm_provider.py
  -> tool_registry.py validates allowed tool params
  -> chat_router.py dispatches approved tools
  -> job_store/main.py endpoints run the same backend jobs
  -> dashboard_db.py saves chat sessions/messages
```

The chat tool allowlist is intentionally narrow. It lives in `dashboard/backend/chat/tool_registry.py`.

---

## 4. Frontend

Frontend entry point:

- `dashboard/frontend/src/main.jsx`
- `dashboard/frontend/src/App.jsx`

`App.jsx` owns:

- Authentication gate with `api.me()`.
- Top-level routes with `react-router-dom`.
- Sidebar navigation.
- Jobs state.
- Polling running jobs every 2.5 seconds.
- Chat sidebar/fullscreen state.
- Opening `ReportModal`.

Routes in `App.jsx`:

| Route | Component |
|---|---|
| `/dashboard` | `OverviewPanel` |
| `/jobs` | `JobsPanel` |
| `/policy-flow/:lob` | `PolicyPanel` |
| `/policy-flow` | Redirects to saved/default LOB |
| `/uw-tests` | `ApiAssertionsPanel` |
| `/api-tests` | Redirects to `/uw-tests` |
| `/settings` | `SettingsPanel` |
| `/` | Redirects to `/dashboard` |

The frontend API client is `dashboard/frontend/src/utils/api.js`. If you add an endpoint, add a matching function there.

Important frontend components:

| Component | Purpose |
|---|---|
| `OverviewPanel.jsx` | Summary cards and live automation feed. |
| `PolicyPanel.jsx` | Quick test, persona generation, run journey. |
| `ApiAssertionsPanel.jsx` | Regression sweep, direct assert, assertion history. |
| `JobsPanel.jsx` | Job list, rerun, cancel, delete. |
| `ChatPanel.jsx` | Chat sessions, ask mode, tool confirmation, streaming. |
| `ReportModal.jsx` | Parses Markdown/JSON results into readable reports. |
| `LoginPage.jsx` and `RegisterPage.jsx` | Dashboard auth screens. |

---

## 5. Backend

Backend entry point:

```powershell
python dashboard/backend/main.py
```

This starts FastAPI on `http://localhost:8000`.

### Core backend modules

| File | Role |
|---|---|
| `dashboard/backend/main.py` | Main FastAPI app, endpoint definitions, background job orchestration. |
| `dashboard/backend/auth.py` | Dashboard account and session routes. |
| `dashboard/backend/dashboard_db.py` | SQLite schema and persistence. |
| `dashboard/backend/job_store.py` | Runtime job API over `dashboard_db.py`. |
| `dashboard/backend/chat/chat_router.py` | Chat endpoints and tool dispatch. |
| `dashboard/backend/chat/tool_registry.py` | Allowed chat tool schemas. |
| `dashboard/backend/chat/llm_provider.py` | OpenAI, Anthropic, DeepSeek, and Ollama chat calls. |
| `dashboard/backend/chat/intent_parser.py` | Turns natural language into tool intents. |
| `dashboard/backend/api_assertions/` | Plain-English API assertion system. |

### Auth middleware

`dashboard/backend/main.py` defines `dashboard_auth_middleware()`.

Protected paths:

- Most `/api/*` routes.
- `/screenshots/*`.
- `/allure/*`.

Public API paths:

- `/api/health`
- `/api/config`
- `/api/login`
- `/api/register`
- `/api/auth/login`
- `/api/auth/me`
- `/api/auth/logout`

Session handling:

- `auth.py` sets an HTTP-only cookie named `dashboard_session`.
- Session tokens are stored hashed in the `sessions` table.
- `dashboard_db.user_for_token()` validates tokens.
- `dashboard_db.set_current_user()` stores the user in a context variable while a request is handled.

---

## 6. Job System

Jobs are used for long-running work: browser flows, AI generation, validation sweeps, UW audits, and chat-dispatched tools.

### Job lifecycle

```text
Endpoint receives request
  -> _new_job(label, execution_type, metadata)
  -> job_store.new_job()
  -> dashboard_db.create_execution()
  -> bg.add_task(_run)
  -> _run calls automation code
  -> _status(jid, phase, detail) during progress
  -> _done(jid, result) on success
  -> _fail(jid, error) on exception
```

The helper aliases in `dashboard/backend/main.py` are:

```python
_new_job = wrapped job_store.new_job
_log = _job_store.log_job
_status = _job_store.update_job_status
_done = _job_store.complete_job
_fail = _job_store.fail_job
```

`job_store.py` stores a memory copy in `_jobs`, but it also persists every job to SQLite through `dashboard_db.py`. After backend restart, job history comes back from the `executions` table.

### Job endpoints

| Endpoint | Function |
|---|---|
| `GET /api/jobs` | Lists jobs visible to the current user. |
| `GET /api/jobs/{job_id}` | Returns one job. |
| `DELETE /api/jobs/{job_id}` | Deletes terminal jobs owned by the current user. |
| `POST /api/jobs/{job_id}/cancel` | Marks a job canceled. |
| `POST /api/jobs/{job_id}/rerun` | Recreates a supported job from saved metadata. |

### Cancellation

Cancellation uses:

- `job_store.cancel_job(jid)`
- `job_store.is_canceled(jid)`
- `job_store.mark_canceled(jid)`
- `flow_runner._check_cancel(job_id)`

`mcp_tools/policy_flow_generator/flow_runner.py` checks cancellation before and during supported flow execution.

---

## 7. Database

Active database helper:

- `dashboard/backend/dashboard_db.py`

Default database:

```text
dashboard/backend/data/dashboard.db
```

Override:

```env
DASHBOARD_DB_PATH=some/path/dashboard.db
```

Tables:

| Table | Main columns | Purpose |
|---|---|---|
| `users` | `id`, `username`, `password_hash`, `first_name`, `last_name`, `role`, `created_at` | Dashboard users. |
| `sessions` | `token_hash`, `user_id`, `created_at`, `expires_at`, `revoked_at` | Login sessions. |
| `executions` | `id`, `execution_type`, `execution_name`, `status`, `result`, `error`, `logs_json`, `current_status_json`, `metadata_json` | Job history and reports. |
| `saved_suites` | `name`, `prompts_json`, `builder_json`, `shared_persona`, `created_by` | Saved test prompt suites. |
| `assertion_results` | `persona_description`, `assertion_type`, `expected_value`, `actual_value`, `passed`, `persona_json`, `flow_result_json`, `run_id` | Validation history. |
| `chat_sessions` | `user_id`, `title`, `created_at`, `updated_at` | Chat sessions. |
| `chat_messages` | `chat_session_id`, `role`, `content`, `created_at` | Chat messages. |

Important functions:

| Function | Purpose |
|---|---|
| `init_db()` | Creates or migrates tables. Called at import. |
| `create_user()` / `authenticate_user()` | Account creation and login. |
| `create_session()` / `user_for_token()` / `revoke_session()` | Session lifecycle. |
| `create_execution()` | Inserts a running job. |
| `update_execution_status()` | Stores current job phase. |
| `append_execution_log()` | Adds a log entry to `logs_json`. |
| `finish_execution()` | Stores done/error/canceled result. |
| `list_executions()` / `get_execution()` / `delete_execution()` | Job history access. |
| `save_assertion_result()` | Stores direct assert/sweep history. |
| `create_chat_session()` / `add_chat_message()` | Chat persistence. |

Note: `dashboard/backend/database.py` defines a SQLAlchemy engine, but the active implementation for dashboard users, sessions, jobs, assertions, and chat is `dashboard_db.py`.

---

## 8. Playwright UI Layer

The UI automation code is built around Page Object Model.

```text
Feature files
  -> Step functions
  -> Page object fixtures
  -> Page object methods
  -> BasePage helpers
  -> Playwright page
```

### Key files

| File | Purpose |
|---|---|
| `conftest.py` | Browser lifecycle, CLI options, screenshot hook, metrics hook. |
| `ui/fixtures.py` | Creates page object fixtures. |
| `ui/pages/common/base_page.py` | Smart Playwright wrappers and OneShield/ExtJS helpers. |
| `ui/steps/common/data_steps.py` | Loads JSON/Excel data by `TC_ID`. |
| `utils/json_reader.py` | JSON file reader. |
| `utils/excel_reader.py` | Excel file reader. |
| `utils/api_flow_recorder.py` | Optional network capture for UI actions. |

### Root `conftest.py` hooks

| Hook/fixture | What it does |
|---|---|
| `pytest_configure()` | Adds markers, run id, metadata, Allure environment file. |
| `pytest_addoption()` | Registers custom CLI options. |
| `browser()` | Launches Chromium/Firefox/WebKit/Chrome/Edge. |
| `context()` | Creates a fresh browser context per test and optional trace. |
| `page()` | Creates a fresh Playwright page per test. |
| `api_flow_recorder()` | Optional API traffic capture. |
| `pytest_runtest_makereport()` | Captures failure screenshots and writes metrics. |
| `pytest_sessionfinish()` | Runs `scripts/generate_metrics_dashboard.py`. |

---

## 9. AI and MCP Layer

### MCP server config

`.mcp.json` declares these local MCP servers:

| Name | Module |
|---|---|
| `policy-flow-generator` | `mcp_tools.policy_flow_generator.server` |
| `uw-rules-validator` | `mcp_tools.uw_rules_validator.server` |
| `local-inference` | `mcp_tools.local_inference.server` |
| `smart-assertions` | `mcp_tools.smart_assertions.server` |

The config currently includes absolute paths. If another engineer clones the project into a different directory, update `.mcp.json`.

### Policy flow AI

`mcp_tools/policy_flow_generator/persona_generator.py` is responsible for AI-created personas.

Important functions:

- `generate_persona(lob, description)`
- `generate_persona_variations(lob, base_description, count)`
- `generate_batch_personas(scenarios)`
- `list_archetypes(lob)`

The dashboard imports these in `main.py`:

```python
from mcp_tools.policy_flow_generator.flow_runner import run_flow
from mcp_tools.policy_flow_generator.persona_generator import generate_persona, list_archetypes
from mcp_tools.policy_flow_generator.result_formatter import format_batch_summary, format_result
```

### Flow execution

`mcp_tools/policy_flow_generator/flow_runner.py` launches Playwright and routes by LOB:

```python
_LOB_RUNNERS = {
    "auto": run_auto_flow,
    "homeowner": run_homeowner_flow,
}
```

Result shape returned by `run_flow()`:

```python
{
    "tc_id": str,
    "lob": str,
    "persona_type": str,
    "overall_status": "passed" | "failed" | "uw_referral",
    "outcome": "policy_bound" | "uw_referral" | "error",
    "uw_conditions": list[str],
    "steps": list[dict],
    "total_duration_s": float,
    "premium": str | None,
    "error": str | None,
    "screenshot_path": str | None,
}
```

`result_formatter.format_result()` converts this dict into dashboard Markdown.

---

## 10. Policy Flow Details

### Auto runner

File:

- `mcp_tools/policy_flow_generator/runners/auto_runner.py`

Main function:

- `run_auto_flow(page, persona, steps, progress_callback=None)`

Flow:

```text
LoginPage.navigate()
LoginPage.fill_credentials_from_env()
LoginPage.click_login()
NewQuotePage.new_quote_steps()
CustomerPage.customer_steps(persona)
QuoteRegistrationPage.quote_registration_steps(persona)
QuoteSummaryPage.summary_steps(persona)
DriverInfoPage.fill_driver_info(persona)
VehicleInfoPage.fill_vehicle_info(persona)
PolicyTermPage.policy_term_steps(persona)
UWReferralPage detection/capture/optional override
CreatePolicyPage issue/next/bind path
PolicySummary.extract_details(persona)
PolicySummary.save_lob_report(policy_summary)
```

Outcomes:

- `policy_bound`
- `uw_referral`
- `error`

### Homeowner runner

File:

- `mcp_tools/policy_flow_generator/runners/homeowner_runner.py`

Main function:

- `run_homeowner_flow(page, persona, steps, progress_callback=None)`

Flow:

```text
Login
New Quote
Customer
Quote Registration
HomeOwnerQuoteSummaryPage.summary_steps(persona)
HomeownerCityInformationPage.click_save()
HomeownerCityInformationPage.click_homeowners_link(persona)
HomeownerCoveragePage.coverage_steps(persona)
HomeownerBindInformationPage set fields
Rate Quote
UW referral detection or policy bind
PolicySummary.extract_details(persona)
PolicySummary.save_lob_report(policy_summary)
```

---

## 11. API Assertion Layer

The API assertion layer lets the dashboard validate business rules from plain English.

Main files:

| File | Responsibility |
|---|---|
| `dashboard/backend/api_assertions/parser.py` | Converts plain English into `ApiAssertionSpec`. |
| `dashboard/backend/api_assertions/schemas.py` | Pydantic models: `ApiAssertion`, `ApiAssertionSpec`, `AssertionFinding`, `ApiAssertionRunResult`. |
| `dashboard/backend/api_assertions/runner.py` | `run_plain_english_api_assertion()`. |
| `dashboard/backend/api_assertions/assertion_engine.py` | `evaluate_assertions()` and finding logic. |
| `dashboard/backend/api_assertions/premium.py` | Extracts premium evidence. |
| `dashboard/backend/api_assertions/comparative.py` | Compares two personas/scenarios. |
| `dashboard/backend/api_assertions/ladder.py` | Runs rating ladder checks. |
| `dashboard/backend/api_assertions/regression_sweep.py` | Generates variants and analyzes regressions. |
| `dashboard/backend/api_assertions/snapshot.py` | Temporary replay snapshot cache by `run_id`. |
| `api_tests/oneshield_api_replay.py` | Browserless replay client for captured Auto flow. |

Plain-English assertion flow:

```text
Prompt
  -> parse_plain_english_api_assertion(prompt)
  -> generate_persona(spec.lob, spec.persona_prompt)
  -> OneShieldApiReplay().run_captured_auto_flow(...)
  -> evaluate_assertions(spec.assertions, persona, flow_result)
  -> ApiAssertionRunResult
  -> format_api_assertion_report()
```

Supported assertion types in `assertion_engine.py` include:

- `premium`
- `coverage`
- `page_contains`
- `page_not_contains`
- `uw_condition_contains`
- `uw_condition_absent`
- `uw_condition_count`
- `completed`
- `field_value`
- `action_available`
- `flow_blocked`
- `total_cost`
- `policy_status`
- `base_rate`
- `premium_factor`

---

## 12. Reports

### Test run reports

`pytest.ini` automatically creates:

- `reports/pytest_report.html`
- `allure-results/`

`conftest.py` adds:

- Allure `environment.properties`.
- Failure screenshots for UI tests.
- Metrics JSONL.
- Metrics HTML dashboard after the session.

### Dashboard reports

Dashboard job results are usually Markdown strings saved in `executions.result`.

Created by:

- `mcp_tools/policy_flow_generator/result_formatter.py`
- `mcp_tools/uw_rules_validator/report_formatter.py`
- `dashboard/backend/api_assertions/formatter.py`
- custom formatting blocks in `dashboard/backend/main.py`

Rendered by:

- `dashboard/frontend/src/components/ReportModal.jsx`

`ReportModal.jsx` contains parsing helpers such as:

- `parsePolicyFlowReport(content)`
- `parseSummaryChunk(chunk)`
- `parseStepsChunk(chunk)`
- `parseUwChunk(chunk)`
- `parseCoverageRows(content)`
- `parseAssertionSuiteContent(content)`
- `parseUwBatchContent(content)`

### Policy summary CSV

`ui/pages/common/policy_summary_page.py` uses:

- `PolicySummary.extract_details(test_data)`
- `PolicySummary.save_lob_report(details)`
- `utils.file_writer.save_summary_to_csv()`

The LOB-specific policy summary class is selected by `PolicySummary._lob_summary(program)`.

---

## 13. Main Change Points

### Add a new BDD UI test

Change:

- `ui/features/<lob>/*.feature`
- `ui/tests/test_<lob>.py`
- `ui/steps/<lob>_steps.py`
- `ui/pages/<lob>/*.py`
- `ui/fixtures.py`
- `conftest.py` if adding a new step module
- `pytest.ini` if adding a new marker
- `testdata/static/<lob>/*.json`

### Add a new page object

Change:

- Add class under `ui/pages/<lob>/`.
- Inherit `BasePage`.
- Add a fixture in `ui/fixtures.py`.
- Call it from a step function or runner.

### Add a new dashboard backend action

Change:

- Endpoint in `dashboard/backend/main.py`.
- Job persistence through `job_store.py` for long-running work.
- Database helpers in `dashboard/backend/dashboard_db.py` if history is needed.
- React API wrapper in `dashboard/frontend/src/utils/api.js`.
- Component in `dashboard/frontend/src/components/`.

### Add a new chat tool

Change:

- Tool schema in `dashboard/backend/chat/tool_registry.py`.
- Intent handling in `dashboard/backend/chat/intent_parser.py` if needed.
- Dispatch logic in `dashboard/backend/chat/chat_router.py`.
- Job endpoint or direct function in `dashboard/backend/main.py`.

### Add a new AI-supported LOB

Change:

- Persona prompt/schema in `mcp_tools/policy_flow_generator/persona_generator.py`.
- Runner in `mcp_tools/policy_flow_generator/runners/`.
- `_LOB_RUNNERS` in `flow_runner.py`.
- Result formatting in `result_formatter.py` if needed.
- Dashboard LOB lists and mappings in `main.py`, `PolicyPanel.jsx`, and `utils/api.js`.
- Page objects, test data, features, steps, and fixtures under `ui/`.

### Add a new UW rule

Change:

- `mcp_tools/uw_rules_validator/rule_registry.py`.
- `mcp_tools/uw_rules_validator/validator.py` only for new validation semantics.
- `mcp_tools/uw_rules_validator/report_formatter.py` only for report shape changes.
- `mcp_tools/policy_flow_generator/result_formatter.py` if you want the rule name recognized in policy flow reports.

---

## 14. Quick Debug Map

| Symptom | Start here |
|---|---|
| Dashboard cannot log in | `dashboard/backend/auth.py`, `dashboard/backend/dashboard_db.py`, `users`, `sessions` tables |
| Job stuck or missing | `dashboard/backend/job_store.py`, `dashboard/backend/dashboard_db.py`, `executions` table |
| Policy flow fails in dashboard | `dashboard/backend/main.py`, `mcp_tools/policy_flow_generator/flow_runner.py`, LOB runner, `reports/screenshots/` |
| BDD step not found | `conftest.py` `pytest_plugins`, matching file under `ui/steps/` |
| Page click/fill flaky | `ui/pages/common/base_page.py`, use `smart_click`, `smart_fill`, `select_extjs_option` |
| Test data not loading | `ui/steps/common/data_steps.py`, JSON `testCases`, exact `TC_ID` |
| Dashboard validation assertion wrong | `dashboard/backend/api_assertions/parser.py`, `assertion_engine.py`, `api_tests/oneshield_api_replay.py` |
| Report looks wrong in UI | `dashboard/frontend/src/components/ReportModal.jsx` parser/render helpers |
| Chat ran wrong tool | `dashboard/backend/chat/intent_parser.py`, `tool_registry.py`, `chat_router.py` |
| AI provider wrong | `.env`, `AI_PROVIDER`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, startup logs in `main.py` |

---

## 15. Mental Model for New QA Engineers

Think of the project in layers:

1. **Page objects** know how to click and fill OneShield.
2. **Step definitions** turn readable BDD steps into page object calls.
3. **Pytest** runs those steps and produces test reports.
4. **MCP/AI tools** generate personas and run some flows automatically.
5. **FastAPI** wraps those tools into dashboard endpoints.
6. **Jobs** make slow actions trackable and rerunnable.
7. **SQLite** keeps dashboard users, job history, chat, and assertion history.
8. **React** gives QA engineers a visual way to start flows, watch progress, and read reports.

When adding a feature, first decide which layer owns the behavior. Then make the smallest change in that layer and wire outward only as needed.
