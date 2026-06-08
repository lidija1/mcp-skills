# INFORCE Test Automation Dashboard

The dashboard is a local web app for running insurance automation workflows from a browser. It sits on top of this repository's Playwright + pytest-bdd framework and the MCP-style tooling under `mcp_tools/`.

It provides two main work areas:

- **Policy Flow**: generate customer profiles and run end-to-end policy workflows.
- **UW Validator**: run underwriting rule audits, single-rule tests, and custom edge cases.

The app is intentionally local-first. The frontend runs with Vite, the backend runs with FastAPI, and the backend calls the existing Python automation code in this repository.

## App Structure

```text
dashboard/
|- README.md
|- start-backend.bat
|- start-frontend.bat
|- backend/
|  |- main.py
|  `- requirements.txt
`- frontend/
   |- package.json
   |- vite.config.js
   |- src/
   |  |- App.jsx
   |  |- index.css
   |  |- utils/api.js
   |  `- components/
   |     |- Header.jsx
   |     |- PolicyPanel.jsx
   |     |- UWPanel.jsx
   |     |- JobSidebar.jsx
   |     `- ReportModal.jsx
   `- dist/
```

## Prerequisites

Install the repository prerequisites first:

```powershell
pip install -r requirements.txt
playwright install
```

Install dashboard backend dependencies:

```powershell
pip install -r dashboard/backend/requirements.txt
```

Install frontend dependencies:

```powershell
cd dashboard/frontend
npm install
```

The app also needs the root `.env` used by the automation framework:

```env
PARTNER_NUM=0
USERNAMEE=your_username
PASSWORD=your_password
OPENAI_API_KEY=your_key
```

`USERNAMEE` intentionally has a double `E`, matching the rest of the framework.

## Running Locally

Start the backend from the repository root:

```powershell
python dashboard/backend/main.py
```

The backend starts on:

```text
http://localhost:8000
```

Start the frontend:

```powershell
cd dashboard/frontend
npm run dev
```

The frontend starts on:

```text
http://localhost:5173
```

The Vite dev server proxies `/api/*` requests to `http://localhost:8000`.

You can also use the batch files:

```powershell
dashboard/start-backend.bat
dashboard/start-frontend.bat
```

## Policy Flow

Policy Flow supports these lines of business:

- Personal Auto
- Homeowner

Available actions:

- **Quick Policy Test**: takes a natural-language customer description, generates a structured persona, and immediately runs the policy workflow.
- **Build Customer Profile**: generates persona JSON only.
- **Run Policy Journey**: runs the policy workflow using pasted persona JSON.
- **Test Multiple Customers**: runs several generated scenarios back-to-back.
- **Browse Customer Types**: shows supported persona archetypes for the selected line of business.

Policy flow execution uses:

```text
mcp_tools/policy_flow_generator/
```

The backend routes into these runners:

```text
mcp_tools/policy_flow_generator/runners/auto_runner.py
mcp_tools/policy_flow_generator/runners/homeowner_runner.py
```

## UW Validator

UW Validator supports:

- Viewing registered UW rule libraries by line of business.
- Running all cases for one line of business.
- Running cases for one selected rule.
- Creating and running a custom boundary scenario.
- Launching a full audit across all registered LOBs.

UW execution uses:

```text
mcp_tools/uw_rules_validator/
```

Rules are registered in:

```text
mcp_tools/uw_rules_validator/rule_registry.py
```

## Job History

Every action that can take time creates a backend job. The frontend shows these jobs in the right-side Job History panel.

Job states:

- `running`
- `done`
- `error`

The frontend polls running jobs every few seconds and updates the job cards when the backend marks them complete.

Click a completed or failed job to open the report viewer. The report modal supports:

- Markdown reports.
- Generated JSON profiles.
- Error details.
- Copy-to-clipboard.
- Status banners for passed, warning/review, and failed reports.

## Concurrency

The frontend can submit multiple jobs. Each job receives its own ID and appears independently in Job History.

Backend execution uses FastAPI background tasks. Browser workflow execution is wrapped in a single-worker thread executor per job:

```python
concurrent.futures.ThreadPoolExecutor(max_workers=1)
```

This isolates each browser run from the FastAPI event loop. Practical concurrency still depends on local machine resources, browser availability, credentials/session behavior, and how the target application handles simultaneous logins.

For long-running audits, avoid launching too many jobs at once unless you intentionally want to stress local resources.

## Backend API

Health and jobs:

```text
GET  /api/health
GET  /api/jobs
GET  /api/jobs/{job_id}
```

Policy flow:

```text
GET  /api/policy/archetypes?lob=auto|homeowner
POST /api/policy/create-persona
POST /api/policy/run-flow
POST /api/policy/quick-run
POST /api/policy/batch-run
```

UW validator:

```text
GET  /api/uw/rules?lob=auto|homeowner
POST /api/uw/audit
POST /api/uw/rule-cases
POST /api/uw/custom-boundary
POST /api/uw/full-audit
```

Example quick run payload:

```json
{
  "lob": "homeowner",
  "description": "High-value home with prior water loss and refused coverage"
}
```

Example run-flow payload:

```json
{
  "lob": "auto",
  "persona_json": "{\"TC_ID\":\"AI_123456\",\"CustomerType\":\"Individual\"}"
}
```

## Frontend Design

The current frontend uses a light Material-inspired layout:

- Fixed top app bar.
- Left navigation rail.
- Main content pane.
- Right job history panel.
- Card-based forms with lucide icons.
- Light report modal for job output.

Primary files:

```text
dashboard/frontend/src/App.jsx
dashboard/frontend/src/index.css
dashboard/frontend/src/components/Header.jsx
dashboard/frontend/src/components/PolicyPanel.jsx
dashboard/frontend/src/components/UWPanel.jsx
dashboard/frontend/src/components/JobSidebar.jsx
dashboard/frontend/src/components/ReportModal.jsx
```

The app uses React, Vite, Tailwind base layers, and custom CSS in `src/index.css`.

## Data And Timestamp Handling

The automation framework supports dynamic email values with:

```text
{timestamp}
```

Runtime processing lives in:

```text
utils/email_util.py
ui/pages/common/customer_page.py
```

For standard UI flows, `CustomerPage.enter_email()` replaces `{timestamp}` before filling the Email field.

Quick policy tests rely on the AI-generated persona containing a valid email field. A unique email does not necessarily prevent duplicate-customer search results if the target application matches on name, DOB, phone, or address.

## Build

Build the frontend:

```powershell
cd dashboard/frontend
npm run build
```

Preview the production build:

```powershell
npm run preview
```

The production assets are written to:

```text
dashboard/frontend/dist/
```

## Troubleshooting

### Backend Offline

If the frontend shows `Backend offline`, start the backend:

```powershell
python dashboard/backend/main.py
```

Then refresh the frontend.

### AI Generation Fails

Check the root `.env`:

```env
OPENAI_API_KEY=...
```

The backend forces OpenAI when `OPENAI_API_KEY` is present in `.env`. If no AI key is configured, persona generation returns an error.

### Browser Flow Fails

Confirm the normal Playwright framework works:

```powershell
pytest ui/tests/test_auto_workflow.py -v
```

Also confirm credentials:

```env
PARTNER_NUM=0
USERNAMEE=your_username
PASSWORD=your_password
```

### Duplicate Customer Records

Dynamic email timestamping helps, but the target application may still find duplicate records based on:

- first name
- last name
- DOB
- phone
- address
- ZIP

If quick tests repeatedly use the same prompt, AI-generated identity fields can be similar. Consider normalizing generated personas before execution if uniqueness is required for every run.

### Port Already In Use

Frontend default:

```text
5173
```

Backend default:

```text
8000
```

If a port is busy, stop the existing process or update the relevant Vite/FastAPI configuration.

### Vite Build Spawn Error On Windows

If `npm run build` fails with an `esbuild` spawn permission error, rerun from a normal terminal with sufficient permissions.

## Development Notes

- Keep API calls in `frontend/src/utils/api.js`.
- Keep UI state inside React components unless shared state becomes necessary.
- Keep backend orchestration in `backend/main.py`.
- Keep browser interaction logic in the existing page objects and MCP runners.
- Do not put Playwright selectors into the dashboard frontend.
- Preserve the framework's existing env var names, especially `USERNAMEE`.

## Useful Commands

```powershell
# Backend
python dashboard/backend/main.py

# Frontend dev server
cd dashboard/frontend
npm run dev

# Frontend build
npm run build

# Targeted automation validation
pytest ui/tests/test_auto_workflow.py -v
pytest -m homeowner -v
pytest -m uw -v
```
