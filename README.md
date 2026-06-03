# Playwright Automation Framework Guide

**Last updated:** March 13, 2026
**Status:** Active

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Technology Stack](#2-technology-stack)
3. [Project Structure](#3-project-structure)
4. [Getting Started](#4-getting-started)
5. [Environment Variables](#5-environment-variables)
6. [Core Concepts](#6-core-concepts)
   - 6.1 [Page Object Model (POM)](#61-page-object-model-pom)
   - 6.2 [BasePage & Smart Wrappers](#62-basepage--smart-wrappers)
   - 6.3 [BDD with pytest-bdd](#63-bdd-with-pytest-bdd)
   - 6.4 [Data-Driven Testing](#64-data-driven-testing)
   - 6.5 [Fixtures & Dependency Injection](#65-fixtures--dependency-injection)
7. [Writing Tests](#7-writing-tests)
8. [Test Execution & CLI Reference](#8-test-execution--cli-reference)
9. [Markers Reference](#9-markers-reference)
10. [Reporting](#10-reporting)
11. [Logging & Credential Safety](#11-logging--credential-safety)
12. [Screenshot on Failure](#12-screenshot-on-failure)
13. [API Testing](#13-api-testing)
14. [Docker](#14-docker)
15. [Docker Compose Profiles](#15-docker-compose-profiles)
16. [CI/CD — Jenkins](#16-cicd--jenkins)
17. [Configuration Files](#17-configuration-files)
18. [Troubleshooting](#18-troubleshooting)

---

## 1. Architecture Overview

The framework combines three complementary patterns:

| Pattern | Purpose |
|---|---|
| **Page Object Model (POM)** | Encapsulates all UI element locators and interactions inside page classes, organized by application module. |
| **BDD — pytest-bdd** | Tests are authored in Gherkin `.feature` files and mapped to Python step definitions. |
| **Data-Driven Testing (DDT)** | Test data lives in external JSON files (primary) and Excel (legacy), filtered by `TC_ID` and injected via pytest fixtures. |

### Request Flow

```
Feature File (.feature)
    ↓  parsed by pytest-bdd
Step Definitions (ui/steps/)
    ↓  receive page fixtures via DI
Page Objects (ui/pages/)
    ↓  extend BasePage
Playwright Sync API
    ↓
Browser (Chromium / Firefox / WebKit / Chrome / Edge)
```

### Data Flow

```
AutoData.json  →  DataLoader  →  test_data dict  →  Step Definitions  →  Page Object methods
                                      ↑
                              filtered by TC_ID
```

---

## 2. Technology Stack

| Category | Library | Purpose |
|---|---|---|
| Browser automation | `playwright` | Cross-browser UI testing via Sync API |
| Test runner | `pytest` | Discovery, execution, fixtures, hooks |
| BDD engine | `pytest-bdd` | Gherkin feature file support |
| Parallel execution | `pytest-xdist` | Multi-process `-n N` parallelism |
| Reporting (rich) | `allure-pytest`, `allure-python-commons` | Step-by-step Allure reports |
| Reporting (lightweight) | `pytest-html` | Self-contained HTML report |
| Environment config | `python-dotenv` | `.env` file loading |
| API testing | `requests` | HTTP client for API test suites |
| Data (primary) | JSON + stdlib `json` | Fast, lightweight test data |
| Data (legacy) | `pandas`, `openpyxl` | Excel-based test data reader |
| Visualization | `matplotlib` | Policy premium trend charts |
| Code coverage | `pytest-cov` | Coverage reports |
| Test timeouts | `pytest-timeout` | Prevent hanging tests |
| Code quality | `flake8` | Linting in CI pipeline |

Full dependency list in `requirements.txt`.

---

## 3. Project Structure

```
SandboxPlaywright/
│
├── conftest.py                  # Global fixtures, CLI options, screenshot hook
├── pytest.ini                   # Discovery, markers, addopts, default browser
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker image for test execution
├── docker-compose.yml           # Multi-service test execution profiles
├── Jenkinsfile                  # Jenkins CI/CD pipeline
├── .env                         # Credentials and env vars (git-ignored)
│
├── config/
│   ├── environments.yaml        # Environment-specific URLs and config
│   └── secrets.yaml             # Sensitive config (git-ignored)
│
├── ui/
│   ├── fixtures.py              # Page object fixture instantiation
│   ├── features/                # BDD Gherkin feature files
│   │   ├── auto/
│   │   │   └── personal_auto.feature
│   │   ├── common/
│   │   │   ├── login.feature
│   │   │   ├── login_validation.feature
│   │   │   └── customer_validation.feature
│   │   └── homeowner/
│   │       └── homeowner_creation.feature
│   ├── pages/                   # Page Object Model classes
│   │   ├── common/
│   │   │   ├── base_page.py     # Abstract base (smart wrappers, helpers)
│   │   │   ├── login_page.py    # Splash screen and credentials
│   │   │   ├── customer_page.py # Customer creation & search
│   │   │   ├── new_quote_page.py
│   │   │   └── policy_summary_page.py
│   │   ├── auto/
│   │   │   ├── quote_registration_page.py
│   │   │   ├── quote_summary_page.py
│   │   │   ├── driver_info_page.py
│   │   │   ├── vehicle_info_page.py
│   │   │   ├── policy_term_page.py
│   │   │   └── create_policy_page.py
│   │   └── homeowner/
│   │       ├── homeowner_quote_summary_page.py
│   │       └── homeowner_coverage_page.py
│   ├── steps/                   # BDD step definitions
│   │   ├── common/
│   │   │   ├── auth_steps.py           # Login step
│   │   │   ├── data_steps.py           # JSON + Excel data loading
│   │   │   ├── login_validation_steps.py # Detailed login field validation
│   │   │   └── customer_validation_steps.py
│   │   ├── auto/
│   │   │   └── auto_workflow_steps.py  # Full auto policy workflow
│   │   └── homeowner_steps.py
│   └── tests/                   # pytest-bdd scenario entry points
│       ├── test_auto_workflow.py
│       ├── test_login.py
│       ├── test_login_validation.py
│       ├── test_customer_validation.py
│       └── test_homeowner.py
│
├── api_tests/
│   ├── conftest.py              # Session-scoped requests.Session fixture
│   ├── test_users.py
│   ├── test_bin.py
│   ├── kupujem_prodajem_test.py
│   ├── GUIDE_API_TESTING.md
│   └── ASSERTION_GUIDE.md
│
├── testdata/
│   ├── auth_state.json          # Saved browser authentication state
│   └── static/
│       ├── AutoData.json        # Primary auto test data
│       ├── AutoData.xlsx        # Legacy Excel data
│       ├── CustomerValidationData.json
│       └── HomeData.json
│
├── utils/
│   ├── logger.py                # Timestamped file logger + credential masking
│   ├── json_reader.py           # DataLoader (Pathlib-based JSON reader)
│   ├── excel_reader.py          # ExcelReader (pandas + openpyxl)
│   ├── email_util.py            # Timestamp-based unique email generator
│   ├── file_writer.py           # CSV summary writer (append mode)
│   ├── policy_reporter.py       # matplotlib trend charts
│   ├── waiters.py               # Custom wait strategies
│   └── assertions.py            # Custom assertion helpers
│
├── logs/                        # Generated log files per test session
├── screenshots/                 # Failure screenshots
├── reports/                     # pytest-html output
├── allure-results/              # Allure raw result data
└── allure-report/               # Generated Allure HTML report
```

---

## 4. Getting Started

### Prerequisites

- Python 3.10+
- pip
- Allure CLI — [install guide](https://docs.qameta.io/allure/#_installing_a_commandline)
- Docker (optional, for containerized runs)

### Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd SandboxPlaywright

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browser binaries
playwright install
```

### Verify Setup

```bash
pytest ui/tests/test_login.py -v --headed
```

---

## 5. Environment Variables

The framework calls `load_dotenv()` at session start (`conftest.py`). Create a `.env` file in the project root:

```env
PARTNER_NUM=0
USERNAMEE=your_username
PASSWORD=your_password
```

> **Note:** `USERNAMEE` uses a double E intentionally to avoid collision with the Windows system variable `USERNAME`.

`.env` is git-ignored and must never be committed.

---

## 6. Core Concepts

### 6.1 Page Object Model (POM)

Every application page is a Python class that:

1. Inherits from `BasePage`
2. Defines element locators in `__init__`
3. Exposes action methods decorated with `@allure.step`

**Module layout:**

| Directory | Scope |
|---|---|
| `ui/pages/common/` | Login, Customer, Quote, Policy Summary |
| `ui/pages/auto/` | Entire Personal Auto insurance workflow |
| `ui/pages/homeowner/` | Homeowner insurance workflow |

**Locator priority (most stable → least):**

1. `page.get_by_role(...)` — accessibility-based, preferred
2. `page.get_by_label(...)` — form fields with visible labels
3. `page.get_by_text(...)` — text-based elements
4. `page.locator("css=...")` — CSS selectors
5. `page.locator("//xpath")` — last resort only

### 6.2 BasePage & Smart Wrappers

`ui/pages/common/base_page.py` is the foundation every page class inherits from.

**Key capabilities:**

| Method | Description |
|---|---|
| `smart_click(target)` | Visibility + enabled check, stability wait, 2-attempt retry, DOM metadata capture on failure |
| `smart_fill(locator, value)` | Resilient fill with click + clear pre-step |
| `type_text(selector, value)` | Character-by-character typing with Ctrl+A → Backspace clear |
| `answer_question(group, answer)` | Radio group selection via `dispatch_event("click")` for OneShield patterns |
| `wait_visible(selector)` | Waits for visibility, returns locator |
| `wait_clickable(selector)` | Waits for element attachment |
| `read_summary(label)` | Extracts display-only summary values |
| `spinner_wait(selector)` | Waits for loading mask/spinner to disappear |

**Failure metadata capture:** When a smart wrapper fails, `_capture_failure_metadata()` collects element tag, class, ID, aria-label, bounding box, and computed CSS styles, then attaches a JSON artifact to the Allure report automatically.

### 6.3 BDD with pytest-bdd

**Layer responsibilities:**

```
.feature file      →  Describes WHAT (business language)
step definitions   →  Maps Gherkin → Python, orchestrates page objects
page objects       →  Describes HOW the interaction works
```

**Feature file anatomy:**

```gherkin
Feature: Personal Auto Creation

  Background:
    Given The user is logged in with valid credentials

  @auto
  Scenario Outline: Create a new personal auto policy
    Given the data is loaded "testdata/static/AutoData.json", "<TC_ID>"
    When i create a new quote
    When i create a new customer
    When I provide quote registration details
    When I provide quote summary PA info
    When I provide Driver Details
    When I provide Vehicle Details
    Given I provide policy term details
    When I create a policy from the quote
    Then I read and extract policy summary page details

    Examples:
      | TC_ID      |
      | TC_ID_0001 |
      | TC_ID_0002 |
```

**Test entry points** — each feature requires a matching file in `ui/tests/`:

```python
# ui/tests/test_auto_workflow.py
from pytest_bdd import scenario

@scenario('../features/auto/personal_auto.feature', 'Create a new personal auto policy')
def test_personal_auto_workflow():
    pass          # All logic is in step definitions; body is intentionally empty
```

### 6.4 Data-Driven Testing

#### JSON (Primary)

File: `testdata/static/AutoData.json`

```json
{
  "testCases": [
    {
      "TC_ID": "TC_ID_0001",
      "CustomerType": "Individual",
      "FirstName": "James",
      "LastName": "Smith",
      "DOB": "11/10/1992",
      "Email": "jsmith_{timestamp}@auto.com",
      "ZIP": "01101",
      "Producer": "Janis Irey",
      "Program": "Personal Auto",
      "Gender": "Male",
      "Year": "2018",
      "Make": "BMW",
      "Model": "M3",
      "PolicyCoverage": "Gold"
    }
  ]
}
```

Conventions:
- Keys use `CamelCase` to align with modern API standards
- Values are always strings (preserves leading zeros in ZIP/phone)
- `{timestamp}` in email values is replaced at runtime with epoch milliseconds via `utils/email_util.py`

#### Excel (Legacy)

Supported via `ExcelReader` using pandas + openpyxl:

```gherkin
Given the data is loaded "testdata/static/AutoData.xlsx", "Sheet1", "TC_ID_0001"
```

Both loaders inject a single filtered row as the `test_data` fixture via `target_fixture="test_data"`.

#### Multiple Data Files

| File | Usage |
|---|---|
| `AutoData.json` | Personal Auto full workflow |
| `CustomerValidationData.json` | Customer creation/validation |
| `HomeData.json` | Homeowner workflow |
| `AutoData.xlsx` | Legacy fallback for AutoData |

### 6.5 Fixtures & Dependency Injection

**Root `conftest.py` fixtures:**

| Fixture | Scope | Description |
|---|---|---|
| `log` | session | Logger instance with credential masking |
| `browser_name` | session | Browser from `--browser` CLI option |
| `playwright` | session | Playwright context manager |
| `browser` | session | Launched browser (headed/headless, slow_mo) |
| `context` | function | Fresh browser context per test; full-screen viewport; optional tracing |
| `page` | function | Fresh page per test |
| `data` | function | Alias for `test_data` |

**Custom CLI options registered in `conftest.py`:**

| Option | Default | Description |
|---|---|---|
| `--browser` | `chromium` | `chromium`, `firefox`, `webkit`, `chrome`, `msedge` |
| `--headed` | `False` | Show browser window |
| `--slow-mo` | `0` | Slow down every Playwright operation by N ms |
| `--pw-trace` | `off` | Enable Playwright tracing (`on` saves `.zip` to `reports/traces/`) |

`--browser chrome` and `--browser msedge` launch locally installed Chrome / Edge via Chromium channels, not Playwright's bundled Chromium.

**Page object fixtures** — defined in `ui/fixtures.py`:

```python
@pytest.fixture
def login_page(page):
    return LoginPage(page)
```

Every page class has a matching fixture. All are registered as plugins via `pytest_plugins` in `conftest.py`:

```python
pytest_plugins = [
    "ui.fixtures",
    "ui.steps.common.auth_steps",
    "ui.steps.common.login_validation_steps",
    "ui.steps.common.data_steps",
    "ui.steps.auto.auto_workflow_steps",
    "ui.steps.homeowner_steps",
    "ui.steps.common.customer_validation_steps",
]
```

**Lifecycle:**

```
Session
  └── log, playwright, browser
      ├── Test 1
      │   └── context → page → [page objects] → test_data
      ├── Test 2
      │   └── context → page → [page objects] → test_data
      └── ...
```

---

## 7. Writing Tests

### Adding a New Test Case to an Existing Feature

1. Add a data row to the relevant JSON file with a new `TC_ID`
2. Add the `TC_ID` to the `Examples` table in the corresponding `.feature` file
3. Run and verify: `pytest ui/tests/test_auto_workflow.py -v`

### Adding a New Feature

1. Create a `.feature` file under `ui/features/<module>/`
2. Create step definition files under `ui/steps/<module>/`
3. Create a test entry point under `ui/tests/`
4. Register the step module in `pytest_plugins` in `conftest.py`
5. Add necessary page objects to `ui/pages/<module>/` and `ui/fixtures.py`

---

## 8. Test Execution & CLI Reference

```bash
# All tests (uses addopts from pytest.ini)
pytest

# Targeted marker
pytest -m auto
pytest -m validation
pytest -m api
pytest -m smoke
pytest -m homeowner

# Parallel execution
pytest -m auto -n 4
pytest -m validation -n 2

# Browser selection
pytest --browser=chromium          # default
pytest --browser=chrome            # system Google Chrome
pytest --browser=msedge            # system Edge
pytest --browser=firefox
pytest --browser=webkit

# Debugging
pytest --headed                    # show browser
pytest --slow-mo=100               # 100ms between actions
pytest --pw-trace=on               # enables Playwright trace recording

# Single test file
pytest ui/tests/test_login.py -v

# Single scenario
pytest ui/tests/test_auto_workflow.py::test_personal_auto_workflow -v
```

---

## 9. Markers Reference

Defined in `pytest.ini`:

| Marker | Description |
|---|---|
| `auto` | Personal Auto insurance workflow tests |
| `homeowner` | Homeowner insurance workflow tests |
| `smoke` | Quick critical path checks |
| `regression` | Full regression suite |
| `login` | Login flow tests |
| `validation` | Field validation and error handling |
| `api` | API/HTTP tests |
| `empty-fields` | Empty field edge cases |
| `invalid-credentials` | Bad credential handling |
| `format-validation` | Field format rules |
| `security` | Security-related UI tests |
| `accessibility` | Accessibility checks |

---

## 10. Reporting

### Allure (Rich Reports)

```bash
# Generate and serve Allure report
allure serve allure-results

# Or generate static report
allure generate allure-results --clean -o allure-report
```

Allure reports include:
- Step-by-step test execution with `@allure.step` breadcrumbs
- Failure screenshots automatically attached
- DOM failure metadata JSON attached on smart wrapper errors
- Masked credential parameters where applicable

### pytest-html (Lightweight)

Generated to `reports/pytest_report.html` automatically via `pytest.ini` addopts.

Open directly in any browser — fully self-contained, no server needed.

### Artifacts Per Run

| Artifact | Location |
|---|---|
| Allure raw data | `allure-results/` |
| Allure HTML report | `allure-report/` |
| pytest-html report | `reports/pytest_report.html` |
| Failure screenshots | Attached to Allure (in-memory, no file write) |
| Playwright traces | `reports/traces/<test_name>.zip` (when `--pw-trace=on`) |
| Execution logs | `logs/test_run_<timestamp>.log` |

---

## 11. Logging & Credential Safety

### Logger Setup

`utils/logger.py` creates a timestamped log file per session under `logs/`.

Log format: `YYYY-MM-DD HH:MM:SS - LoggerName - LEVEL - message`

Live log output to console is enabled in `pytest.ini` at INFO level.

### Credential Masking

The logger applies a `_CredentialMaskFilter` that intercepts every log record and replaces the resolved values of `USERNAMEE` and `PASSWORD` environment variables with `***`.

Pattern is built once lazily on the first log write, using escaped regex from the actual env values.

Allure report masking is implemented in `ui/steps/common/login_validation_steps.py`:

```python
from allure_commons.types import ParameterMode

allure.dynamic.parameter("username", username, mode=ParameterMode.MASKED)
allure.dynamic.parameter("password", password, mode=ParameterMode.MASKED)
```

> **Note:** The Allure Python API does not have `allure.mask_parameters()`. Use `allure.dynamic.parameter(..., mode=ParameterMode.MASKED)` instead.

---

## 12. Screenshot on Failure

Implemented as a `pytest_runtest_makereport` hook in `conftest.py`.

Behavior:
- Triggers on `report.when == "call"` and `report.failed == True`
- Skips tests marked with `@pytest.mark.api` (no browser)
- Locates the `page` fixture from `item.funcargs` or `item._request`
- Takes a full-page screenshot and attaches it to the Allure report as PNG
- No disk write — screenshot bytes are attached in memory directly

---

## 13. API Testing

Location: `api_tests/`

**Session fixture** (`api_tests/conftest.py`): Creates a `requests.Session` with pre-configured headers for the target API. Session is shared across all API tests and closed at session teardown.

**Test files:**

| File | Subject |
|---|---|
| `test_users.py` | JSONPlaceholder users API |
| `test_bin.py` | httpbin.org practice tests |
| `kupujem_prodajem_test.py` | KupujemProdajem search API |

Run API tests:

```bash
pytest api_tests/ -v
# or by marker
pytest -m api -v
```

See `api_tests/ASSERTION_GUIDE.md` and `api_tests/GUIDE_API_TESTING.md` for assertion patterns.

---

## 14. Docker

The `Dockerfile` builds an image from the official Playwright Python base image.

**Key build steps:**

1. Install Python dependencies from `requirements.txt`
2. Install Playwright browsers with `playwright install --with-deps`
3. Copy all project files
4. Scaffold required directories (`reports`, `logs`, `screenshots`, `allure-results`)

**Default environment variables baked into the image:**

```
PYTHONUNBUFFERED=1
PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
PYTHONPATH=/app
```

**Build:**

```bash
docker build -t playwright-tests:latest .
```

**Run directly:**

```bash
docker run --rm --.env-file ..env playwright-tests:latest pytest -m auto -n 4 -v
```

Volumes are not mounted in a direct `docker run`, so artifacts stay inside the container and are lost when it exits. Use Docker Compose for artifact persistence.

---

## 15. Docker Compose Profiles

`docker-compose.yml` defines isolated services per test suite. Each service:
- Builds from the same `Dockerfile`
- Loads credentials from `.env` via `env_file`
- Mounts output directories as volumes so artifacts persist on the host after the run

| Service | Marker | Workers |
|---|---|---|
| `tests-auto` | `-m auto` | `-n 4` |
| `tests-validation` | `-m validation` | `-n 5` |
| `tests-api` | `-m api` | none |

**Run a single service:**

```bash
docker compose run --rm tests-auto
docker compose run --rm tests-validation
docker compose run --rm tests-api
```

**Run all sequentially (Windows CMD):**

```cmd
docker compose run --rm tests-auto & docker compose run --rm tests-validation & docker compose run --rm tests-api
```

**Run all sequentially (PowerShell / bash):**

```bash
docker compose run --rm tests-auto
docker compose run --rm tests-validation
docker compose run --rm tests-api
```

> Use `--rm` (double dash). `-rm` (single dash) is invalid and will error.

### Adding a New Suite

Add a new service block in `docker-compose.yml`:

```yaml
tests-smoke:
  build:
    context: .
    dockerfile: Dockerfile
  env_file:
    - ..env
  volumes:
    - ./reports:/app/reports
    - ./allure-results:/app/allure-results
    - ./screenshots:/app/screenshots
    - ./logs:/app/logs
  command: >
    pytest -m smoke
    --html=reports/report.html
    --self-contained-html
    --alluredir=allure-results
    -v
```

---

## 16. CI/CD — Jenkins

Pipeline defined in `Jenkinsfile`.

Typical stages:
- Checkout
- Install dependencies
- Run tests
- Publish Allure and HTML reports
- Archive artifacts (logs, screenshots)

---

## 17. Configuration Files

| File | Purpose |
|---|---|
| `pytest.ini` | Markers, discovery patterns, addopts (default browser, reports, allure dir, live logging) |
| `Dockerfile` | Image definition for test execution |
| `docker-compose.yml` | Multi-suite execution profiles |
| `config/environments.yaml` | Per-environment URLs and config |
| `config/secrets.yaml` | Sensitive config (git-ignored) |
| `.env` | Runtime credentials (git-ignored) |
| `requirements.txt` | Python dependencies |

---

## 18. Troubleshooting

### `AttributeError: module 'allure' has no attribute 'mask_parameters'`

`allure.mask_parameters()` does not exist in the Python Allure package.

Fix:
```python
from allure_commons.types import ParameterMode
allure.dynamic.parameter("password", password, mode=ParameterMode.MASKED)
```

### `unknown shorthand flag: 'r' in -rm`

You used `-rm` (single dash). Fix:
```bash
docker compose run --rm <service>
```

### `exec: ";": executable file not found in $PATH`

`;` is a bash separator; it does not work in Windows CMD. Use `&` or run commands on separate lines.

### Tests fail with credential errors

- Confirm `.env` exists in the project root with correct keys
- For Docker: confirm `--env-file .env` is passed, or `env_file: - .env` is in the compose service
- `USERNAMEE` must have double E

### Screenshot not captured on failure

- Confirm the failing test uses the `page` fixture
- API tests are intentionally skipped (`@pytest.mark.api`)
- Check the hook in `conftest.py` — the `page` is looked up from `funcargs` or `_request`

### Playwright trace not saved

- Add `--pw-trace=on` to your command
- Traces save to `reports/traces/<test_nodeid>.zip`
