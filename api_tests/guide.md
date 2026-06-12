# OneShield Auto API Replay Guide

This guide explains the API testing work added under `api_tests/`, what was proven, how the Personal Auto browserless replay works, and how to run it safely.

## What Was Built

The main implementation is `api_tests/oneshield_api_replay.py`.

It is a `requests`-based client that replays selected OneShield requests from a captured successful UI flow:

- source capture: `reports/auto_api_flow_TC_ID_0001_20260519.json`
- test data: `testdata/static/auto/AutoData.json`
- output summary: `policy_summary/policy_reports_api_auto.csv`
- local key payload export: `api_tests/artifacts/auto_rate_bind_payloads_20260519.json`

The payload export is intentionally local-only and ignored by Git. It can contain live OneShield session IDs, transaction IDs, object IDs, and submitted field values from the capture.

This stays separate from the Playwright UI framework. The UI framework still owns BDD/page-object browser flows; this API work lives under `api_tests/` and uses `requests`.

## Confirmed Result

The API replay successfully created and bound a Personal Auto policy without a browser.

Validated bound policy:

```text
Policy Number: PA10134896357-00
Customer: Alan Carter
TC_ID: TC_ID_0011
Final page: Policy | Current Summary
Premium captured in CSV: $ 2,235.75
CSV: policy_summary/policy_reports_api_auto.csv
```

The replay was tested one checkpoint at a time:

```text
rate            -> premium | summary
request-issue   -> Delivery Preferences
verify-billing  -> quote | verify billing choices
bind            -> Policy | Current Summary
```

## Safety Rules

These API calls are live OneShield actions. They create real quote/customer records, and bind creates a real policy.

The script has guard flags for that reason:

- `--allow-live-create` is required for `--action run-auto`.
- `--allow-bind` is additionally required for `--stop-after bind`.
- Direct CLI actions `rate`, `request-issue`, and `bind` are intentionally blocked because those actions need live state built by the full replay.

Safe inspection commands do not create records:

```powershell
python api_tests\oneshield_api_replay.py --action summary
python api_tests\oneshield_api_replay.py --action export-payloads
pytest api_tests\test_oneshield_api_login.py -v -s -m api
```

Commands that create live records:

```powershell
python api_tests\oneshield_api_replay.py --action run-auto --stop-after rate --tc-id TC_ID_0011 --allow-live-create
python api_tests\oneshield_api_replay.py --action run-auto --stop-after request-issue --tc-id TC_ID_0011 --allow-live-create
python api_tests\oneshield_api_replay.py --action run-auto --stop-after verify-billing --tc-id TC_ID_0011 --allow-live-create
```

Command that binds a live policy:

```powershell
python api_tests\oneshield_api_replay.py --action run-auto --stop-after bind --tc-id TC_ID_0011 --allow-live-create --allow-bind
```

## Required Environment

The client uses the same credentials as the UI framework:

```env
PARTNER_NUM=...
USERNAMEE=...
PASSWORD=...
```

Optional base URL override:

```env
ONESHIELD_BASE_URL=https://inforcedev.oneshield.com
```

The replay client also accepts an application URL such as
`https://inforcedev.oneshield.com/oneshield/`. Captured request paths that
start with `/` stay origin-relative, so `/splash.html` is requested from the
host root while `/oneshield/...` requests stay under the OneShield servlet
path.

`USERNAMEE` is intentionally spelled with a double `E`; keep that name.

## Login Flow

`OneShieldApiReplay.login()` does not use hard-coded login field names. It dynamically reads the current login page and extracts state from `pageJSON`.

The login sequence is:

```text
GET  /splash.html
GET  /oneshield/?oswt=EmployeePortal
POST /oneshield/SessionExtendServlet
POST /oneshield/FieldProcessorServlet  # partner number
POST /oneshield/FieldProcessorServlet  # username
POST /oneshield/FieldProcessorServlet  # password
POST /oneshield/GatewayServlet         # TX_NAME=Action.3
```

After login, the client stores live OneShield state:

- `browserTabId`
- `workflowContext`
- `objectTree`
- `hvars`
- page layout
- tree state
- latest transaction/session values

The smoke test is:

```powershell
pytest api_tests\test_oneshield_api_login.py -v -s -m api
```

It checks for HTTP 200, no invalid session page, and response content containing `pageName`.

## Auto API Action Chain

The important captured Gateway actions are:

| Stage | Capture page | TX_NAME | Expected response page |
|---|---|---:|---|
| Login submit | `auto_new_quote` | `Action.3` | post-login app state |
| Coverage prepare | `auto_coverages_rating` | `1534748` | Coverages |
| Rate quote | `auto_premium_summary` | `Action.1753948` | `premium | summary` |
| Request issue | `auto_premium_summary` | `Action.305905` | `Delivery Preferences` |
| Delivery next | `auto_delivery_preferences` | `Action.1262048` | `billing plan` |
| Billing next | `auto_billing_plan` | `Action.1504046` | `quote | verify billing choices` |
| Bind | `auto_verify_billing` | `Action.1780148` | `Policy | Current Summary` |

Important correction: `TX_NAME=1534748` is not the final rate transition. It prepares/saves coverage state and remains on Coverages. The actual transition to Premium Summary is `TX_NAME=Action.1753948`.

## Why Replay Is Stateful

OneShield request bodies are not static API payloads. They contain many dynamic values:

- `WORKFLOW_CONTEXT`
- `CURRENT_OBJECT`
- `OBJECT_TREE`
- `SELECTED_NODE`
- `USER_SESSION_GUID`
- `DRAGON_TRANSACTION_ID`
- `HTTP_SESSION_ID`
- dynamic field names like `bv_<object_id>_<attribute_path>`

Captured payloads cannot be posted back unchanged. The replay updates these values after every response.

## How Dynamic Mapping Works

`OneShieldApiReplay.replay_event()` builds each outgoing form from the captured request, then normalizes it with live state.

Main helpers:

- `_update_state_from_response()` reads fresh `pageJSON` after each request.
- `_map_context_object()` maps captured workflow object IDs to live workflow object IDs.
- `_replace_dynamic_tokens()` replaces object IDs and `bv_*` field names.
- `_layout_field_candidates()` reads current live layout and finds valid `bv_*` names by attribute suffix.
- `_selected_tree_node_for_event()` selects live tree nodes for Driver, Vehicle, and Coverages navigation using tree labels/orders.
- `_substitute_auto_data()` swaps captured James Smith values with the selected JSON test case.

This is the core reason browserless replay now works: each request uses the current OneShield state, not stale IDs from the capture.

## Test Data Substitution

The replay starts from a captured `TC_ID_0001` James Smith flow and substitutes data from `testdata/static/auto/AutoData.json`.

Currently supported substitutions include:

- first name
- last name
- full name
- DOB
- phone
- email with `{timestamp}`
- address
- ZIP
- city

The successful bind used `TC_ID_0011`:

```text
Alan Carter
55 Prospect Street
Springfield, MA 01101
2018 BMW M3
Gold coverage
Direct Billed
```

## CLI Usage

Print key captured request identifiers:

```powershell
python api_tests\oneshield_api_replay.py --action summary
```

Export decoded captured payloads:

```powershell
python api_tests\oneshield_api_replay.py --action export-payloads
```

Login only:

```powershell
python api_tests\oneshield_api_replay.py --action login
```

Run to rate:

```powershell
python api_tests\oneshield_api_replay.py --action run-auto --stop-after rate --tc-id TC_ID_0011 --allow-live-create
```

Run through rate and open Rating Detail:

```powershell
python api_tests\oneshield_api_replay.py --action run-auto --stop-after rating-detail --tc-id TC_ID_0011 --allow-live-create
```

Run to request issue:

```powershell
python api_tests\oneshield_api_replay.py --action run-auto --stop-after request-issue --tc-id TC_ID_0011 --allow-live-create
```

Run to billing plan:

```powershell
python api_tests\oneshield_api_replay.py --action run-auto --stop-after billing-plan --tc-id TC_ID_0011 --allow-live-create
```

Run to verify billing:

```powershell
python api_tests\oneshield_api_replay.py --action run-auto --stop-after verify-billing --tc-id TC_ID_0011 --allow-live-create
```

Run through bind:

```powershell
python api_tests\oneshield_api_replay.py --action run-auto --stop-after bind --tc-id TC_ID_0011 --allow-live-create --allow-bind
```

## Programmatic Usage

Example:

```python
from api_tests.oneshield_api_replay import OneShieldApiReplay, load_auto_test_data

client = OneShieldApiReplay()
try:
    test_data = load_auto_test_data("testdata/static/auto/AutoData.json", "TC_ID_0011")
    result = client.run_captured_auto_flow(
        test_data,
        stop_after="verify-billing",
    )
    print(result["last_page"])
finally:
    client.close()
```

For bind:

```python
result = client.run_captured_auto_flow(
    test_data,
    stop_after="bind",
    allow_bind=True,
)
```

## Result Shape

`run_captured_auto_flow()` returns a dictionary like:

```json
{
  "stop_after": "bind",
  "completed": true,
  "blocked_reason": "",
  "policy_number": "PA10134896357-00",
  "premium": "$ 2,235.75",
  "last_page": "Policy | Current Summary",
  "workflow_context": "117202,10134933557,1",
  "messages": [],
  "trace": [],
  "summary": {},
  "ui_data": {},
  "stage_ui_data": {},
  "report_path": "policy_summary\\policy_reports_api_auto.csv"
}
```

Premium assertions use the Premium Summary UI model at
`stage_ui_data["rate"]["field_values"]["Premium"]`. Rating Detail
`business_values["calculated_total_premium"]` is a diagnostic sum of selected
`Policy Term Factor` rows and may not equal the premium displayed by
OneShield. Reports should expose that mismatch and assert against Premium
Summary.

Regression sweeps pass `continue_soft_uw=True`. For editable SR-22 and
under-25 referrals, the replay sets every `Overridden?` value to `Yes`, adds
an underwriter comment, posts the live `>>> accept` action, completes Contact
Information when shown, and re-rates back to Premium Summary. Read-only UW
rows remain blocked and are not forced through.

`trace` records each replayed event with:

- capture page
- `TX_NAME`
- HTTP status
- response URL
- resulting page name
- workflow context
- OneShield messages

## UI Data Snapshots

OneShield Gateway responses contain the UI model in `pageJSON.layout`. The
replay result exposes the assertable part of that model without returning raw
session-bearing `pageJSON` internals:

- `ui_data`: visible fields, lookup display values, page actions, tabs, and
  messages for the final page reached.
- `stage_ui_data`: the same snapshot for each reached replay checkpoint such
  as `rate`, `rating-detail`, `request-issue`, `verify-billing`, and
  `bind`.

Example after a rate stop:

```python
result = oneshield_api_client.run_captured_auto_flow(test_data, stop_after="rate")

rate_ui = result["stage_ui_data"]["rate"]
assert rate_ui["page_name"] == "premium | summary"
assert rate_ui["field_values"]["Premium"]
assert rate_ui["field_values"]["Surcharges"] == ["$ 0.00"]
```

`fields` keeps both the raw cell `value` and the UI-facing `display_value`.
That matters for OneShield lookups, where the response may store a code such
as `1` while the UI shows `Direct Billed`.

Only fields exposed by the page reached at that checkpoint are present. The
captured rate checkpoint reaches the Premium Summary page, which exposes
premium summary fields and a `rating detail` tab. Use
`stop_after="rating-detail"` to post that live tab action and inspect or
assert `result["stage_ui_data"]["rating-detail"]`.

Rating Detail uses a OneShield grid instead of plain label/value fields. Its
rows are under `result["stage_ui_data"]["rating-detail"]["grids"]`, keyed by
UI column names:

```python
detail_ui = result["stage_ui_data"]["rating-detail"]
rating_grid = detail_ui["grids"][0]
base_rate_rows = [row for row in rating_grid["rows"] if row.get("Factor") == "Base Rate"]

assert base_rate_rows
assert base_rate_rows[0]["F.Value"]
```

The snapshot omits OneShield object and row identifiers from grid rows.
Live validation on May 22, 2026 reached `premium | rating detail` for
`TC_ID_0011` and returned the `premium debug information` grid with `Base
Rate` rows for Bodily Injury and Property Damage. OneShield loaded 25 rows in
that first response while the grid reported 124 total rows, so pagination is
still needed when assertions require later Rating Detail rows.

The API replay can now collect paged Rating Detail rows from the
`premium debug information` datamart grid through `DataSearchServlet` using
OneShield's list-navigation action values. The initial UI snapshot still shows
the first page only, but `result["rating_factors"]` exposes the collected rows
and a smaller `business_values` object for practical assertions:

```python
result = oneshield_api_client.run_captured_auto_flow(test_data, stop_after="rating-detail")

factors = result["rating_factors"]
assert factors["complete"]
assert factors["row_count"] == factors["total_rows"]

business = factors["business_values"]
assert business["base_rates"]
assert business["coverage_premiums"]
assert business["calculated_total_premium"]
```

Live validation on May 25, 2026 for `UW_TC_010` collected all 124 Rating
Detail rows over five pages and returned `complete=True`.

## API UW Rules Checks

UW API assertions use the same visible page model as the UI assertions. A
positive UW test runs a rule case to `stop_after="rate"` and asserts the
Underwriting Referral grid rows from `stage_ui_data["rate"]`:

```python
result = oneshield_api_client.run_captured_auto_flow(test_data, stop_after="rate")
uw_ui = result["stage_ui_data"]["rate"]

assert "underwriting" in uw_ui["page_name"].lower()
assert any(
    row.get("Type") == "Underwriting"
    and "All drivers under 25 years of age" in row.get("Condition", "")
    for grid in uw_ui["grids"]
    for row in grid["rows"]
)
```

`api_tests/test_oneshield_api_uw_rules.py` parametrizes the positive Auto UW
matrix from `AutoUWRulesData.json`: SR-22, suspended/revoked license,
under-25, and the combined cases. The replay resolves the live OneShield
lookup codes from driver-field labels such as `License Status` and
`SR-22/ Certificate of Insurance Required?` before it posts the captured
forms. It also records the UW page as the `rate` checkpoint when OneShield
redirects to Underwriting Referral before the captured Rate Quote action
finishes.

Leased and other non-owned vehicle data also needs a Loss Payee / Additional
Interest row before vehicle save. The API replay now reads that block's live
`Add` button metadata, posts its block object references, and fills the row's
`Interest Type` and `Loss Payee/Additional Interest Name` fields from the live
layout before the normal vehicle save action. Current live traffic identifies
that Add action as `Action.189`.

Live validation on May 22, 2026 passed the full 14-case positive Auto UW API
matrix:

```powershell
pytest api_tests\test_oneshield_api_uw_rules.py -v -s -m api -k uw_referral_snapshot_matches_ui_rule
```

After the leased Loss Payee Add replay was added, focused live validation also
passed the two leased UW cases, `UW_TC_008` and `UW_TC_010`.

The same test module contains a guarded clean-flow bind assertion for the data
available after rate, request issue, and bind:

```powershell
pytest api_tests\test_oneshield_api_uw_rules.py -v -s -m api
pytest api_tests\test_oneshield_api_uw_rules.py -v -s -m api --oneshield-api-allow-bind
```

The second command binds a live test policy. Without
`--oneshield-api-allow-bind`, the bind snapshot test skips.

## CSV Summary

Bound API policies are appended to:

```text
policy_summary/policy_reports_api_auto.csv
```

Columns:

```text
Source
Stop After
TC_ID
Policy Number
Status
Premium
Customer Name
Program
Billing Method
Employment Category
Vehicle Use
Ownership
Policy Coverage Option
Vehicle Type
Vehicle Year
Vehicle Make
Vehicle Model
```

Current confirmed row:

```text
api_auto,bind,TC_ID_0011,PA10134896357-00,Bound,$ 2,235.75,Alan Carter,...
```

## Pytest Fixtures

`api_tests/conftest.py` provides:

```python
oneshield_api_client
```

It creates `OneShieldApiReplay` using:

- `--oneshield-api-capture`
- `--oneshield-base-url`

Example:

```powershell
pytest api_tests\test_oneshield_api_login.py -v -s -m api
```

## Files Added Or Updated

Key files:

- `api_tests/oneshield_api_replay.py`: replay client, CLI, stateful Auto replay.
- `api_tests/conftest.py`: API fixture for `OneShieldApiReplay`.
- `api_tests/test_oneshield_api_login.py`: API login smoke test.
- `api_tests/artifacts/auto_rate_bind_payloads_20260519.json`: exported key captured payloads. This is a local ignored artifact because it can contain live session/request state.
- `policy_summary/policy_reports_api_auto.csv`: API-created Auto policy summary output.
- `docs/ONESHIELD_APP_KNOWLEDGE.md`: persistent OneShield API replay findings.

## Known Limitations

This is not yet a generic OneShield Auto API.

Current constraints:

- It replays the known-good captured Personal Auto shape.
- It assumes the same general happy-path page order as the capture.
- It uses simple substitution from the JSON data row.
- Driver and non-owned vehicle fields needed for the positive Auto UW matrix
  are replayed from live layout lookups. The Loss Payee / Additional Interest
  Add-row path still depends on OneShield exposing the live block button and
  current block object references in the vehicle layout.
- It has been proven for `TC_ID_0011`, but broad variation still needs validation.
- Captured traffic did not include a logout/unlock endpoint.
- Server-side quote locks may require UI exit/logout, session timeout, or an admin unlock mechanism.

## Troubleshooting

If login fails:

- Confirm `.env` has `PARTNER_NUM`, `USERNAMEE`, and `PASSWORD`.
- Run `pytest api_tests\test_oneshield_api_login.py -v -s -m api`.
- Confirm the target app is reachable at `DEFAULT_BASE_URL` or `ONESHIELD_BASE_URL`.

If replay stops early:

- Check `blocked_reason`.
- Check `last_page`.
- Check `messages`.
- Inspect `trace` to see the first unexpected page transition.

If a payload looks stale:

- Check that `WORKFLOW_CONTEXT`, `OBJECT_TREE`, `USER_SESSION_GUID`, and `DRAGON_TRANSACTION_ID` are updated from the latest response.
- Check dynamic `bv_*` keys against the current response layout.
- Check tree navigation nodes for Driver, Vehicle, and Coverages.

If records appear locked:

- Exit the quote normally in the UI if possible.
- Log out from OneShield.
- Wait for OneShield session timeout.
- Use an admin session/lock release tool if one exists.

## fast_mode

`run_captured_auto_flow` accepts `fast_mode=True` which skips all `FieldProcessorServlet` events in the main replay loop. Validated 2026-05-21 for `stop_after="rate"`:

```
normal:    32s  42 requests  completed=True  premium='$ 2,049.45'
fast_mode: 23s  25 requests  completed=True  premium='$ 2,049.45'
```

All 17 FieldProcessorServlet calls in the main loop (including TX-named vehicle cascade and driver handlers) were redundant — GatewayServlet payloads already carry the complete field values. The remaining ~23s is server-side GatewayServlet processing: two setup calls (~2.5s and ~3.2s) and the rate computation (~5.1s). These cannot be reduced from the client.

`fast_mode` has not yet been validated for `stop_after` stages beyond `rate`. Validate before enabling it for `request-issue`, `verify-billing`, or `bind`.

Validated 2026-05-25 for Auto UW referral checks with `stop_after="rate"`:
`UW_TC_001` reached `quote | underwriting referral | underwriter` in 25.76s
with 18 replayed requests, and leased case `UW_TC_010` reached the same page
in 24.78s with 19 replayed requests while preserving the vehicle
Loss Payee/Add-row action (`Action.189`). The UW referral snapshot pytest now
uses `fast_mode=True`.

Additional rate-stop profiling on 2026-05-25 showed the fast-mode path spends
about 3.4s in login, 5.8s in the final Rate Quote action, and the rest building
the live quote/customer/driver/vehicle/coverage workflow state. Posting the
captured Rate Quote action directly after login returned HTTP 200 but remained
on `carrier portal`, so the rate action cannot be dropped onto a fresh session.
Removing `bv_*` business-value fields from the final Rate Quote payload still
reached UW for `UW_TC_001`, but the rate call took 5.72s, effectively the same
as the full payload. The rate form is small; the bottleneck is server-side
rating and mandatory workflow setup, not upload size.

API pytest auto-parallelism is capped at 6 workers by default. A 10-worker run
of the 14-case UW referral matrix passed, but individual calls stretched to
about 60s under server load, so 6 is the safer default ceiling for routine
validation. Passing `-n` explicitly still overrides the automatic default.

## Recommended Next Improvements

- Add a true dry-run mode that logs generated live-substituted forms without posting them.
- Add pytest coverage for `summary`, payload export, and guarded CLI behavior.
- Add a dedicated API bind test marked as destructive/live and skipped by default.
- Expand substitution beyond the current happy-path Auto values.
- Capture or discover the proper logout/unlock endpoint if OneShield exposes one.
- Add richer policy summary extraction from the final `Policy | Current Summary` response instead of relying primarily on regex and test data.
