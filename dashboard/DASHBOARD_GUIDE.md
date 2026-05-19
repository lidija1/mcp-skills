# Insurance Testing Dashboard — User Guide

## Starting the Dashboard

You need two terminals running simultaneously.

**Terminal 1 — Backend** (from the project root):
```bash
python dashboard/backend/main.py
```
Runs on `http://localhost:8000`. On startup it prints which AI provider is active:
```
[INFO] AI provider: openai
```
If it prints `[WARN] No AI API key found` then check your `.env` file.

**Terminal 2 — Frontend** (from `dashboard/frontend/`):
```bash
npm run dev
```
Runs on `http://localhost:5173`. Open this URL in your browser.

> The backend must be restarted for `.env` changes to take effect.

---

## Navigation

The left sidebar has five sections:

| Nav item | What it does |
|---|---|
| **Overview** | Status summary and quick links |
| **Policy Flow** | Generate personas and run end-to-end policy flows |
| **UW Validator** | Validate underwriting rules against the live application |
| **Customers** | Reference for all customer archetypes used by the tools |

The **Jobs** sidebar on the right tracks every running and completed task. Click any completed job to open its full report.

---

## Overview

Shows live backend status (green = connected), a count of running and completed jobs for this session, and shortcut cards to the three main tools.

---

## Policy Flow Generator

Generates realistic insurance customer profiles and drives full end-to-end policy workflows in a headed browser.

### Line of Business selector

All cards respect the active LOB. Switch between **Personal Auto**, **Cyber**, and **Homeowner** before running.

---

### Quick Policy Test *(featured card)*

The fastest path. Describe a customer in plain English — the system calls the AI to build a structured profile, then immediately runs the full browser workflow.

**How to use:**
1. Pick a LOB
2. Type a customer description (examples are shown as placeholders)
3. Click **Run Policy Test**
4. Watch the job appear in the right sidebar — click it when done to read the report

**Example inputs:**
- Auto: *"A 23-year-old driver with an SR-22 on a leased BMW, two at-fault accidents in the past 3 years"*
- Cyber: *"A fintech startup with 80 employees handling card data, no prior cyber coverage, remote workforce"*
- Homeowner: *"A homeowner with a 22-year-old roof in a flood zone, prior water damage claim two years ago"*

**Runtime:** ~2–3 minutes (AI call + browser flow)

---

### Build Customer Profile

Calls only the AI step — produces a structured JSON profile without running the browser. Use this when you want to inspect or edit test data before running the flow.

**How to use:**
1. Describe the customer
2. Click **Build Profile**
3. The JSON appears in the job report — copy it for use in Run Policy Journey

**Runtime:** ~5–10 seconds

---

### Run Policy Journey

Takes the JSON from Build Customer Profile and runs it through the browser workflow.

**How to use:**
1. Paste the persona JSON from a previous Build Profile job
2. Click **Run Journey**

**Runtime:** ~90–120 seconds

---

### Test Multiple Customers (Batch)

Runs several policy scenarios back-to-back. Useful for regression sweeps or comparing how different profiles are treated.

**How to use:**
1. Each row has a LOB selector + description field
2. Click **Add Customer** to add more rows (max 25)
3. Click **Test All Customers**

The report shows a summary table with pass/fail/bind status for each scenario.

**Runtime:** ~2–3 minutes per customer

---

## UW Rules Validator

Runs pre-defined edge-case test scenarios against the live application and reports rule violations — false approvals (risky profile wasn't flagged), false referrals (clean profile incorrectly flagged), wrong condition counts, and flow errors.

### Line of Business selector

Works the same as in Policy Flow — pick your LOB first.

---

### View Rule Library

Expands a table of all registered underwriting rules for the selected LOB: rule ID, name, severity, and number of test cases. Use this to understand what is being tested before running an audit.

Click **View Rules** to expand, click again to collapse.

---

### Run Department Audit

Runs every pre-defined test case for one LOB. This is the main validation sweep.

**Runtimes:**
- Auto: ~15–30 min
- Cyber: ~10–20 min
- Homeowner: ~10–20 min

The report groups results by rule and highlights any mismatches.

---

### Test One Rule

Runs only the test cases belonging to a single underwriting rule. Use this to investigate a specific rule after a department audit flags it.

**How to use:**
1. Select a rule from the dropdown — a description and severity appear below
2. Click **Test Rule**

---

### Test Edge Case

Provide your own risk scenario, declare what you expect to happen, and validate whether the application agrees.

**How to use:**
1. Describe the risk scenario in plain English
2. Set **Expected outcome**: `UW Referral` or `Policy Bound`
3. Optionally add **Expected condition text** — substrings you expect to appear in the UW conditions list (e.g. `"SR-22"`, `"suspended license"`)
4. Click **Test Edge Case**

The report tells you whether the outcome matched and which expected conditions were found or missing.

---

### Full System Audit

Runs every test case across Auto, Cyber, and Homeowner in one sweep.

**Runtime:** 30–45 minutes. Best started and left running — check the Jobs sidebar for completion.

---

## Customer Types Reference

A read-only panel documenting all customer archetypes used by the automated tools. Useful for understanding what kind of profile the AI generates for a given LOB.

Browse by LOB — each archetype card shows:
- Risk level (Clean / Elevated / High / Very High)
- Age range or business type
- What underwriting rules the profile is designed to trigger
- When to use it

---

## Jobs Sidebar

Every action that launches a browser or calls the AI creates a job entry in the right sidebar:

| Status | Meaning |
|---|---|
| Running (spinner) | Background task is active |
| Done (green) | Completed — click to open the full report |
| Error (red) | Failed — click to see the error message |

Jobs persist for the current browser session. Refreshing the page clears the sidebar (jobs still ran on the backend).

---

## Common Workflows

**I want to validate that a new policy flow works end-to-end:**
→ Policy Flow → Quick Policy Test → describe the customer → read the report

**I want to generate test data I can reuse:**
→ Policy Flow → Build Customer Profile → copy the JSON → paste it anywhere

**I want to check if a specific UW rule fires correctly:**
→ UW Validator → Test One Rule → select the rule → read the report

**I want to test a scenario the pre-built cases don't cover:**
→ UW Validator → Test Edge Case → describe the scenario → set expected outcome → add expected condition text
