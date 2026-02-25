# Playwright Automation Framework Guide

A modern, scalable Python automation framework built for end-to-end testing of enterprise insurance applications (OneShield platform). This guide is the single source of truth for architecture decisions, coding standards, and operational procedures.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Technology Stack](#2-technology-stack)
3. [Project Structure](#3-project-structure)
4. [Getting Started](#4-getting-started)
5. [Core Concepts](#5-core-concepts)
   - 5.1 [Page Object Model (POM)](#51-page-object-model-pom)
   - 5.2 [Base Page Class](#52-base-page-class)
   - 5.3 [BDD with pytest-bdd](#53-bdd-with-pytest-bdd)
   - 5.4 [Data-Driven Testing](#54-data-driven-testing)
   - 5.5 [Fixtures & Dependency Injection](#55-fixtures--dependency-injection)
6. [Writing Tests — Step by Step](#6-writing-tests--step-by-step)
7. [Test Data Management](#7-test-data-management)
8. [Execution & CLI Reference](#8-execution--cli-reference)
9. [Reporting](#9-reporting)
10. [Logging](#10-logging)
11. [Screenshot Capture on Failure](#11-screenshot-capture-on-failure)
12. [Business Reporting (Policy Reporter)](#12-business-reporting-policy-reporter)
13. [CI/CD — Jenkins Pipeline](#13-cicd--jenkins-pipeline)
14. [Configuration Files Reference](#14-configuration-files-reference)
15. [Utility Modules Reference](#15-utility-modules-reference)
16. [Coding Standards & Best Practices](#16-coding-standards--best-practices)
17. [Troubleshooting](#17-troubleshooting)
18. [Extending the Framework](#18-extending-the-framework)

---

## 1. Architecture Overview

This framework implements three complementary design patterns:

| Pattern | Purpose |
|---|---|
| **Unified POM (Page Object Model)** | Encapsulates all UI element locators and interactions inside page classes, organized by application module. |
| **BDD (Behavior Driven Development)** | Tests are authored in Gherkin (`.feature` files) and wired to Python step definitions via `pytest-bdd`. |
| **Data-Driven Testing (DDT)** | Test data lives in external JSON files (primary) or Excel (legacy). Data is filtered by `TC_ID` and injected into steps as a Python dictionary. |

### High-Level Flow

```
Feature File (.feature)
    ↓  (parsed by pytest-bdd)
Step Definitions (ui/steps/)
    ↓  (receive page fixtures via DI)
Page Objects (ui/pages/)
    ↓  (use BasePage helpers)
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

| Category | Tool / Library | Version | Purpose |
|---|---|---|---|
| Language | Python | 3.10+ | Core programming language |
| Browser Automation | Playwright (Sync API) | Latest | Cross-browser UI testing |
| Test Runner | pytest | Latest | Test discovery, execution, fixtures |
| BDD Engine | pytest-bdd | Latest | Gherkin feature file support |
| Reporting | Allure Framework | Latest | Rich HTML reports with screenshots |
| HTML Reports | pytest-html | Latest | Lightweight standalone HTML report |
| Data (Primary) | JSON + `json` stdlib | — | Fast, lightweight test data |
| Data (Legacy) | pandas + openpyxl | Latest | Excel-based test data reader |
| Environment Config | python-dotenv | Latest | `.env` file loading |
| Parallel Execution | pytest-xdist | Latest | Multi-process test runs |
| Code Coverage | pytest-cov | Latest | Coverage reporting |
| Test Timeout | pytest-timeout | Latest | Prevents tests from hanging |
| Code Quality | flake8 | Latest | Linting for CI pipeline |
| Visualization | matplotlib | Latest | Policy premium trend charts |
| HTTP Client | requests | >=2.32.4 | API calls (if needed) |
| CI/CD | Jenkins | — | Automated pipeline execution |

### Full `requirements.txt`

```
pytest
playwright
allure-pytest
python-dotenv
pytest-xdist
pytest-bdd
pandas
openpyxl>=2.4.2
pytest-html
requests>=2.32.4
matplotlib
allure-python-commons
behave
pytest-timeout
pytest-cov
flake8
```

> **Note:** `pytest-playwright` is **not** used. The framework manages Playwright lifecycle directly via `conftest.py`, which allows custom browser options including Chrome and Edge channels.

---

## 3. Project Structure

```
SandboxPlaywright/
│
├── conftest.py                  # Global fixtures, hooks, plugin registration
├── pytest.ini                   # Pytest configuration (markers, addopts, logging)
├── requirements.txt             # Python dependencies
├── Jenkinsfile                  # CI/CD pipeline definition
├── create_folders.py            # Scaffold script for initial project setup
├── .env                         # Environment variables (not committed to git)
│
├── config/
│   ├── environments.yaml        # Environment-specific configuration
│   └── secrets.yaml             # Sensitive configuration (not committed)
│
├── fixtures/
│   └── ui_fixtures.py           # Page Object instantiation fixtures
│
├── ui/
│   ├── __init__.py
│   ├── components/              # Reusable UI components (reserved)
│   │   └── __init__.py
│   ├── features/                # BDD Gherkin feature files
│   │   ├── login.feature        # Login scenario
│   │   └── personal_auto.feature# End-to-end auto policy creation
│   ├── pages/                   # Page Object Model classes
│   │   ├── __init__.py
│   │   ├── common/              # Shared across all insurance products
│   │   │   ├── base_page.py     # Abstract base with reusable helpers
│   │   │   ├── login_page.py    # Splash screen & credential entry
│   │   │   ├── customer_page.py # Customer creation & search
│   │   │   ├── new_quote_page.py# Quote initiation
│   │   │   ├── quote_registration_page.py  # Producer, date, program
│   │   │   └── policy_summary_page.py      # Post-bind data extraction
│   │   ├── auto/                # Personal Auto insurance module
│   │   │   ├── quote_summary_page.py  # Billing, misleading info, damage
│   │   │   ├── driver_info_page.py    # Gender, marital status, license
│   │   │   ├── vehicle_info_page.py   # Year, make, model, spec
│   │   │   ├── policy_term_page.py    # Coverage option & rate quote
│   │   │   └── create_policy_page.py  # Issue, next, bind workflow
│   │   └── homeowner/           # Homeowner insurance module
│   │       └── quote_summary.py # Homeowner-specific quote summary
│   ├── steps/                   # BDD step definitions
│   │   ├── __init__.py
│   │   ├── auth_steps.py        # Login step: "The user is logged in..."
│   │   ├── data_steps.py        # Data loading: JSON and Excel loaders
│   │   └── auto_workflow_steps.py # All auto policy workflow steps
│   └── tests/                   # pytest-bdd scenario files (test entry points)
│       ├── test_login.py        # Wires login.feature to pytest
│       ├── test_auto_workflow.py# Wires personal_auto.feature to pytest
│       └── test_screenshot_verify.py  # Screenshot verification (reserved)
│
├── testdata/
│   ├── auth_state.json          # Saved browser authentication state
│   ├── static/
│   │   ├── AutoData.json        # PRIMARY test data file (JSON)
│   │   └── AutoData.xlsx        # LEGACY test data file (Excel)
│   └── factories/               # Dynamic data generators (reserved)
│       └── __init__.py
│
├── utils/
│   ├── logger.py                # Timestamped file logger setup
│   ├── json_reader.py           # JSON DataLoader with Pathlib resolution
│   ├── excel_reader.py          # Excel reader with pandas + header handling
│   ├── email_util.py            # Timestamp-based email uniqueness
│   ├── file_writer.py           # CSV summary writer (append mode)
│   ├── policy_reporter.py       # matplotlib charts for policy trends
│   ├── screenshot_helper.py     # Screenshot utilities (reserved)
│   ├── waiters.py               # Custom wait strategies (reserved)
│   └── assertions.py            # Custom assertion helpers (reserved)
│
├── logs/                        # Auto-generated log files per session
├── screenshots/                 # Captured screenshots directory
├── reports/                     # pytest-html reports output
├── policy_summary/              # CSV exports & PNG trend charts
├── allure-results/              # Raw Allure JSON result data
└── allure-report/               # Generated Allure HTML report
```

---

## 4. Getting Started

### 4.1 Prerequisites

- **Python 3.10** or later
- **Node.js** (required by Playwright for browser binaries)
- **pip** (Python package manager)
- **Allure CLI** (for report generation — [install guide](https://docs.qameta.io/allure/#_installing_a_commandline))

### 4.2 Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd SandboxPlaywright

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install Playwright browser binaries
playwright install
# Or install only Chromium:
playwright install chromium
```

### 4.3 Environment Configuration

Create a `.env` file in the project root. The framework reads these via `python-dotenv` at startup:

```env
# Target application URL
BASE_URL=https://inforcedev.oneshield.com/splash.html

# Login credentials
PARTNER_NUM=0
USERNAMEE=your_username
PASSWORD=your_password
```

> **Note:** The environment variable is `USERNAMEE` (double E) to avoid conflicts with the Windows system `USERNAME` variable.

### 4.4 Verify Setup

```bash
# Run the login test to confirm everything works
pytest ui/tests/test_login.py -v --headed
```

---

## 5. Core Concepts

### 5.1 Page Object Model (POM)

Every page in the application under test is represented by a Python class that:

1. **Inherits from `BasePage`** — gains common methods (`type_text`, `click_element`, `answer_question`, `wait_visible`, etc.)
2. **Defines locators in `__init__`** — using Playwright's accessibility-first locators
3. **Exposes action methods** — each decorated with `@allure.step` for report visibility

#### Module Organization

| Directory | Scope | Pages |
|---|---|---|
| `ui/pages/common/` | Shared across all product lines | `LoginPage`, `CustomerPage`, `NewQuotePage`, `QuoteRegistrationPage`, `PolicySummary` |
| `ui/pages/auto/` | Personal Auto insurance | `QuoteSummaryPage`, `DriverInfoPage`, `VehicleInfoPage`, `PolicyTermPage`, `CreatePolicyPage` |
| `ui/pages/homeowner/` | Homeowner insurance | `HomeownerQuoteSummary` |

#### Locator Strategy Priority

The framework enforces this locator preference (most stable → least stable):

1. `page.get_by_role("button", name="login")` — **Preferred** (accessibility-based)
2. `page.get_by_label("First Name")` — For form fields with labels
3. `page.get_by_text("Submit")` — For text-based elements
4. `page.locator("css=.my-class")` — CSS selectors
5. `page.locator("//xpath")` — **Last resort only** (brittle)

#### Example Page Object

```python
# ui/pages/auto/driver_info_page.py
from ui.pages.common.base_page import BasePage

class DriverInfoPage(BasePage):
    def __init__(self, page):
        super().__init__(page)
        # Locators defined using accessibility-first approach
        self.gender = page.get_by_role("combobox", name="Gender*")
        self.marital_status = page.get_by_role("combobox", name="Marital Status*")
        self.driver_status = page.get_by_role("combobox", name="Driver Status*")
        self.employment = page.get_by_role("combobox", name="Employment Category")
        self.occupation = page.get_by_role("combobox", name="Occupation")
        self.licence = page.get_by_role("combobox", name="License Status*")
        self.save_button = page.get_by_role("button", name="save changes")

    def fill_driver_info(self, data):
        """Fill driver information form from test data dictionary."""
        self.gender.fill(data["Gender"])
        self.marital_status.fill(data["MaritalStatus"])
        self.driver_status.fill(data["DriverStatus"])
        self.employment.fill(data["EmploymentCategory"])
        self.occupation.fill(data["Occupation"])
        self.licence.fill(data["LicenseStatus"])
        self.answer_question("Certificate of Insurance Required?", data["SR22"])
        self.save_button.click()
```

### 5.2 Base Page Class

`ui/pages/common/base_page.py` is the foundation for all page objects. Every page inherits from it.

#### Available Methods

| Method | Signature | Description |
|---|---|---|
| `wait_visible` | `(selector, timeout=15000)` | Waits for element to become visible, returns the locator |
| `wait_clickable` | `(selector, timeout=15000)` | Waits for element to be attached to DOM |
| `type_text` | `(selector, value, delay=5)` | Clears field via Ctrl+A → Backspace, then types character-by-character |
| `safe_fill` | `(locator, value)` | Click → clear → fill (for stubborn input fields) |
| `click_element` | `(selector)` | Waits for clickable then clicks |
| `answer_question` | `(group_name, answer)` | Selects a radio button within a named radio group using `dispatch_event("click")` |
| `read_summary` | `(label_text)` | Reads a display-only value associated with a label (for extraction) |

All methods are decorated with `@allure.step` and include logger calls for full traceability.

#### `answer_question` — Deep Dive

This method handles the OneShield radio-button pattern where questions are grouped:

```python
def answer_question(self, group_name: str, answer: str):
    if not answer:
        return
    group = self.page.get_by_role("radiogroup", name=re.compile(group_name, re.I))
    radio = group.get_by_label(re.compile(f"^{answer}$", re.I))
    radio.dispatch_event("click")
```

- Uses `re.IGNORECASE` for resilience against case variations
- Uses `dispatch_event("click")` instead of `.click()` because some radio buttons in the platform intercept standard clicks
- Gracefully skips if `answer` is empty/None

### 5.3 BDD with pytest-bdd

#### Layer Responsibilities

```
.feature file     →  Describes WHAT the test does (business language)
step definitions  →  Maps Gherkin to code, orchestrates page objects
page objects      →  Encapsulates HOW interactions work
```

#### Feature File Anatomy

```gherkin
# ui/features/personal_auto.feature
Feature: Personal Auto Creation

  Background: Login as Claim Adjuster
    Given The user is logged in with valid credentials

  @smoke @auto
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
      | TC_ID_0003 |
```

**Key points:**
- **`Background`** runs before every scenario (handles login)
- **`Scenario Outline` + `Examples`** drives data parameterization via `TC_ID`
- **Markers** (`@smoke`, `@auto`) map to pytest markers for selective execution
- The `bdd_features_base_dir` in `pytest.ini` is set to `ui/features/`

#### Test Entry Points

Each feature file needs a corresponding test file in `ui/tests/` that wires the scenario:

```python
# ui/tests/test_auto_workflow.py
from pytest_bdd import scenario

@scenario('../features/personal_auto.feature', 'Create a new personal auto policy')
def test_personal_auto_workflow():
    """All step definitions are imported via conftest.py's pytest_plugins."""
    pass
```

The test function body is `pass` because all logic lives in the step definitions.

### 5.4 Data-Driven Testing

#### JSON-First Approach (Primary)

The framework uses `testdata/static/AutoData.json` as the primary data source.

**JSON Structure:**

```json
{
  "testCases": [
    {
      "TC_ID": "TC_ID_0001",
      "CustomerType": "Individual",
      "FirstName": "James",
      "LastName": "Smith",
      "DOB": "11/10/1992",
      "PhoneNum": "921-549-5577",
      "Email": "jsmith_{timestamp}@auto.com",
      "Address": "230 Old Taunton Ave",
      "ZIP": "01101",
      "Producer": "Janis Irey",
      "Program": "Personal Auto",
      "BillingMethod": "Direct Billed",
      "FalseInfo": "No",
      "DamageInfo": "No",
      "Gender": "Male",
      "MaritalStatus": "Married",
      "DriverStatus": "Active (rated)",
      "EmploymentCategory": "Employed",
      "SR22": "No",
      "Occupation": "Day Care",
      "LicenseStatus": "Active License",
      "Year": "2018",
      "Make": "BMW",
      "Model": "M3",
      "Spec": "Convertible 2-Door | 2WD | 4.0 Ltrs | 4x2",
      "VehicleUse": "Pleasure",
      "Ownership": "Owned",
      "PolicyCoverage": "Gold"
    }
  ]
}
```

**Naming convention:** `CamelCase` keys (e.g., `FirstName`, `BillingMethod`, `VehicleUse`).

**Why CamelCase?**
- Aligns with modern API/JSON standards
- Directly maps to method parameters without transformation
- Values are stored as **strings** to preserve leading zeros (ZIP codes, phone numbers)

**Special feature — Dynamic email via `{timestamp}`:**

The `Email` field supports a `{timestamp}` placeholder that gets replaced at runtime with the current epoch in milliseconds, ensuring unique email addresses per test run:

```python
# utils/email_util.py
def process_email(email: str) -> str:
    if "{timestamp}" in email:
        timestamp = str(int(time.time() * 1000))
        return email.replace("{timestamp}", timestamp)
    return email
```

`"jsmith_{timestamp}@auto.com"` → `"jsmith_1707753600000@auto.com"`

#### Excel Support (Legacy)

The framework retains backward compatibility with Excel via `utils/excel_reader.py`:

```gherkin
Given the data is loaded "testdata/static/AutoData.xlsx", "Sheet1", "TC_ID_0001"
```

- Uses `pandas` + `openpyxl` engine
- Reads all values as strings (`dtype=str`)
- Normalizes column headers to uppercase + stripped
- Expects `header_row=1` (second row in Excel is the header; first row is a title)

#### How Data Flows Through the Framework

1. **Feature file** specifies data source and `TC_ID`
2. **`data_steps.py`** loads + filters → returns single row as `test_data` dict (via `target_fixture="test_data"`)
3. **`conftest.py`** aliases it: `data` fixture wraps `test_data`
4. **Step definitions** receive `test_data` as a fixture parameter
5. **Page objects** receive the dict in method arguments (e.g., `fill_driver_info(self, data)`)

### 5.5 Fixtures & Dependency Injection

#### Global Fixtures (`conftest.py`)

The root `conftest.py` manages the entire Playwright lifecycle:

| Fixture | Scope | Description |
|---|---|---|
| `log` | session | Logger instance via `setup_logger("PlaywrightTest")` |
| `browser_name` | session | Reads `--browser` CLI option (default: `chromium`). Valid: `chromium`, `firefox`, `webkit`, `chrome`, `msedge` |
| `playwright` | session | Playwright instance (context manager) |
| `browser` | session | Launched browser (headless=False, slow_mo=100). For `chrome`/`msedge`, uses Chromium engine with the corresponding channel |
| `context` | function | Fresh browser context per test (full-screen viewport) |
| `page` | function | Fresh page per test |
| `data` | function | Alias for `test_data` (from data_steps.py) |

**Plugin registration** — step definition modules are imported via:

```python
pytest_plugins = [
    "fixtures.ui_fixtures",
    "ui.steps.auth_steps",
    "ui.steps.data_steps",
    "ui.steps.auto_workflow_steps",
]
```

#### Page Object Fixtures (`fixtures/ui_fixtures.py`)

Each page object has a corresponding fixture that handles instantiation:

```python
@pytest.fixture
def login_page(page):
    return LoginPage(page)

@pytest.fixture
def vehicle_info_page(page):
    return VehicleInfoPage(page)
```

This ensures page objects receive the current test's `page` and are freshly created per test.

#### Fixture Lifecycle Diagram

```
Session Start
  └── log, playwright, browser (created once, shared)
      │
      ├── Test 1
      │   └── context → page → [login_page, customer_page, ...] → test_data
      │       (all destroyed after test)
      │
      ├── Test 2
      │   └── context → page → [login_page, customer_page, ...] → test_data
      │
      └── ...
Session End
  └── browser.close(), policy trend chart generated
```

---

## 6. Writing Tests — Step by Step

### Step 1: Add Test Data

Add a new entry to `testdata/static/AutoData.json`:

```json
{
  "TC_ID": "TC_ID_0011",
  "CustomerType": "Individual",
  "FirstName": "NewUser",
  "LastName": "TestLast",
  "DOB": "03/15/1988",
  ...
}
```

### Step 2: Create or Update the Feature File

Add a new `TC_ID` row to the `Examples` table:

```gherkin
Examples:
  | TC_ID      |
  | TC_ID_0001 |
  | TC_ID_0011 |   # ← new test case
```

Or create an entirely new `.feature` file in `ui/features/`.

### Step 3: Write Step Definitions (if needed)

If your test requires new steps, add them to the appropriate step file in `ui/steps/`:

```python
# ui/steps/auto_workflow_steps.py
@when("I provide some new step")
def some_new_step(some_page, test_data, log):
    log.info("Executing new step...")
    some_page.do_something(test_data)
```

### Step 4: Create Page Objects (if needed)

If interacting with a new page:

```python
# ui/pages/auto/new_page.py
from ui.pages.common.base_page import BasePage

class NewPage(BasePage):
    def __init__(self, page):
        super().__init__(page)
        self.some_field = page.get_by_role("textbox", name="Some Field")

    def do_something(self, data):
        self.some_field.fill(data["SomeField"])
```

### Step 5: Register the Fixture

Add a fixture in `fixtures/ui_fixtures.py`:

```python
from ui.pages.auto.new_page import NewPage

@pytest.fixture
def new_page(page):
    return NewPage(page)
```

### Step 6: Create the Test Entry Point

```python
# ui/tests/test_new_scenario.py
from pytest_bdd import scenario

@scenario('../features/new_feature.feature', 'My new scenario')
def test_new_scenario():
    pass
```

### Step 7: Run and Verify

```bash
pytest ui/tests/test_new_scenario.py -v --headed
```

---

## 7. Test Data Management

### JSON Data File Keys Reference

The following keys are used in `AutoData.json` and consumed by page objects:

| Key | Used By | Example Value |
|---|---|---|
| `TC_ID` | Data loader (filter) | `"TC_ID_0001"` |
| `CustomerType` | CustomerPage | `"Individual"` |
| `FirstName` | CustomerPage | `"James"` |
| `LastName` | CustomerPage | `"Smith"` |
| `DOB` | CustomerPage | `"11/10/1992"` |
| `PhoneNum` | CustomerPage | `"921-549-5577"` |
| `Email` | CustomerPage (via `process_email`) | `"jsmith_{timestamp}@auto.com"` |
| `Address` | CustomerPage | `"230 Old Taunton Ave"` |
| `ZIP` | CustomerPage | `"01101"` |
| `Producer` | QuoteRegistrationPage | `"Janis Irey"` |
| `EffDateOffset` | QuoteRegistrationPage | `0` (days from today) |
| `Program` | QuoteRegistrationPage | `"Personal Auto"` |
| `BillingMethod` | QuoteSummaryPage | `"Direct Billed"` |
| `FalseInfo` | QuoteSummaryPage | `"No"` |
| `DamageInfo` | QuoteSummaryPage | `"No"` |
| `Gender` | DriverInfoPage | `"Male"` |
| `MaritalStatus` | DriverInfoPage | `"Married"` |
| `DriverStatus` | DriverInfoPage | `"Active (rated)"` |
| `EmploymentCategory` | DriverInfoPage | `"Employed"` |
| `Occupation` | DriverInfoPage | `"Day Care"` |
| `SR22` | DriverInfoPage | `"No"` |
| `LicenseStatus` | DriverInfoPage | `"Active License"` |
| `Year` | VehicleInfoPage | `"2018"` |
| `Make` | VehicleInfoPage | `"BMW"` |
| `Model` | VehicleInfoPage | `"M3"` |
| `Spec` | VehicleInfoPage | `"Convertible 2-Door \| 2WD \| 4.0 Ltrs \| 4x2"` |
| `VehicleUse` | VehicleInfoPage | `"Pleasure"` / `"Business"` / `"Commute"` |
| `Ownership` | VehicleInfoPage | `"Owned"` |
| `PolicyCoverage` | PolicyTermPage | `"Gold"` / `"Silver"` |

### Adding a New Data Field

1. Add the key to the JSON test case object
2. Update the consuming Page Object method to read `data["NewKey"]`
3. If the field requires special handling, add a utility function in `utils/`

---

## 8. Execution & CLI Reference

### Basic Commands

```bash
# Run all tests
pytest

# Run with visible browser
pytest --headed

# Run specific test file
pytest ui/tests/test_auto_workflow.py

# Run by marker
pytest -m smoke
pytest -m auto
pytest -m login
pytest -m regression

# Run on a specific browser
pytest --browser chromium
pytest --browser firefox
pytest --browser webkit
pytest --browser chrome     # Uses system-installed Google Chrome
pytest --browser msedge     # Uses system-installed Microsoft Edge

# Run with verbose output
pytest -v

# Run a specific TC_ID only (by test node ID)
pytest ui/tests/test_auto_workflow.py -k "TC_ID_0001"
```

### Combined Examples

```bash
# Smoke tests, headed, on Firefox, with Allure
pytest -m smoke --headed --browser firefox --alluredir=allure-results

# Run login tests on Edge
pytest -m login --browser msedge

# Run smoke tests on Chrome
pytest -m smoke --browser chrome

# Full auto regression, parallel (4 workers)
pytest -m auto -n 4

# With coverage report
pytest --cov=./ --cov-report=html

# With timeout (300s per test)
pytest --timeout=300
```

### Default Options (from `pytest.ini`)

These are applied automatically on every run:

```ini
addopts =
    -v                          # Verbose output
    -ra                         # Show extra test summary
    --showlocals                # Show local vars in tracebacks
    --strict-markers            # Fail on unknown markers
    --capture=fd                # Capture file descriptors
    --continue-on-collection-errors
    --html=reports/pytest_report.html
    --self-contained-html
    --alluredir=allure-results
```

### Available Markers

| Marker | Description |
|---|---|
| `@pytest.mark.smoke` | Critical smoke tests (quick validation) |
| `@pytest.mark.auto` | Personal Auto insurance tests |
| `@pytest.mark.regression` | Full regression suite |
| `@pytest.mark.login` | Login-specific tests |
| `@pytest.mark.homeowner` | Homeowner insurance tests |

---

## 9. Reporting

### Allure Reports (Primary)

Allure provides rich, interactive HTML reports with:

- **Step-by-step execution breadcrumbs** — every `@allure.step` is visible
- **Automatic failure screenshots** — attached as PNG images
- **Parameterized test data** — shows which `TC_ID` was used
- **Execution timeline** — visual representation of test duration
- **Categories & trends** — track flaky tests over time

```bash
# Generate and open Allure report
allure serve allure-results

# Or generate static report
allure generate allure-results -o allure-report --clean
```

### pytest-html Reports (Secondary)

A standalone HTML report is generated automatically at `reports/pytest_report.html` (configured in `pytest.ini`). Useful for quick sharing without Allure CLI.

---

## 10. Logging

### Architecture

The framework uses Python's built-in `logging` module with file-based output:

```
logs/
├── test_run_2026-02-12_10-30-45.log
├── test_run_2026-02-12_14-22-10.log
└── ...
```

### Configuration (`utils/logger.py`)

- **Level:** `DEBUG` (captures everything)
- **Format:** `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- **Encoding:** UTF-8
- **File naming:** `test_run_YYYY-MM-DD_HH-MM-SS.log` (unique per session)
- **Handler deduplication:** Checks `logger.handlers` to prevent duplicate entries in the same session

### Console Logging (`pytest.ini`)

Live logging is enabled in the console:

```ini
log_cli = true
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)s] %(message)s (%(filename)s:%(lineno)s)
log_cli_date_format = %Y-%m-%d %H:%M:%S
```

### Using the Logger

Every `BasePage` subclass automatically gets a logger:

```python
class BasePage:
    def __init__(self, page):
        self.page = page
        self.logger = setup_logger(self.__class__.__name__)
```

In step definitions, use the `log` fixture:

```python
@when("I provide Driver Details")
def provide_driver_details(driver_info_page, test_data, log):
    log.info("Filling driver details...")
    driver_info_page.fill_driver_info(test_data)
```

---

## 11. Screenshot Capture on Failure

Screenshots are automatically captured when a test fails, via the `pytest_runtest_makereport` hook in `conftest.py`:

### How It Works

1. The hook intercepts the test report after the `call` phase
2. If `report.failed` is `True`, it retrieves the `page` fixture
3. Takes a full-page screenshot as bytes (`page.screenshot(full_page=True)`)
4. Attaches the screenshot directly to the Allure report as a PNG

### What Gets Captured

- **Full-page screenshot** (not just the viewport)
- **Named** with the test function name: `Failure_test_personal_auto_workflow`
- **Attached to Allure** — visible in the report under the failed test

### Fallback Behavior

- If `page` fixture is not available (e.g., test failed during setup), a warning is printed
- No file is saved to disk — the screenshot exists only in the Allure report as an attachment

---

## 12. Business Reporting (Policy Reporter)

After all tests complete, the framework generates business analytics from the policy data extracted during test runs.

### Session Finish Hook

```python
def pytest_sessionfinish():
    generate_trend_chart("policy_summary/policy_reports.csv")
```

### Generated Reports

| Report | File | Description |
|---|---|---|
| Policy CSV | `policy_summary/policy_reports.csv` | Append-mode CSV with all policy details |
| Premium Trend Chart | `policy_summary/policy_report.png` | Bar chart: Mean premium by coverage × vehicle use |
| Status Distribution | `policy_summary/status_distribution.png` | Pie chart: Policy status breakdown |

### Data Collected Per Policy

The `auto_workflow_steps.py` → `read_extract_summary` step extracts:

- Timestamp, Policy Number, Program, Customer Name
- Status, Payment Method, Primary Jurisdiction
- Total Policy Premium, Payment Plan
- Employment Category, Vehicle Use, Ownership, Policy Coverage Option

---

## 13. CI/CD — Jenkins Pipeline

### Pipeline Stages

The `Jenkinsfile` defines a declarative pipeline with these stages:

| Stage | Actions |
|---|---|
| **Checkout** | `checkout scm` — pulls latest code from repository |
| **Setup Environment** | Creates venv, installs `requirements.txt`, installs `chromium` browser |
| **Run Tests** | Activates venv, cleans old results, runs `pytest` with browser and path parameters |
| **Generate Coverage Report** | Runs `pytest --cov=./ --cov-report=html` |

### Jenkins Parameters

| Parameter | Default | Description |
|---|---|---|
| `BROWSER` | `chromium` | Browser engine (`chromium`, `firefox`, `webkit`, `chrome`, `msedge`) |
| `TEST_PATH` | `ui/` | Directory or file to test |

### Credentials

Credentials are managed via Jenkins Credentials store:

```groovy
environment {
    PARTNER_NUM = '0'
    AUTH = credentials('oneshield-login')   // Jenkins credential ID
    USERNAMEE = "${env.AUTH_USR}"
    PASSWORD = "${env.AUTH_PSW}"
}
```

### Post Actions

Allure report is always generated in the `post > always` block:

```groovy
post {
    always {
        allure includeProperties: false, jdk: '', results: [[path: 'allure-results']]
    }
}
```

### Running in Jenkins

1. Create a Pipeline job in Jenkins
2. Point SCM to the repository
3. Jenkins will auto-detect the `Jenkinsfile`
4. Optionally override `BROWSER` and `TEST_PATH` parameters per build

---

## 14. Configuration Files Reference

### `pytest.ini`

| Setting | Value | Purpose |
|---|---|---|
| `python_files` | `test_*.py *_test.py` | Test file discovery patterns |
| `python_classes` | `Test*` | Test class discovery pattern |
| `python_functions` | `test_*` | Test function discovery pattern |
| `bdd_features_base_dir` | `ui/features/` | Root for `.feature` file resolution |
| `markers` | `auto`, `smoke`, `regression`, `login`, `homeowner` | Custom test markers |
| `addopts` | see [CLI Reference](#8-execution--cli-reference) | Default command-line options |
| `log_cli` | `true` | Enable real-time console logging |
| `log_cli_level` | `INFO` | Console log verbosity |

### `config/environments.yaml`

Reserved for environment-specific configuration (URLs, timeouts per environment). Currently empty — environment config is managed via `.env`.

### `config/secrets.yaml`

Reserved for sensitive configuration. Currently empty — secrets are managed via `.env` and Jenkins credentials.

---

## 15. Utility Modules Reference

### `utils/json_reader.py` — `DataLoader`

```python
DataLoader.get_data("testdata/static/AutoData.json")
# Returns: dict (the full JSON object)
```

- Handles both absolute and relative paths (relative to project root)
- Uses `pathlib.Path` for cross-platform compatibility
- Raises `FileNotFoundError` with detailed message if file is missing

### `utils/excel_reader.py` — `ExcelReader`

```python
ExcelReader.get_excel_data("path/to/file.xlsx", sheet_name="Sheet1", header_row=1)
# Returns: list[dict] (each row as a dictionary)
```

- `header_row=1` — skips a title row; your column headers should be on the second row
- All values read as `str` to preserve leading zeros
- Columns are normalized to `UPPERCASE` + stripped whitespace
- Includes a `debug=True` mode for troubleshooting
- Validates that `TC_ID` column exists

### `utils/email_util.py` — `process_email`

```python
process_email("user_{timestamp}@test.com")
# Returns: "user_1707753600000@test.com"
```

### `utils/file_writer.py` — `save_summary_to_csv`

```python
save_summary_to_csv({"Policy Number": "P12345", "Status": "Active"})
# Appends to: policy_summary/policy_reports.csv
```

- Creates `policy_summary/` directory if it doesn't exist
- Writes headers only for new files
- Always appends (mode `'a'`)

### `utils/policy_reporter.py`

```python
generate_trend_chart("policy_summary/policy_reports.csv")
# Output: policy_summary/policy_report.png

generate_status_pie_chart("policy_summary/policy_reports.csv")
# Output: policy_summary/status_distribution.png
```

- Cleans currency values (removes `$`, `,`, etc.)
- Filters out zero/negative premiums
- Groups by coverage option × vehicle use

### `utils/logger.py` — `setup_logger`

```python
logger = setup_logger("MyComponent")
logger.info("Something happened")
logger.debug("Detailed debug info")
```

### Reserved (Empty) Modules

- `utils/waiters.py` — For custom wait strategies beyond Playwright's built-in waits
- `utils/assertions.py` — For domain-specific assertion helpers
- `utils/screenshot_helper.py` — For advanced screenshot utilities

---

## 16. Coding Standards & Best Practices

### Locators

| DO | DON'T |
|---|---|
| `page.get_by_role("button", name="login")` | `page.locator("//button[@id='btn-login']")` |
| `page.get_by_role("combobox", name="Gender*")` | `page.locator("#gender-select")` |
| `page.get_by_label("First Name")` | `page.locator("input[name='fname']")` |
| Use `re.compile(name, re.I)` for flexibility | Hardcode exact case-sensitive strings |

### Data Handling

| DO | DON'T |
|---|---|
| Pass `data` dict from step → page method | Hardcode data inside page objects |
| Use `TC_ID` for filtering test cases | Reference rows by index |
| Store values as strings in JSON | Use numeric types for ZIP/phone (loses leading zeros) |
| Use `{timestamp}` placeholder for unique emails | Generate random data inline |

### Page Objects

| DO | DON'T |
|---|---|
| Inherit from `BasePage` | Create standalone page classes |
| Define locators in `__init__` | Define locators inside action methods |
| One method per user action | Mega-methods doing 10 things |
| Decorate with `@allure.step` | Skip step decoration (invisible in reports) |
| Add `self.logger.info(...)` calls | Use `print()` for debugging |
| Add docstrings to all public methods | Leave methods undocumented |

### Step Definitions

| DO | DON'T |
|---|---|
| Keep steps reusable across features | Write feature-specific steps |
| Use the `log` fixture for tracing | Use `print()` statements |
| Accept `test_data` via fixture injection | Load data inside step definitions |
| Group related steps in one file | Scatter steps across many files |

### General

| DO | DON'T |
|---|---|
| Use `time.sleep()` only as last resort | Sprinkle `time.sleep(5)` everywhere |
| Prefer `page.expect_response()` for waits | Use arbitrary timeouts |
| Use `safe_fill()` for problematic inputs | Assume `.fill()` always works |
| Register new step files in `conftest.py`'s `pytest_plugins` | Forget to register and wonder why steps aren't found |

---

## 17. Troubleshooting

### Common Issues

| Issue | Cause | Fix |
|---|---|---|
| `TC_ID 'X' not found` | Typo in feature file or missing JSON entry | Check `Examples` table matches `AutoData.json` |
| `Step definition not found` | Step file not registered | Add to `pytest_plugins` in `conftest.py` |
| `TimeoutError` on element | Element not loading, wrong locator | Use `--headed` to visually debug; check locator |
| `Page fixture not available` | Test failed during setup (before page created) | Check `Background` steps (login) for failures |
| Browser not installed | Playwright binaries missing | Run `playwright install` |
| `USERNAME` env var conflict | Windows system variable | Use `USERNAMEE` (double E) |
| `FileNotFoundError` for JSON | Relative path resolution | Ensure working directory is project root |
| Excel `TC_ID` column not found | Wrong `header_row` in ExcelReader | Set `header_row` matching your Excel layout |
| Duplicate log entries | Logger handlers accumulating | `setup_logger` already guards against this |
| `POM classes not receiving data` | Forgot `target_fixture="test_data"` in data step | Ensure `@given` decorator includes `target_fixture` |

### Debugging Tips

1. **Run headed**: `pytest --headed` to see the browser
2. **Slow down**: `slow_mo=500` is set in browser launch (adjustable in `conftest.py`)
3. **Single test**: `pytest -k "TC_ID_0001"` to isolate
4. **Check logs**: Look in `logs/test_run_*.log` for DEBUG-level detail
5. **Allure steps**: Failed step is highlighted in the Allure report with the exact error
6. **Network waits**: `VehicleInfoPage` uses `page.expect_response("**/FieldProcessorServlet*")` — check network tab if this times out

---

## 18. Extending the Framework

### Adding a New Insurance Product (e.g., Commercial Auto)

1. **Create page directory**: `ui/pages/commercial/`
2. **Create page objects**: Inherit from `BasePage`, define locators and methods
3. **Create fixtures**: Add to `fixtures/ui_fixtures.py`
4. **Create steps**: `ui/steps/commercial_steps.py`
5. **Register steps**: Add to `pytest_plugins` list in `conftest.py`
6. **Create feature file**: `ui/features/commercial_auto.feature`
7. **Create test file**: `ui/tests/test_commercial_auto.py`
8. **Add test data**: New JSON file or new section in existing data
9. **Add marker**: Register in `pytest.ini` under `markers`

### Adding API Tests (Future)

The project structure has placeholders from the scaffold (`create_folders.py`):

```
api/
├── clients/
│   ├── base_client.py
│   ├── policy_client.py
│   └── auth_client.py
├── schemas/
└── tests/
```

### Using Saved Authentication State

The framework stores browser auth state in `testdata/auth_state.json`. This can be used to skip login for subsequent tests:

```python
# Load saved state into a new context
context = browser.new_context(storage_state="testdata/auth_state.json")
```

---

**Last Updated**: February 12, 2026
