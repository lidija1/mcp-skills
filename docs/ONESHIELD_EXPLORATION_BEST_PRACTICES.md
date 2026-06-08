# OneShield Exploration Best Practices

This guide defines how to explore the OneShield application through this Playwright + pytest-bdd framework without repeating known mistakes. Use it when adding or debugging flows, discovering fields, stabilizing selectors, or converting app behavior into reusable page objects.

## Goals

- Learn the app incrementally and preserve that learning in the repo.
- Keep UI logic in page objects, not tests or step definitions.
- Prefer stable, reusable interactions over one-off Playwright calls.
- Record failed approaches so future work does not retry them unchanged.
- Turn confirmed discoveries into page methods, fixtures, data, and BDD steps.

## Required Reading Before Exploration

Read these in order:

1. `docs/ONESHIELD_APP_KNOWLEDGE.md`
2. `README.md`
3. `CLAUDE.md`
4. `FRAMEWORK_GUIDE.md`
5. `conftest.py`
6. `pytest.ini`
7. Relevant feature, step, fixture, and page object files for the flow

For cross-module questions, also read `graphify-out/GRAPH_REPORT.md` if present.

## Exploration Loop

Follow this loop for every screen or workflow:

1. **Prepare**
   - Identify the LOB, scenario, test data file, and current page object.
   - Check `docs/ONESHIELD_APP_KNOWLEDGE.md` for known selectors, waits, and failed approaches.
   - Start from the closest existing page method instead of writing raw test logic.

2. **Observe**
   - Use traces, screenshots, DOM inspection, and page object logging.
   - Capture the current URL, visible header, OneShield step indicator, active modal/dropdown, and spinner state.
   - Note ExtJS-generated IDs only as diagnostics unless no better selector exists.

3. **Interact**
   - Prefer `BasePage.smart_click`, `smart_fill`, `smart_type`, `answer_question`, and `spinner_wait`.
   - Keep selectors and interaction logic inside page classes.
   - Use role, label, text, stable attributes, and local container scoping before brittle XPath.
   - For ExtJS dropdowns, use existing JS-assisted visible-item selection patterns.

4. **Verify**
   - Verify the action changed the intended state, not just that the click/fill succeeded.
   - Wait for spinners/masks after navigation, rating, dropdown selection, and save/next actions.
   - Prefer targeted pytest runs before broader marker suites.

5. **Persist Learning**
   - Update `docs/ONESHIELD_APP_KNOWLEDGE.md` with confirmed behavior.
   - Record failed selectors or strategies under "Known Failed Approaches".
   - Move stable behavior into page object methods.
   - Add or update JSON test data when inputs are reusable.

## Page Object Rules

- Add new selectors and helper methods to `ui/pages/...`.
- Use step definitions only to orchestrate page object calls.
- Keep scenario wrappers in `ui/tests/` thin.
- Register new page fixtures in `ui/fixtures.py`.
- Register new step modules in `conftest.py`.
- Add new markers to `pytest.ini`.
- Reuse common page objects for login, customer, quote registration, delivery preferences, billing, and policy summary behavior.

## Selector Strategy

Prefer selectors in this order:

1. `get_by_role(...)` when roles/names are reliable.
2. `get_by_label(...)` for labeled fields.
3. Stable attributes such as `name`, `data-*`, or application-specific attributes.
4. Scoped `get_by_text(...)` within a known container.
5. CSS with stable classes and local structure.
6. XPath only when the app gives no safer option.

Avoid:

- Hard-coded ExtJS generated IDs unless documented as stable.
- Global text selectors when duplicate labels exist.
- Clicking hidden dropdown items left behind by previous ExtJS interactions.
- Sleeping instead of waiting for a concrete UI state.
- Adding selectors directly to tests.

## ExtJS Interaction Notes

OneShield uses ExtJS-style controls. Treat dropdowns, modal masks, grids, and comboboxes as stateful widgets.

For comboboxes:

- Scroll the field into view before opening.
- Click or focus the input trigger.
- Wait for a visible `.x-boundlist-item`, not merely an attached item.
- Filter items by bounding box visibility.
- Use JS-assisted click when tooltips or overlays intercept pointer events.
- Call `spinner_wait()` after selection when the app recalculates state.

For navigation:

- Wait after `Next`, `Save`, `Rate`, `Bind`, and quote/policy creation actions.
- Capture the current step/header before and after navigation.
- Treat masks/spinners as first-class blockers.

## Failure Log Discipline

Every meaningful exploration failure should be preserved in `docs/ONESHIELD_APP_KNOWLEDGE.md`:

- Date
- Page/flow
- Attempted selector or method
- Failure symptom
- Why it failed, if known
- Replacement approach

Do not repeat a failed strategy unchanged. If retrying is necessary, document what changed.

## Test Workflow

Use the narrowest useful validation first:

```powershell
pytest ui/tests/test_auto_workflow.py -v
pytest -m homeowner -v
pytest -m wc -v
```

For exploration and debugging:

```powershell
pytest --pw-trace=on --browser=chromium
pytest --headed --slow-mo=100
```

Artifacts:

- Pytest HTML: `reports/pytest_report.html`
- Allure results: `allure-results/`
- Playwright traces: `reports/traces/`

## Knowledge Update Template

Use this template in `docs/ONESHIELD_APP_KNOWLEDGE.md`:

```md
### YYYY-MM-DD - Flow/Page

**Context**
- LOB:
- Scenario:
- Test data:

**Confirmed Behavior**
- 

**Stable Selectors / Methods**
- 

**Required Waits**
- 

**Known Failed Approaches**
- Attempt:
- Symptom:
- Replacement:

**Open Questions**
- 
```

## Definition Of Done

Exploration is not done until:

- The useful finding is written to the knowledge file.
- Stable behavior is implemented in the right page object.
- Step definitions remain orchestration-only.
- Targeted validation has passed or the blocker is documented.
- Any failed approach that cost time is recorded.

