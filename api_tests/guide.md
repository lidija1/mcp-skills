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
  "report_path": "policy_summary\\policy_reports_api_auto.csv"
}
```

`trace` records each replayed event with:

- capture page
- `TX_NAME`
- HTTP status
- response URL
- resulting page name
- workflow context
- OneShield messages

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

## Recommended Next Improvements

- Add a true dry-run mode that logs generated live-substituted forms without posting them.
- Add pytest coverage for `summary`, payload export, and guarded CLI behavior.
- Add a dedicated API bind test marked as destructive/live and skipped by default.
- Expand substitution beyond the current happy-path Auto values.
- Capture or discover the proper logout/unlock endpoint if OneShield exposes one.
- Add richer policy summary extraction from the final `Policy | Current Summary` response instead of relying primarily on regex and test data.
