# OneShield App Knowledge

This is the living memory for OneShield app exploration. Update it after every useful discovery so future agents and sessions do not repeat failed approaches.

## Global Facts

- The app uses ExtJS-style controls, masks, comboboxes, grids, and generated DOM.
- Reuse `BasePage.smart_click`, `smart_fill`, `smart_type`, `answer_question`, and `spinner_wait`.
- Keep selectors and UI interaction details inside page objects.
- Use JSON test data under `testdata/static/` as the primary reusable input source.
- Preserve the `USERNAMEE` environment variable name.

## General Liability Notes

- General Liability now has a dedicated feature/test pair under `ui/features/general_liability/` and `ui/tests/test_general_liability.py`.
- The flow is split across separate page objects for policy information, coverage and limits, liability location list, and rating basis/classification.
- The page split maps to `GeneralLiabilityBasicPolicyInformationPage`, `GeneralLiabilityCoverageAndLimitsPage`, `GeneralLiabilityLiabilityLocationListPage`, and `GeneralLiabilityRatingBasisAndClassificationPage`.
- The flow covers policy information, coverage and limits, liability location list, rating basis/classification, rate quote, request issue, billing plan, and bind.
- The billing plan step now supports `Payer Currency` before `Payment Plan` so the GL flow can follow the live UI sequence.
- Billing-plan comboboxes should use the shared `BasePage.select_extjs_option` helper; the earlier custom visible-boundlist wait was too stale for the live GL page.
- Save/rating actions use OneShield mask waits and also attempt to observe `FieldProcessorServlet` responses when fields trigger backend recalculation.
- The current data file uses `Annual` audit frequency, `Massachusetts` for the liability location, `Norton` for the rendered city node, `501` class code, `10015: Amusement Centers` for the class description, and `100000` exposure.
- Live validation showed the liability location tree renders `Massachusetts > Norton` for the current sample address, so `LiabilityCity` should be `Norton` for that scenario rather than the customer mailing city.
- The GL class-description dropdown expects the full visible option text, for example `10015: Amusement Centers`, not the shorthand `: Amusement Centers`.
- Live validation of `ui/tests/test_general_liability.py::test_general_liability_creation[TC_ID_0001]` passed end to end after those data and selector fixes.

## Known Interaction Patterns

### ExtJS Dropdowns

- Scroll dropdown fields into view before opening.
- Wait for visible bound-list items by checking bounding boxes.
- Ignore stale attached `.x-boundlist-item` nodes from previous dropdowns.
- Use JS-assisted clicking when overlays intercept Playwright pointer events.
- Wait for spinners after selection if the field affects downstream state.

### Navigation

- After `Next`, `Save`, `Rate`, `Bind`, and quote/policy creation actions, wait for masks/spinners and verify the target page state.
- Capture current page header, URL, and OneShield step indicator when diagnosing navigation issues.

## Known Failed Approaches

Record failed approaches here. Do not retry them unchanged.

| Date | Flow/Page | Failed approach | Symptom | Replacement |
|---|---|---|---|---|
| 2026-05-05 | Homeowner feature docs | `* I click the Quotes buttoca` decorative Gherkin bullet | pytest-bdd treated the bullet as an executable step and failed before homeowner pages | Correct the text to the registered no-op step `I click the Quotes button` |
| 2026-05-05 | Quote Registration / Program | `get_by_role("option", name="Homeowner", exact=True).click()` after opening ExtJS combobox | Timed out waiting for the option even though the field was present | Use visible `.x-boundlist-item` bounding-box filtering and JS click, then wait for OneShield loaders |

## Confirmed Pages And Flows

Add confirmed behavior below as exploration progresses.

### 2026-06-07 - Cyber Reinsurance And Inspection Discovery

**Context**
- LOB: Cyber
- Probe: `tools/probe_cyber_elements.py`
- Scenario: `test_cyber_reinsurance_inspection_discovery`

**Confirmed Behavior**
- Reinsurance list has one Add button. Add creates a `New Reinsurance` tree node; selecting it reveals Gross Premium (Risk), Gross Limit, and required Type.
- Reinsurance Type options are `Facultative` and `Treaty`.
- Inspection list has two distinct initial Add buttons plus `order inspection`.
- The first Inspection Add opens the request form: Inspection Type, Request Date, Inspection Company, Inspection Date, Inspector, Inspection Completed, Request Details, and Inspector Comments.
- The second Inspection Add opens an assignment row: Inspection Company, Inspector, and Inspection Comments.
- Inspection Type options are `Comprehensive`, `Liability`, and `Property`; Inspection Completed options are `Yes` and `No`.
- No save, order inspection, rating, request issue, or bind action was executed.

**Stable Selectors / Methods**
- Reinsurance and Inspection tree nodes use exact link names.
- Reinsurance detail fields have confirmed `osviewid` fallbacks ending `14148146`, `14084946`, and `8548805`.
- Inspection request fields have confirmed fallbacks ending `11648776`, `11649276`, `11648476`, `11664376`, `11648576`, `11649376`, `11648976`, and `11648676`.
- Inspection assignment fields have confirmed fallbacks ending `11522746`, `11522946`, and `11521346`.
- The two initial Inspection Add buttons have no distinct accessible names before rows exist. `CyberInspectionPage` verifies there are exactly two and maps index 0 to request, index 1 to assignment.

**Required Waits**
- Wait for OneShield GatewayServlet responses and application masks after tree navigation and Add actions.

**Known Failed Approaches**
- Attempt: Find the Add buttons using lowercase exact accessible name `add`.
- Symptom: The visible controls were captured, but Playwright returned zero exact matches.
- Replacement: Use exact rendered name `Add`.
- Attempt: Expect Reinsurance fields immediately after Add.
- Symptom: Add only created a `New Reinsurance` tree child.
- Replacement: Open the new child node before locating detail fields.

**Open Questions**
- Inspector option values depend on selecting an Inspection Company and were not expanded because the discovery did not save or order an inspection.

### 2026-06-07 - Cyber Policy Information Element Discovery

**Context**
- LOB: Cyber
- Probe: `tools/probe_cyber_elements.py`
- Test data: `testdata/static/cyber/CyberData.json`, `TC_ID_0001`

**Confirmed Behavior**
- Two fresh live quotes confirmed previously unmapped optional text inputs: `Business Interruption` and `Cyber Extortion`.
- The controls are always visible in the Optional Coverages section on the default Policy Information screen.
- One-field changes across all Common Eligibility options did not reveal additional conditional controls before save or rating.
- The probe did not rate, request issue, or bind; zero policies were bound.
- Exact dropdown options are recorded in `reports/lob-discovery/cyber/latest.json`.

**Stable Selectors / Methods**
- Use `get_by_role("textbox", name="Business Interruption")` with `osviewid` ending `17480548` as fallback.
- Use `get_by_role("textbox", name="Cyber Extortion")` with `osviewid` ending `17480648` as fallback.
- Treat both fields as optional and fill only when the corresponding JSON value is non-empty.

**Required Waits**
- Wait for the application masks after eligibility dropdown changes that emit `FieldProcessorServlet`.

**Known Failed Approaches**
- Attempt: Always click `#employeePortal` after navigating to the direct OneShield URL.
- Symptom: Timeout because the direct URL can already display the login form.
- Replacement: Click the splash control only when visible.
- Attempt: Collect options from all visible `.x-boundlist-item` nodes.
- Symptom: Aggregate Limit initially returned stale Billing Method options.
- Replacement: Scope option collection to the last visible `.x-boundlist` and confirm in a second quote.
- Attempt: Use only the accessible combobox name for `Expiration Date*`.
- Symptom: The control was visible in the DOM inventory but the pytest browser did not expose that role/name consistently.
- Replacement: Add the confirmed `osviewid` fallback ending `17477248`; use the same pattern for Effective Date.

**Open Questions**
- Save/rating-dependent UW behavior for adverse eligibility choices was intentionally not explored in this non-binding inventory.

### 2026-06-07 - Cyber Workflow Migration For TC_ID_0001

**Context**
- LOB: Cyber
- Scenario: `ui/tests/test_cyber.py::test_cyber_workflow[TC_ID_0001]`
- Legacy sources: `CyberPolicyInformation.java` and `Cyber.xlsx`

**Confirmed Behavior**
- Live validation passed end to end for `TC_ID_0001`.
- The flow produced active policy `CY10276980457-00` with total policy premium `$ 2,576.08`.
- Static validation passes: the selected Excel row converts to JSON, Cyber Python modules compile, and pytest-bdd collects exactly one scenario.
- The destination flow uses the shared quote registration, delivery preferences, billing plan, verify billing, and policy summary components.
- ZIP `02766` and address `230 Old Taunton Ave` require `City=Norton` in the current customer-page schema; the legacy workbook has no City column.
- The legacy effective date `01/30/2024` is preserved as `SourceEffectiveDate`; omitting `EffectiveDate` lets the shared quote-registration page use tomorrow's date for a runnable quote.
- The live policy summary reports `Massachusetts`, payment method `Bill Me`, and payment plan `Pay In Full`.

**Selector Status**
- Accessible Cyber field locator names and the legacy field `osviewid` fallbacks completed the live flow.
- Use the accessible role buttons for `>>> rate quote` and `>>> request issue`.
- Do not combine those role buttons with the legacy action `osviewid` using `Locator.or_`; the `osviewid` is on a child span, so the combined locator resolves both the button and its child.

**Known Failed Approaches**
- Attempt: Run the traced Cyber scenario against `https://inforcedev.oneshield.com/oneshield/`, both in the default sandbox and with approved external execution.
- Symptom: Navigation failed before login with `net::ERR_NAME_NOT_RESOLVED`.
- Replacement: Connect through the AWS/VPN environment, then rerun the targeted traced scenario.
- Attempt: Combine the Rate Quote accessible button and its child-span `osviewid` with `Locator.or_`.
- Symptom: Playwright strict-mode violation because the locator resolved two nodes.
- Replacement: Use `get_by_role("button", name=">>> rate quote")` directly; the same rule applies to Request Issue.

### 2026-05-26 - Auto Policy Journey Stops At UW Referral

**Context**
- LOB: Personal Auto
- Scenario: Dashboard Run Policy Journey with generated/pasted auto persona that triggers UW before request issue.

**Confirmed Behavior**
- Run Policy Journey should treat a visible UW referral page as a terminal `uw_referral` outcome, not automatically override conditions and continue to bind.
- UW conditions can be a valid passed test outcome when the profile is intentionally risky.
- The auto policy-flow runner now captures UW grid cells and returns `uw_referral` before request issue, during request issue, after request issue, after rating, or during normal-flow exceptions.

**Known Failed Approaches**
- Attempt: Automatically call `_try_uw_override()` when the current user can edit UW rows.
- Symptom: The flow continued from the UW referral page to policy summary/bind, hiding the expected referral outcome.
- Replacement: Stop at UW, capture triggered rules, and report `UW Referral` as the result.

### 2026-05-05 - Live Homeowner Policy Flow

**Context**
- LOB: Homeowner
- Scenario: `ui/tests/test_homeowner.py::test_homeowner_workflow[TC_ID_0001]`
- Test data: `testdata/static/HomeData.json`, `TC_ID_0001`

**Confirmed Behavior**
- The flow completed end to end after the wait fixes; final validation produced active policy `HO10045437257-00`.
- Quote registration, homeowner quote summary, location coverage, rating, request issue, delivery preferences, billing, bind, and policy summary were reached in the live DEV app.
- The homeowner flow uses both `#ajax-sub-pre-loading` and `.x-mask` as loader/mask indicators.

**Stable Selectors / Methods**
- Use `BasePage.wait_for_app_ready()` after OneShield navigation, saves, rating, and ExtJS selections.
- Use visible `.x-boundlist-item` filtering for Quote Registration program/producer and homeowner comboboxes.
- Homeowner tree navigation links are still role links by visible city/program text, followed by app-loader waits.

**Required Waits**
- Wait after producer and program selections in Quote Registration.
- Wait after homeowner Program Type and Billing Method selections.
- Wait after homeowner quote-summary saves and tree-link navigation.
- Wait after coverage Residence Type selection, saves, Bind Information navigation, and Rate Quote.
- Wait through both OneShield loaders after policy creation navigation and bind actions.

**Known Failed Approaches**
- Attempt: ARIA role option click for `Homeowner` in Quote Registration.
- Symptom: 30-second timeout waiting for option.
- Replacement: visible ExtJS bound-list filtering plus JS click.

**Open Questions**
- `CreatePolicyPage` is still named under `ui/pages/auto/` but is reused by homeowner; consider moving it to common in a separate cleanup if desired.
- Policy summary extraction still includes auto-specific fields as `None` for homeowner reports.

### 2026-05-05 - Live Homeowner Additional Elements Probe

**Context**
- LOB: Homeowner
- Scenario: `ui/tests/test_homeowner_additional_elements.py::test_homeowner_additional_elements[TC_ID_0001]`
- Test data: `testdata/static/HomeData.json`, `TC_ID_0001`

**Confirmed Behavior**
- The additional-elements flow completed end to end and produced active policy `HO10045659057-00`.
- Quote Summary exposes identity and named-insured controls that the base flow does not change: Quote Name, Term, Effective Date, Expiration Date, Add/Delete, Prefix, First Name, Middle Name, Last Name, Suffix, and DOB.
- City Information is a read-only/display page in this path with Address Line 1, City, State, ZIP, and Country visible; save and return to the homeowners location coverage node after review.
- Location Coverage has visible limit fields and optional property controls outside the base flow: Replacement cost contents, Contents, Loss of Use, Other Structures, Protection Class, BCEG, roof mitigation dropdowns, distance to shore, security/protection checkboxes, and Perimeter Security Protection.
- Premium Summary exposes review/actions outside the base bind path: RATING DETAIL, Premium Package Selected, Re-Rate, and Print Quote Letter.
- Delivery Preferences exposes preference controls: Add A New Preference, Add, Remove, Primary Email, and Validate Email.
- Billing Plan exposes Default Name, Options radio buttons, Edit Profile Details, Payer Currency, and Payment Plan.
- Verify Billing exposes both `>>> Bind` and `>>> Bind With Payment`; the stable bind path still uses exact `>>> Bind`.

**Stable Selectors / Methods**
- Add discovered homeowner quote summary and city elements to `HomeOwnerQuoteSummaryPage`.
- Add discovered coverage limit, mitigation, and security elements to `HomeownerCoveragePage`.
- Add post-rating delivery/billing/verify review elements to `CreatePolicyPage` until that shared page is moved out of `ui/pages/auto/`.
- For additional coverage limit fields, `Contents` and `Loss of Use` accept `smart_fill` with `FieldProcessorServlet` response waits.

**Required Waits**
- Wait for app readiness before reviewing discovered page elements.
- Continue waiting after request issue, delivery next, billing next, and bind.

**Known Failed Approaches**
- None in the validated additional-elements scenario.

**Open Questions**
- Optional mitigation/security controls were verified as visible but not selected because no stable data values were defined for them.

### 2026-05-05 - Live Homeowner Additional Elements Test Cases

**Context**
- LOB: Homeowner
- Scenario: `ui/tests/test_homeowner_additional_elements.py`
- Test data: `testdata/static/HomeData.json`, `TC_ID_0001`, `TC_ID_0011`, `TC_ID_0012`

**Confirmed Behavior**
- The additional-elements scenario outline completed live for three package variants: Gold, Silver, and Bronze.
- `TC_ID_0001` produced active policy `HO10045819557-00` with premium `$ 4,339.58`.
- `TC_ID_0011` produced active policy `HO10045967557-00` with premium `$ 3,032.80`.
- `TC_ID_0012` produced active policy `HO10046115557-00` with premium `$ 1,763.93`.
- New rows `TC_ID_0011` and `TC_ID_0012` need the canonical homeowner keys used by the page objects, such as `DayCare`, `UndergroundOil`, `ResidenceRented`, `ResidenceVacant`, `ResidenceType`, deductible fields, liability fields, and bind-info question fields.
- Older `TC_ID_0002` through `TC_ID_0010` still use partial/legacy key names like `Day Care` and are not valid for the additional-elements aggregate step without normalization.

**Stable Selectors / Methods**
- The same additional-elements page object methods handled Gold, Silver, and Bronze package data without selector changes.
- Keep exercising `Contents` and `Loss of Use` through `HomeownerCoveragePage.set_additional_limit_fields`.

**Required Waits**
- Existing `wait_for_app_ready()` calls remained sufficient for all three live cases.

**Known Failed Approaches**
- None in the three-case validation run.

**Open Questions**
- The partial legacy rows in `HomeData.json` can be normalized later if they should become runnable homeowner test cases.

### 2026-05-05 - Homeowner Page Object Split

**Context**
- LOB: Homeowner
- Scenario: `ui/tests/test_homeowner_additional_elements.py` and `ui/tests/test_homeowner.py`
- Test data: `testdata/static/HomeData.json`, `TC_ID_0001`, `TC_ID_0011`, `TC_ID_0012`

**Confirmed Behavior**
- The homeowner additional-elements feature now maps to the live screens page by page instead of routing post-rating controls through `ui/pages/auto/create_policy_page.py`.
- Live validation passed for the additional-elements scenario outline: `3 passed in 239.80s`.
- Live validation passed for the base homeowner policy flow: `1 passed in 65.97s`, producing active policy `HO10046729957-00`.

**Stable Selectors / Methods**
- Quote Summary locators belong in `HomeOwnerQuoteSummaryPage`.
- City Information locators belong in `HomeownerCityInformationPage`.
- Location Coverage locators belong in `HomeownerCoveragePage`.
- Bind Information radio questions and Rate Quote belong in `HomeownerBindInformationPage`.
- Premium Summary actions belong in `HomeownerPremiumSummaryPage`.
- Delivery Preferences controls belong in `HomeownerDeliveryPreferencesPage`.
- Billing Plan controls belong in `HomeownerBillingPlanPage`.
- Verify Billing controls and bind actions belong in `HomeownerVerifyBillingPage`.
- `CreatePolicyPage` should stay focused on generic auto/shared issue-next-bind behavior unless a future refactor moves that shared flow into `ui/pages/common/`.

**Required Waits**
- The same `wait_for_app_ready()` waits remained sufficient after splitting page ownership.

**Known Failed Approaches**
- Do not add homeowner-specific premium, delivery, billing, or verify-billing review locators back into `CreatePolicyPage`.

**Open Questions**
- The base homeowner feature still keeps high-level aggregate steps for quote summary and location coverage; split it further only if the test language needs to mirror every screen as explicitly as the additional-elements feature.

### 2026-05-05 - Policy Summary LOB Reports

**Context**
- Page: `ui/pages/common/policy_summary_page.py`
- Shared step: `Then I read and extract policy summary page details`
- Validation scenario: `ui/tests/test_homeowner.py::test_homeowner_workflow[TC_ID_0001]`

**Confirmed Behavior**
- Policy summary reports are now saved by Program/LOB instead of appending every LOB to `policy_summary/policy_reports.csv`.
- Live homeowner validation produced active policy `HO10046888857-00`.
- The homeowner report was written to `policy_summary/policy_reports_homeowner.csv`.

**Stable Selectors / Methods**
- `PolicySummary.extract_details(test_data)` owns summary extraction and test-data enrichment.
- `PolicySummary.save_lob_report(details)` owns the report destination decision.
- `PolicySummary.report_file_name(program)` normalizes Program values, for example `Homeowner` to `policy_reports_homeowner.csv` and `Personal Auto` to `policy_reports_personal_auto.csv`.

**Required Waits**
- No new UI waits were needed; this is post-summary file output.

**Known Failed Approaches**
- Do not hard-code a shared `policy_reports.csv` path in step definitions for new LOB report writes.

**Open Questions**
- Existing historical rows remain in `policy_summary/policy_reports.csv`; split or migrate them only if historical reports need cleanup.

### 2026-05-05 - LOB-Specific Policy Summary Schemas

**Context**
- Page router: `ui/pages/common/policy_summary_page.py`
- LOB pages:
  - `ui/pages/auto/auto_policy_summary_page.py`
  - `ui/pages/homeowner/homeowner_policy_summary_page.py`
  - `ui/pages/cyber/cyber_policy_summary_page.py`
  - `ui/pages/wc/wc_policy_summary_page.py`
- Validation scenario: `ui/tests/test_homeowner.py::test_homeowner_workflow[TC_ID_0001]`

**Confirmed Behavior**
- Policy summary extraction now routes by live `Program` value to a LOB-specific page object.
- Homeowner reports no longer use auto-only columns such as Employment Category, Vehicle Use, and Ownership.
- Live homeowner validation produced active policy `HO10047045057-00`.
- `policy_summary/policy_reports_homeowner.csv` was recreated with homeowner fields including Program Type, Billing Method, Policy Coverage Option, Residence Type, Replacement Cost, Contents, Loss Of Use, deductibles, Liability, Medical Payments, Year Built, Roof Type, and Construction Type.
- The previous homeowner CSV with the wrong schema was preserved as `policy_reports_homeowner_schema_mismatch_20260505_115710.csv`.

**Stable Selectors / Methods**
- `PolicySummary` should remain a router for the shared BDD step.
- LOB-specific report columns belong in each LOB `*_policy_summary_page.py` file.
- `utils.file_writer.save_summary_to_csv` archives an existing CSV when its header does not match the current LOB schema, then writes a new header.

**Required Waits**
- No new UI waits were needed; this is post-summary extraction and reporting behavior.

**Known Failed Approaches**
- A single common policy summary extractor with auto-oriented test-data columns causes wrong schemas for Homeowner, Cyber, and WC reports.

**Open Questions**
- Add richer WC report fields once the WC flow captures more LOB-specific test data.

### 2026-05-05 - Dashboard Explorer Prompt Helper

**Context**
- Area: Dashboard
- Screen: Explorer
- Purpose: Create Codex prompts that automatically invoke the local OneShield Explorer skill.

**Confirmed Behavior**
- The dashboard Explorer panel prefixes user-entered text with `use Oneshield explorer skill`.
- If the user already includes that prefix at the start of the prompt, the dashboard does not duplicate it.
- Explorer prompts are saved as normal dashboard jobs so they appear in local job history and can be copied from the report modal.

**Stable Selectors / Methods**
- Backend endpoint: `POST /api/explorer/prompt`.
- Frontend API helper: `api.explorerPrompt(prompt)`.
- Frontend panel: `dashboard/frontend/src/components/ExplorerPanel.jsx`.

**Required Waits**
- None. This is a dashboard prompt-composition helper and does not run a OneShield browser flow.

**Known Failed Approaches**
- None.

**Open Questions**
- The dashboard currently prepares the Codex prompt; it does not execute Codex directly from the browser.

### 2026-05-05 - Dashboard Explorer Codex Run

**Context**
- Area: Dashboard
- Screen: Explorer
- Purpose: Run Explorer prompts through the local Codex CLI with the OneShield Explorer skill trigger.

**Confirmed Behavior**
- `POST /api/explorer/run` now builds the same `use Oneshield explorer skill` prompt used by the prompt helper.
- The backend invokes `codex exec` from the repository root with `--sandbox workspace-write`.
- Temporary Codex output files are written under `reports/codex-explorer/` instead of the default Windows temp directory.
- The Explorer UI did not need changes because it already calls `/api/explorer/run` and polls the existing job store.
- Codex CLI can be overridden with `CODEX_BIN`; timeout can be overridden with `CODEX_EXPLORER_TIMEOUT_SECONDS`.

**Stable Selectors / Methods**
- Backend helpers: `_find_codex_cli`, `_run_codex_explorer`, `_format_codex_explorer_report`.
- Endpoint: `POST /api/explorer/run`.

**Required Waits**
- None. This is a dashboard backend job, not a OneShield browser interaction.

**Known Failed Approaches**
- Attempt: Explorer Run used dashboard-local AI intent routing and direct policy/UW tool execution.
- Symptom: The run path bypassed the Codex skill even though the prompt helper produced skill-prefixed prompts.
- Replacement: Invoke `codex exec` with the skill-prefixed prompt from the backend run endpoint.
- Attempt: Passing `--ask-for-approval never` to `codex exec`.
- Symptom: Local Codex CLI returned `unexpected argument '--ask-for-approval'`.
- Replacement: Omit approval-policy flags for `codex exec`; this subcommand in the local install only accepts the supported exec options.

**Open Questions**
- Streaming Codex output into job logs is still coarse; current behavior captures the final command output when `codex exec` completes.

### 2026-05-05 - Homeowner Pool And Prior Claims Case

**Context**
- LOB: Homeowner
- Scenario: `ui/tests/test_homeowner.py::test_homeowner_workflow[TC_ID_0013]`
- Test data: `testdata/static/HomeData.json`, `TC_ID_0013`

**Confirmed Behavior**
- BDD collection finds the new pool/prior-claims scenario.
- Live browser execution reached Homeowner Location Coverage for `TC_ID_0013`.
- Prior claims/losses are supported by the current flow: `Loses=Yes` drives the existing `Any losses in the last three years?` question.
- Pool is not confirmed as supported in the current Homeowner Location Coverage UI. The current probe searched accessible radio groups named like `swimming pool` or `pool` and did not find a visible control.
- The targeted run failed at the explicit capability check with `AssertionError: Pool question was not found on Homeowner Location Coverage.`

**Stable Selectors / Methods**
- `HomeownerCoveragePage.set_pool(data)` answers an optional pool radio question only when `Pool` is present in test data.
- The pool radio group is searched by accessible radiogroup name containing `swimming pool` or `pool`, then answers the exact `Pool` value.
- Prior claims reuse the existing `HomeownerCoveragePage.set_loses(data)` method with `Loses=Yes`.

**Required Waits**
- Existing app-ready waits were sufficient to reach Location Coverage.

**Known Failed Approaches**
- Attempt: Inline Playwright probe and targeted pytest run from the sandbox.
- Symptom: Playwright driver startup failed before browser launch with Windows named-pipe `PermissionError: [WinError 5] Access is denied`.
- Replacement: Run the targeted pytest command in a normal local shell/session where Playwright subprocess creation is allowed.
- Attempt: Treat `Pool=Yes` as a runnable Homeowner input using accessible radio groups named `swimming pool` or `pool`.
- Symptom: Live run failed on Homeowner Location Coverage with `Pool question was not found on Homeowner Location Coverage.`
- Replacement: Do not treat pool as confirmed/supported until a live UI probe identifies the actual screen, label, option text, and stable selector.

**Open Questions**
- Whether a pool question exists under a different label, hidden section, endorsement, or downstream screen still needs confirmation.

### 2026-05-05 - Homeowner Dropdown Option Matrix

**Context**
- LOB: Homeowner
- Probe: `tools/probe_homeowner_dropdown_options.py`
- Generated data: `testdata/static/HomeownerDropdownOptionsData.json`
- Validation: `tools/run_homeowner_dropdown_case.py TC_HO_DD_0001`

**Confirmed Behavior**
- Live probe collected Homeowner-specific dropdown options from Quote Summary and Location Coverage.
- The generated dropdown matrix contains 141 test cases, one for each non-placeholder dropdown option discovered by the live probe.
- Every generated row has `Description`, `DropdownScreen`, `DropdownField`, `DropdownDataKey`, and `DropdownOption` so the customer/test intent is visible from JSON.
- Data validation passed with `1 passed`: `ui/tests/test_homeowner_dropdown_options_data.py`.
- Representative live validation passed for `TC_HO_DD_0001` and produced active policy `HO10048888557-00`.

**Stable Selectors / Methods**
- `HomeOwnerQuoteSummaryPage.set_optional_identity_dropdowns(data)` selects optional quote-summary dropdowns when `Term`, `Prefix`, or `Suffix` are present.
- `HomeownerCoveragePage.set_optional_dropdowns(data)` selects optional Location Coverage dropdowns when keys such as `ProtectionClass`, `BCEG`, `RoofShape`, `OpeningProtection`, `DistanceToShore`, or `PerimeterSecurityProtection` are present.
- `reports/homeowner_dropdown_options.json` is the live option artifact used by the generator and data-validation test.

**Required Waits**
- Continue using `wait_for_app_ready()` after ExtJS dropdown selections.
- `RoofType` options may require preceding Location Coverage fields to be populated before the list opens reliably.

**Known Failed Approaches**
- Attempt: Collect `RoofType` options before filling required Location Coverage fields.
- Symptom: The ExtJS bound list did not open within the probe timeout.
- Replacement: Fill required coverage fields first, then collect `RoofType`.

**Open Questions**
- Full live execution of all 141 dropdown cases is intentionally not run by default because it would create many policies and take substantial time.

### 2026-05-05 - Homeowner Roof Type UW Probe Script

**Context**
- LOB: Homeowner
- Probe: `tools/probe_homeowner_roof_uw.py`
- Output: `reports/homeowner_roof_uw_results.json`

**Confirmed Behavior**
- The current live-discovered Roof Type dropdown artifact contains 29 selectable options.
- Existing BDD UW documentation confirms `RoofType=Flat` triggers a `Hard-Stop` condition containing `Roof type is flat, tin or rolled paper`.
- The probe script creates a clean homeowner quote per roof type, stops after Rate Quote, and records whether the app lands on UW Referral or Premium Summary without binding policies.
- Local data validation still passes for the stored homeowner dropdown matrix: `pytest ui\tests\test_homeowner_dropdown_options_data.py -v` produced `1 passed`.

**Stable Selectors / Methods**
- Reuse `HomeownerCoveragePage.coverage_steps(data)` and `HomeownerBindInformationPage` rating methods for roof-type UW probing.
- Detect UW by visible `underwriting referral` or `Underwriting Issues`.
- Detect clean rating by visible `premium | summary`.

**Required Waits**
- Continue filling required Location Coverage fields before selecting `RoofType`.
- Keep `wait_for_app_ready()` after ExtJS selections, Save, Bind Information navigation, and Rate Quote.

**Known Failed Approaches**
- Attempt: Run `python tools\probe_homeowner_roof_uw.py --headless --roof-type "Flat" --roof-type "Tin" --roof-type "Rolled Paper" --roof-type "Roll Roofing" --roof-type "Asbestos Shakes"` from the Codex sandbox.
- Symptom: Playwright failed before browser launch with Windows subprocess pipe `PermissionError: [WinError 5] Access is denied`.
- Replacement: Run the same probe command in a normal local shell/session where Playwright subprocess creation is allowed.

**Open Questions**
- Full live roof matrix results are not confirmed in this sandbox session because browser launch was blocked.
- `Tin`, `Rolled Paper`, `Roll Roofing`, and `Asbestos Shakes` still need live execution to confirm whether they trigger the same or separate UW condition.

### 2026-05-06 - General Liability Dropdown Matrix

**Context**
- LOB: General Liability
- Scenario: `ui/tests/test_general_liability_dropdown_options.py`
- Test data: `testdata/static/general_liability/GeneralLiabilityDropdownOptionsData.json`
- Live inventory: `reports/general_liability_dropdown_inventory.json`

**Confirmed Behavior**
- The GL dropdown matrix now contains 653 generated cases and mirrors the live inventory for the confirmed dropdown controls.
- The matrix keeps the dependent GL flow intact by carrying forward the base case and only changing one dropdown value per case.
- `CoverageType` and `GLClassCode` were not captured by the generic live collector, so the generator backfills the confirmed values from `GeneralLiabilityData.json`.
- `LossHistory` and `ForeignSales` are radios, not dropdowns, and are intentionally excluded from the dropdown matrix.

**Stable Selectors / Methods**
- The matrix reuses the existing GL page objects and flow steps.
- The generated feature uses the same end-to-end flow as the base GL scenario.

**Required Waits**
- Keep the existing loader and FieldProcessor waits after dropdown changes, saves, rating, and bind-navigation actions.

**Known Failed Approaches**
- Attempt: Treat the live inventory file as a flat list of dropdown items.
- Symptom: The source JSON is sectioned by `basic_policy_information`, `coverage_and_limits`, `rating_basis_and_classification`, and `billing_plan`, so the first generator pass failed on JSON shape mismatch.
- Replacement: Iterate the nested section objects and generate the matrix from their key/value pairs.
- Attempt: Include radio controls in the dropdown matrix.
- Symptom: Validation failed because `LossHistory` and `ForeignSales` are radios, not dropdowns.
- Replacement: Keep the matrix dropdown-only and document the radios separately.

**Open Questions**
- The matrix is large enough that a full live execution run should be scheduled deliberately rather than on every normal validation pass.

### 2026-05-06 - General Liability Network Waits

**Context**
- LOB: General Liability
- Scenario: `ui/tests/test_general_liability.py::test_general_liability_creation[TC_ID_0001]`
- Test data: `testdata/static/general_liability/GeneralLiabilityData.json`, `TC_ID_0001`

**Confirmed Behavior**
- Live GL creation passed end to end after adding a reusable optional OneShield response wrapper.
- The final validation produced active policy `GL10055117457-00` with premium `$ 805.92`.
- Server-backed GL actions commonly return `GatewayServlet` or `FieldProcessorServlet` responses.
- Basic/coverage dropdown selections usually rely on ExtJS visible-list selection plus loader waits; adding a response wait to every dropdown caused unnecessary 10-second timeout delays.

**Stable Selectors / Methods**
- `BasePage.with_optional_oneshield_response(...)` wraps actions that may emit OneShield backend responses without hiding real action failures.
- `BasePage.select_extjs_option(...)` retries visible `.x-boundlist-item` matching up to three times to reduce stale bound-list failures.
- Use response waits for GL save buttons, liability-location save, rating tree/class actions, exposure, rate quote, request issue, and billing save/next.
- Do not use response waits for every GL coverage dropdown by default; spinner waits were sufficient and much faster in the live flow.

**Required Waits**
- Keep `wait_for_app_ready()` after GL dropdown selections, tree navigation, saves, rating, request issue, billing, and bind transitions.
- Wrap server-backed GL actions with `with_optional_oneshield_response(...)` before waiting for masks.

**Known Failed Approaches**
- Attempt: Wrap every GL dropdown selection in a network-response wait.
- Symptom: Live flow still passed, but each dropdown without a backend response paid the full timeout and the run slowed to about 4.5 minutes.
- Replacement: Apply response waits selectively to actions observed to produce `GatewayServlet` or `FieldProcessorServlet`; keep plain ExtJS selection plus mask waits for passive dropdowns.

**Open Questions**
- Bind currently relies on existing verify-billing behavior and mask waits; add a bind-specific response wrapper only if future traces show post-bind race conditions.

### 2026-05-06 - Personal Auto Sanity Runner From Dashboard Sandbox

**Context**
- LOB: Personal Auto
- Scenario: Quick sanity check using the dashboard policy-flow runner path
- Test data: In-memory generated clean-standard auto persona for the current run only

**Confirmed Behavior**
- The existing BDD auto wrapper still collects `TC_ID_0001` and `TC_ID_0011` from `ui/features/auto/personal_auto.feature`.
- The generated clean-standard auto persona contained all required fields used by the current auto page-object path.
- Live execution could not start from the Codex sandbox because Playwright failed before browser launch with Windows `PermissionError: [WinError 5] Access is denied`.
- The Playwright MCP browser could open the OneShield splash page, but it was not authenticated and the run did not proceed because credentials from `.env` must not be exposed or copied.

**Stable Selectors / Methods**
- Reuse `mcp_tools.policy_flow_generator.flow_runner.run_flow("auto", persona)` for one-off in-memory auto sanity personas when Playwright subprocess creation is available.
- The auto BDD path remains `ui/tests/test_auto_workflow.py` -> `ui/features/auto/personal_auto.feature` -> `ui/steps/auto/auto_workflow_steps.py` -> auto/common page objects.

**Required Waits**
- No new waits confirmed in this sandbox session because the browser could not launch.

**Known Failed Approaches**
- Attempt: Run the in-memory generated auto persona through `run_flow("auto", persona)` from the Codex sandbox.
- Symptom: Playwright failed during `sync_playwright()` startup with Windows named-pipe `PermissionError: [WinError 5] Access is denied`.
- Replacement: Run the same auto sanity command in a normal local shell/session where Playwright subprocess creation is allowed, or start from an already authenticated browser session without exposing `.env` credentials.

**Open Questions**
- Live auto bind status for the generated clean-standard persona still needs execution outside the restricted sandbox.

### 2026-05-08 - Personal Auto Page-To-API Flow Capture

**Context**
- LOB: Personal Auto
- Scenario: `ui/tests/test_auto_workflow.py::test_personal_auto_workflow[TC_ID_0001]`
- Test data: `testdata/static/auto/AutoData.json`, `TC_ID_0001`

**Confirmed Behavior**
- Live Auto execution passed end to end with API capture enabled and produced active policy `PA10068256657-00`.
- The opt-in pytest flag `--api-flow-map reports\auto_api_flow_TC_ID_0001.json` writes a structured page-to-network artifact without changing normal test runs.
- The capture groups business calls by page labels: login, new quote, customer, quote registration, quote summary, driver, vehicle, coverages/rating, premium summary, delivery preferences, billing plan, verify billing, and policy summary.
- The `TC_ID_0001` capture recorded 47 non-static document/XHR/fetch calls in total.
- The most common OneShield endpoints in the flow were `GatewayServlet` and `FieldProcessorServlet`; login also used `SessionExtendServlet` and initial document/config requests.

**Stable Selectors / Methods**
- Use the `api_flow_recorder` fixture to mark logical page names in step definitions.
- Use `ApiFlowRecorder` in `utils/api_flow_recorder.py` for response-based capture, redacted sensitive headers, parsed JSON/text bodies, and grouped page output.
- Keep API capture opt-in with `--api-flow-map`; use `--api-flow-include-static` only when static resource diagnostics are needed.

**Required Waits**
- Existing Auto page waits remained sufficient; the recorder listens to Playwright network events and does not add UI waits.
- For the issue/bind aggregate, page markers should be placed before the action that triggers the next server-backed transition.

**Known Failed Approaches**
- None in the validated capture run.

**Open Questions**
- The JSON artifact now identifies required candidate calls per page, but the replay MCP server still needs endpoint payload normalization, token/session handling, and ordering rules before it can drive the policy fully through API calls.

### 2026-05-08 - Business-Facing Policy MCP Tools

**Context**
- Area: MCP policy-flow-generator
- Tools: `compare_scenarios`, `summarize_policy`

**Confirmed Behavior**
- The policy-flow MCP server now exposes a BA/customer-facing `compare_scenarios` tool that accepts plain-English scenario descriptions, generates personas, live-runs each scenario, and returns a compact comparison table.
- The server also exposes `summarize_policy`, which reads local `policy_summary/policy_reports*.csv` files and summarizes a saved bound policy by policy number, LOB, customer name, or plain query.
- Local validation confirmed `summarize_policy(policy_number="PA10068256657-00")` returns the saved Personal Auto policy summary from the 2026-05-08 live run.

**Stable Selectors / Methods**
- Business report formatting lives in `mcp_tools/policy_flow_generator/business_reports.py`.
- `flow_runner.run_flow` now carries optional `policy_summary` details returned by LOB runners.
- Auto, Cyber, and Homeowner runners attempt to extract and save `PolicySummary` details after a successful bind.

**Required Waits**
- No new UI waits were added. Summary extraction occurs after existing bind workflows complete.

**Known Failed Approaches**
- None in local import/summary validation.

**Open Questions**
- Full live validation of `compare_scenarios` should be run deliberately because each scenario creates a live quote/policy or UW outcome.

### 2026-05-12 - Policy Journey UW Terminal Detection

**Context**
- Area: Dashboard / MCP policy-flow-generator
- Scenario: Run Policy Journey with pasted customer JSON that triggers UW during the normal issue/billing/bind path.
- Test data: In-memory persona JSON from the dashboard or MCP tool.

**Confirmed Behavior**
- The runner should treat `underwriting referral` or `Underwriting Issues` as a terminal `uw_referral` result anywhere after rating, including during request issue, delivery preferences, billing plan, or bind.
- Waiting only for policy bind buttons can misclassify a valid UW referral as a timeout/error when risky customer data leaves the normal bind path.
- Cyber policy flow is now registered in the policy-flow runner and dashboard policy LOB whitelist so existing cyber runner logic is reachable from Run Policy Journey.

**Stable Selectors / Methods**
- Use `UWReferralPage.is_visible()` for short terminal checks.
- Use `UWReferralPage.capture_conditions()` to collect visible UW grid cells for reports.
- Policy-flow runners check for UW before and after normal issue/billing/bind actions and after exceptions from those actions.

**Required Waits**
- Use short visible checks around expected normal-flow buttons, then a longer visible check after an action exception before classifying the run as an error.

**Known Failed Approaches**
- Attempt: Check for UW only immediately after rating, then always proceed through request issue, next, next, and bind.
- Symptom: Valid risky customers could land on UW referral while the runner kept waiting for policy-bound controls and eventually timed out.
- Replacement: Classify visible UW pages as terminal `uw_referral` throughout the post-rating path.

**Open Questions**
- Full live validation was not run in the Codex sandbox because browser execution can be restricted by local Playwright subprocess permissions.

### 2026-05-11 - Personal Auto Early UW Referral In Dashboard Runner

**Context**
- LOB: Personal Auto
- Scenario: Dashboard Run Policy Journey with pasted JSON `AI_482736`
- Test data: In-memory persona with under-25 driver, `SR22=Yes`, and `LicenseStatus=Revoked`

**Confirmed Behavior**
- OneShield correctly routes this profile to `QUOTE | UNDERWRITING REFERRAL | UNDERWRITER`.
- The visible UW grid shows three conditions: all drivers under 25, SR-22 / Certificate of Insurance, and revoked/suspended license status.
- This is a valid `uw_referral` outcome, not malformed JSON and not a failed policy bind attempt.

**Stable Selectors / Methods**
- Detect UW referral by visible text `underwriting referral`.
- Capture visible UW issue grid values from `page.get_by_role("gridcell")`.
- The dashboard auto runner now checks for UW before coverage/rating, during a coverage/rating exception, and after rating before attempting policy creation.

**Required Waits**
- Use short visible checks for the UW breadcrumb around coverage/rating so a referral screen is classified before the runner searches for normal rating or bind controls.

**Known Failed Approaches**
- Attempt: Always call `PolicyTermPage.policy_term_steps()` and classify UW only afterward.
- Symptom: Risky inputs that reach UW before normal rating were reported as flow errors and could be shown in the dashboard as completed/bound.
- Replacement: Treat early visible UW referral as a terminal `uw_referral` result and skip policy creation.

**Open Questions**
- Additional auto UW screens may need richer grid parsing if the column count changes from the current Asset / Condition / Type / Comments / Overridden layout.

### 2026-05-06 - General Liability UW Trigger Exploration With One Quote

**Context**
- LOB: General Liability
- Scenario: Manual MCP Playwright exploration on one live quote: `GLMCP UW1778082264366`
- Goal: Mutate one quote back and forth instead of creating many sandbox policies while looking for UW referral triggers.

**Confirmed Behavior**
- Baseline GL quote rated clean and landed on `premium | summary` with `>>> request issue` visible.
- `Have there been any losses in the last three years? = Yes` rated clean on the same quote; no `underwriting referral` or `Underwriting Issues` screen appeared.
- Previously probed high-risk GL class descriptions, including explosives, sandblasting, wrecking, foreign sales, fireworks, chemical distributors, anhydrous ammonia, oil refineries, airports, and refuse collection, rated clean when used as the single changed rating basis value.
- `Policy Type = Excess Only Policy` is not a UW trigger by itself. It opens additional excess-policy fields such as `GL Excess Attachment Point*`, `SIR type`, and `SIR amount`; rating is blocked or incomplete until the required excess fields are completed.
- Selecting `Liquor Liability Coverage` adds a `GL Optional Coverages` tree node and opens required liquor fields: `Liquor Classification*`, `Liquor Occurrence Limit*`, `Liquor Gross Sales*`, `Liquor Liability "A" Rate*`, and `Liquor Aggregate Limit*`.
- `Liquor Liability "A" Rate* = 999` is rejected by validation: max accepted value is `99.999`. Entering `99.999` formats to `$ 100.00`, which still violates the max; use `99.99` or lower.
- `Liquor Aggregate Limit*` cannot be greater than the base `General Aggregate Limit*`. The app displays: `Liquor Aggregate Limit can not be greater than General Aggregate Limit. This MUST be fixed or it will ERROR in rating.`
- Valid liquor liability supporting values rated clean on the same quote: classification `58168-Temporary Licensees`, occurrence `100,000`, aggregate `100,000`, gross sales `999,999,999`, and rate `99.99`.
- These liquor/excess behaviors are validation or required-field routing, not confirmed UW referrals.

**Stable Selectors / Methods**
- Use the left detail tree to reuse one quote: `details` tab, then rows `Policy Information`, `GL Coverage and Limits`, `GL Optional Coverages`, `Massachusetts`, and the data-driven city row such as `Norton`.
- Use the page-object style visible ExtJS option selection for dependent dropdowns; MCP role snapshots are useful for discovering newly opened fields.
- Detect UW by visible `underwriting referral` or `Underwriting Issues`. Clean rating is indicated by `premium | summary` and `>>> request issue`.

**Required Waits**
- After toggling optional coverage checkboxes, wait for the tree to refresh before checking for new child nodes.
- After saving optional/excess screens, inspect the message list before attempting rate; validation messages can leave the quote on the same page without showing `>>> rate quote`.

**Known Failed Approaches**
- Attempt: Find a GL UW trigger by changing only one class description or limit value.
- Symptom: High-risk classes and high/edge limit values rated clean or stayed in normal routing.
- Replacement: Explore dependent screens opened by `Excess Only Policy`, optional coverages, and exclusions because they expose additional required/rating fields.
- Attempt: Use an out-of-range liquor rate to force referral.
- Symptom: The app blocks save with field validation instead of producing UW.
- Replacement: Use max-valid values and then rate; treat validation as separate from UW.

**Open Questions**
- No confirmed General Liability UW referral trigger has been found yet in the live app.
- Next GL UW candidates to test on the same quote are optional coverages and exclusions with valid supporting fields: `General Liability Manual Coverages`, `Employee Benefits Coverage`, `Hired Auto Coverage`, `Non-Owned Auto Coverage`, `Contractual Liability Exclusion`, `Exclude Employees as Additional Insureds`, and `Hazards in Connection with Designated Premises`.
- Excess-only rating needs its required excess/SIR fields inventoried before it can be classified as clean vs UW.

### 2026-05-19 - Personal Auto Browserless API Replay

**Context**
- LOB: Personal Auto
- Scenario: Browserless API replay from `reports/auto_api_flow_TC_ID_0001_20260519.json`
- Test data: `testdata/static/auto/AutoData.json`, mainly `TC_ID_0001`

**Confirmed Behavior**
- Browserless login works through `api_tests/oneshield_api_replay.py` by fetching the live portal page, extracting `pageJSON`, posting credential field processors, and submitting `GatewayServlet` `TX_NAME=Action.3`.
- The replay can create live quote/customer records before reaching the rate action. A run that stops at `rate` is not read-only.
- Correct Auto API chain is:
  - coverage prepare: `auto_coverages_rating`, `TX_NAME=1534748`, response remains on Coverages.
  - rate: `auto_premium_summary`, `TX_NAME=Action.1753948`, response page `premium | summary`.
  - request issue: `auto_premium_summary`, `TX_NAME=Action.305905`, response page `Delivery Preferences`.
  - delivery next: `auto_delivery_preferences`, `TX_NAME=Action.1262048`, response page `billing plan`.
  - billing next: `auto_billing_plan`, `TX_NAME=Action.1504046`, response page `quote | verify billing choices`.
  - bind: `auto_verify_billing`, `TX_NAME=Action.1780148`, response page `Policy | Current Summary`.
- Live API validation for `TC_ID_0011` reached `premium | summary` with premium `$ 2,049.45`, reached `Delivery Preferences`, reached `quote | verify billing choices`, and then bound policy `PA10134896357-00`.
- The API bind summary was written to `policy_summary/policy_reports_api_auto.csv`.

**Stable Selectors / Methods**
- Keep API replay code under `api_tests/`; it uses `requests` and must remain separate from the Playwright BDD UI framework.
- `run-auto` in `oneshield_api_replay.py` is now blocked by default. It requires `--allow-live-create` because it creates live OneShield records.
- Binding is separately blocked by default and requires `--allow-bind`; keep this guard because the flow creates real policies.

**Required Waits**
- Not a UI wait issue. The replay must refresh live `pageJSON` state, hvars, `DRAGON_TRANSACTION_ID`, `OBJECT_TREE`, `WORKFLOW_CONTEXT`, and dynamic `bv_<object>_<attribute>` field names after each response.

**Known Failed Approaches**
- Attempt: Treat `--stop-after rate` as a safe/read-only experiment.
- Symptom: Multiple live James Smith Personal Auto quote records appeared in the OneShield quote list even though no bind completed.
- Replacement: Require an explicit live-create flag and keep bind behind a separate explicit flag.
- Attempt: Map OneShield object IDs only by zip order from `OBJECT_TREE`.
- Symptom: Dynamic tree nodes and inserted/reordered objects could route navigation to the wrong node.
- Replacement: Use live tree labels/orders for known navigation nodes such as driver, vehicle, and coverages, plus live layout field-name substitution.

**Open Questions**
- Existing replay uses a captured happy-path Auto shape and simple test-data substitution. Broader data variation still needs validation before treating it as a generic Auto API.
- The captured traffic did not include a logout/unlock endpoint; UI exit/logout or OneShield session timeout may still be needed to release visible locks.

### 2026-05-21 - Personal Auto UW Referral Override Interaction

**Context**
- LOB: Personal Auto
- Scenario: Live DOM probe on Jacob Smith quote (3 conditions: under-25, SR-22, revoked license)
- Goal: Understand exact mechanics for overriding soft UW conditions so the policy flow can continue to bind.

**Confirmed Behavior**
- The UW Issues grid has 6 columns: ASSET | CONDITION | TYPE | PRODUCER/SUB-PRODUCER COMMENTS | UNDERWRITER'S COMMENTS* | OVERRIDDEN?*
- `OVERRIDDEN?*` is the last column (`x-grid-cell-last`). Its `<td>` carries `gridCellEditable` when the current user can override that condition, or `gridCellReadOnly` when they cannot.
- `gridCellReadOnly` on the Overridden? cell means the application fully blocks the editor from opening for that row — it is not a Playwright interaction issue. The current user lacks the authority level to clear that condition.
- `UNDERWRITER'S COMMENTS*` is the second-to-last column. Its `<td>` always carries `gridCellMandatory gridCellEditable` — a comment is required before accept.
- Clicking the `div` inside an editable Overridden? cell opens a standard HTML `<select>` (not an ExtJS boundlist). Options: `- Select -`, `Yes`, `No`. Use `page.get_by_role("option", name="Yes").click()` after opening.
- Clicking the Comments cell activates a `<textarea>`. Fill via JS: `document.activeElement.value = comment` + dispatch `input` and `change` events.
- `>>> accept` button is visible as `page.get_by_role("button", name=">>> accept")`.
- Clicking `>>> accept` when all rows are not yet set to `Yes` shows dialog: _"You must override every underwriting trigger before accepting this transaction. If the override flag is grayed out, you do not have the authority to clear this..."_
- When all rows are set correctly, clicking `>>> accept` shows a confirmation dialog (`OK` button). After OK, the app navigates away from the UW referral screen.
- Jacob Smith's quote could NOT be fully overridden because the revoked-license condition row had `gridCellReadOnly` on the Overridden? cell.

**Stable Selectors / Methods**
- Check editability via JS: `document.querySelectorAll('[id^="gridview"] tr.x-grid-row')` → for each row, check `cells[cells.length - 1].classList.contains('gridCellReadOnly')`.
- `can_be_overridden()` returns True only when NO row has `gridCellReadOnly` on the last cell.
- `override_all_and_accept(comment)` iterates all rows, JS-clicks the last cell `div`, selects "Yes" option, JS-clicks the second-to-last cell, fills the textarea, then clicks `>>> accept` and confirms the dialog.
- Both methods live in `ui/pages/auto/uw_referral_page.py`.

**Runner Integration**
- `auto_runner.py` step 9: if UW referral is visible after rating, call `_try_uw_override()`. If override succeeds, fall through to `_create_policy_or_uw()` → bind. If not overridable, record `uw_referral` outcome with note "not overridable by current user".
- `_create_policy_or_uw()` mid-flow UW checks still return early as `uw_referral` (not extended with override logic yet — this is a safe starting point since override logic in the mid-bind path needs separate validation).

**Known Failed Approaches**
- Attempt: Click `>>> accept` after overriding only 2 of 3 rows (revoked-license row was read-only).
- Symptom: Dialog blocked with "must override every underwriting trigger" error.
- Replacement: `can_be_overridden()` pre-checks ALL rows before attempting override; if any row is read-only, skip override and return `uw_referral` immediately.

**Open Questions**
- Are there test personas whose conditions are ALL editable (none read-only)? A clean soft-UW profile with 1–2 overridable conditions is needed to validate the full override→bind path end to end.
- Does `_create_policy_or_uw()`'s mid-flow UW detection also need override logic? Currently it terminates early; this can be extended once the step-9 path is validated.

### 2026-05-21 - Personal Auto SR-22 UW Override Headed Probe

**Context**
- LOB: Personal Auto
- Scenario: `python tools\probe_uw_override.py --persona sr22 --headed --slow-mo 500 --hold-ms 30000 --skip-runner`
- Test data: in-memory `PROBE_SR22` persona in `tools/probe_uw_override.py`

**Confirmed Behavior**
- The live headed probe reached a one-row SR-22 UW referral after rating.
- The row's `OVERRIDDEN?*` cell was editable and `UWReferralPage.can_be_overridden()` returned `True`.
- `UWReferralPage.override_all_and_accept()` successfully set `Overridden?` to `Yes`, filled the underwriter comment, clicked `>>> accept`, confirmed `OK`, and navigated away from the UW referral page.
- This headed probe used `--skip-runner`, so it validated the manual override/accept interaction but did not run the subsequent full bind path.

**Stable Selectors / Methods**
- `OVERRIDDEN?*` uses an ExtJS grid cell editor, not a native HTML `<select>`, in this SR-22 case.
- Activate the last grid cell, target `.x-grid-editor input`, open the visible `.x-boundlist-item` menu, select exact option text `Yes`, and verify the last cell text commits to `Yes`.
- `tools/probe_uw_override.py` now supports `--headed`, `--slow-mo`, `--hold-ms`, and `--skip-runner` for watchable UW debugging.

**Required Waits**
- Wait until the committed grid cell text is `Yes` before moving to the comments cell.
- Hold the headed browser open after the probe when visual inspection is needed.

**Known Failed Approaches**
- Attempt: Treat the `OVERRIDDEN?*` editor as a visible native `<select>`.
- Symptom: `override_all_and_accept()` raised `RuntimeError: Could not find visible <select> for Overridden? cell on row 0`.
- Replacement: Use the ExtJS grid editor input plus visible bound-list option selection, then verify the cell text changed to `Yes`.

**Open Questions**
- Full runner validation still needs to confirm the accepted SR-22 UW referral can continue through request issue, billing, and bind.

### 2026-05-21 - Personal Auto SR-22 Filing State

**Context**
- LOB: Personal Auto
- Page: Driver Information
- Scenario: headed SR-22 probe after `Certificate of Insurance Required? = Yes`

**Confirmed Behavior**
- Selecting `Certificate of Insurance Required? = Yes` reveals a conditional `SR-22 Filing State` combobox on Driver Information.
- Existing tests/data previously did not handle this field; `DriverInfoPage` only answered the SR-22 radio and continued.
- The live headed probe passed Driver Info after selecting `SR-22 Filing State = Massachusetts`, reached UW, accepted the UW override, completed Contact Information with Email permission, and clicked re-rate.

**Stable Selectors / Methods**
- `DriverInfoPage.set_sr22_required(data)` now waits for the conditional filing-state field when `SR22` is `Yes`.
- `DriverInfoPage.set_sr22_filing_state(data)` selects `data["SR22FilingState"]`, `data["SR-22 Filing State"]`, `data["State"]`, or falls back to `Massachusetts`.
- The probe persona now explicitly includes `SR22FilingState = Massachusetts`.
- AI-generated Auto personas should include `SR22FilingState` when `SR22 = Yes`.

**Required Waits**
- Wait for the `SR-22 Filing State` combobox to become visible after answering the SR-22 radio.
- Use the shared ExtJS option selector for the filing-state combobox.

**Known Failed Approaches**
- Attempt: Answer SR-22 Yes and immediately save or navigate to Vehicle Info.
- Symptom: The conditional filing-state field remained unfilled and blocked the SR-22 flow.
- Replacement: Fill `SR-22 Filing State` before Driver Info save/navigation.

**Open Questions**
- None for the isolated SR-22 probe; full bind validation after re-rate is still separate.

### 2026-05-21 - Personal Auto Overridable UW Override BDD Outline

**Context**
- LOB: Personal Auto
- Scenario: `ui/tests/auto_uw_rules/test_auto_uw_rules.py::test_overridable_uw_referral_to_bind`
- Feature: `ui/features/auto/auto_uw_rules.feature`
- Test data: `testdata/static/auto/AutoUWRulesData.json`, `UW_TC_001`, `UW_TC_003`, and `UW_TC_005`

**Confirmed Behavior**
- A dedicated BDD scenario outline now covers confirmed overridable UW continuation paths: quote creation, UW referral assertion, UW override/accept, Contact Information Email permission, re-rate, normal request issue/delivery/billing/bind, and policy summary extraction.
- The outline includes SR-22-only (`UW_TC_001`), under-25-only (`UW_TC_003`), and combined SR-22 + under-25 (`UW_TC_005`).
- The expected condition cell supports semicolon-separated condition substrings so combined UW cases can verify multiple rows.
- The same UW assertion step text is registered in both auto and homeowner step modules, so semicolon-separated condition handling must stay consistent in both modules and in `UWReferralPage.assert_uw_condition()`.
- Pytest collection confirmed both examples and all step definitions resolve without launching a browser.

**Stable Selectors / Methods**
- UW override uses `UWReferralPage.override_all_and_accept()`.
- Post-UW Contact Information uses `ContactInformationPage.complete_email_permission_if_visible()`.
- Re-rate uses `CreatePolicyPage.click_re_rate_if_visible()`.
- Normal bind tail reuses the existing `When I create a policy from the quote` step.

**Required Waits**
- Reuse each page object's existing app-ready waits after UW accept, contact save/next, re-rate, request issue, next, next, and bind.

**Known Failed Approaches**
- Attempt: Let only the auto step split semicolon-separated expected conditions.
- Symptom: Depending on pytest-bdd plugin registration order, the shared homeowner step could receive the auto UW assertion and pass the whole string to the page object, producing a gridcell locator for `SR-22 ...; All drivers under 25...`.
- Replacement: Split combined expected conditions in both shared step definitions and defensively inside `UWReferralPage.assert_uw_condition()`.

**Open Questions**
- The scenario has not yet been run live through final bind in this session; collection only was used to avoid creating another live bound policy without explicit confirmation.

### 2026-05-21 - Personal Auto Under-25 UW Override Probe

**Context**
- LOB: Personal Auto
- Scenario: `python tools\probe_uw_override.py --persona under25 --headed --slow-mo 500 --hold-ms 30000 --skip-runner`
- Test data: in-memory `PROBE_UNDER25` persona in `tools/probe_uw_override.py`

**Confirmed Behavior**
- The live headed probe reached a one-row under-25 UW referral after rating.
- The visible condition was `All drivers under 25 years of age.`
- The row's `OVERRIDDEN?*` cell was editable and `UWReferralPage.can_be_overridden()` returned `True`.
- `UWReferralPage.override_all_and_accept()` successfully accepted the UW referral.
- The post-UW sequence matched the SR-22-only flow through re-rate: Contact Information appeared, Email contact permission was selected/saved, the page continued, and `re-rate` was visible and clicked successfully.
- This probe used `--skip-runner` and did not continue through final bind.

**Stable Selectors / Methods**
- The same UW override method used for SR-22 also works for the under-25 row.
- The same Contact Information and re-rate methods work after accepting the under-25 referral.

**Required Waits**
- Reuse the established waits: commit `Overridden? = Yes`, fill comment, accept/OK, Contact Information save/next, then re-rate.

**Known Failed Approaches**
- None in the headed under-25 probe.

**Open Questions**
- Final bind after under-25 re-rate has not been run live in this session.

### 2026-05-21 - Personal Auto SR-22 Plus Under-25 UW Override Probe

**Context**
- LOB: Personal Auto
- Scenario: `python tools\probe_uw_override.py --persona sr22-under25 --headed --slow-mo 500 --hold-ms 30000 --skip-runner`
- Test data: in-memory `PROBE_SR22_UNDER25` persona in `tools/probe_uw_override.py`

**Confirmed Behavior**
- The live headed probe reached a two-row UW referral after rating.
- Visible conditions were `SR-22 / Certificate of Insurance Indicator is checked` and `All drivers under 25 years of age.`
- Both rows had editable `OVERRIDDEN?*` cells and `UWReferralPage.can_be_overridden()` returned `True`.
- Initial two-row override attempt failed because moving to the next row could cancel the prior comment editor before it committed.
- After committing each underwriter comment with `Tab`, `UWReferralPage.override_all_and_accept()` successfully accepted both rows.
- The post-UW sequence matched the SR-22-only and under-25-only flows through re-rate: Contact Information appeared, Email contact permission was selected/saved, the page continued, and `re-rate` was visible and clicked successfully.
- This probe used `--skip-runner` and did not continue through final bind.

**Stable Selectors / Methods**
- `override_all_and_accept()` must commit each row comment before editing the next UW row.
- The same ExtJS override cell editor and Contact Information/re-rate methods work for multi-row UW grids.

**Required Waits**
- After filling each underwriter comment textarea, press `Tab` and wait briefly so OneShield commits the grid edit before moving to the next row.

**Known Failed Approaches**
- Attempt: Fill row comments and immediately move to the next override cell.
- Symptom: `>>> accept` was blocked with `UW accept was blocked — not all conditions could be overridden.`
- Replacement: Commit each comment edit before continuing to the next row.

**Open Questions**
- Final bind after combined SR-22 + under-25 re-rate has not been run live in this session.

### Template

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
