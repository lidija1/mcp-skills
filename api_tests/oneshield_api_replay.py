"""Replay selected OneShield API calls from a captured UI flow.

This helper lives with the API test assets and intentionally stays separate
from the Playwright BDD framework. It loads request bodies from an
ApiFlowRecorder JSON artifact and can post the login, rate, and bind
GatewayServlet actions through requests.Session.

Important: OneShield GatewayServlet payloads are stateful. Captured bodies
contain session IDs, object IDs, transaction IDs, and object trees. A stale
capture is useful for endpoint analysis and replay experiments, but a reliable
browserless full policy flow must update those values from each prior response.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urljoin

import requests
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.file_writer import save_summary_to_csv

load_dotenv()


def _latest_capture_file() -> Path:
    candidates = sorted((ROOT_DIR / "reports").glob("auto_api_flow_TC_ID_0001_*.json"))
    return candidates[-1] if candidates else ROOT_DIR / "reports" / "auto_api_flow_TC_ID_0001_20260519.json"


DEFAULT_CAPTURE = _latest_capture_file()
DEFAULT_BASE_URL = "https://inforcedev.oneshield.com/oneshield/"
DEFAULT_PAYLOAD_EXPORT = ROOT_DIR / "api_tests" / "artifacts" / "auto_rate_bind_payloads_latest.json"
DEFAULT_AUTO_DATA = Path("testdata/static/auto/AutoData.json")
FIELD_VAR_PATTERN = re.compile(r"\bbv_(\d{6,})_([A-Za-z0-9p]+)\b")


@dataclass(frozen=True)
class CapturedRequest:
    """A request selected from the API flow capture."""

    page: str
    method: str
    url: str
    path: str
    headers: dict[str, str]
    form: dict[str, str]


class OneShieldApiReplay:
    """Small API client for replaying captured OneShield form posts."""

    def __init__(
        self,
        capture_path: str | Path = DEFAULT_CAPTURE,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 120,
    ) -> None:
        self.capture_path = Path(capture_path)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.capture = json.loads(self.capture_path.read_text(encoding="utf-8"))
        self.state: dict[str, Any] = {}
        self.id_map: dict[str, str] = {}
        self.replay_trace: list[dict[str, Any]] = []

    def close(self) -> None:
        """Close the local HTTP session.

        The captured traffic does not include a OneShield logout/unlock call,
        so this only closes client-side sockets; server-side record locks may
        still require normal UI exit/logout or session timeout.
        """
        self.session.close()

    def login(
        self,
        partner_number: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> requests.Response:
        """Replay the isolated login sequence captured from the browser.

        The capture shows login as:
        1. GET /splash.html
        2. GET /oneshield/?oswt=EmployeePortal
        3. POST /oneshield/SessionExtendServlet
        4. POST /oneshield/FieldProcessorServlet for partner/user/password
        5. POST /oneshield/GatewayServlet with TX_NAME=Action.3

        The credential values default to PARTNER_NUM, USERNAMEE, and PASSWORD.
        """
        partner_number = partner_number if partner_number is not None else os.getenv("PARTNER_NUM", "")
        username = username if username is not None else os.getenv("USERNAMEE", "")
        password = password if password is not None else os.getenv("PASSWORD", "")

        self.session.get(self._absolute_url("/splash.html"), timeout=self.timeout).raise_for_status()
        portal_response = self.session.get(
            self._absolute_url("/oneshield/?oswt=EmployeePortal"),
            timeout=self.timeout,
        )
        portal_response.raise_for_status()
        page_json = self._extract_page_json(portal_response.text)
        hvars = self._hvars(page_json)
        login_fields = self._login_field_names(page_json)

        self.session.post(
            self._absolute_url("/oneshield/SessionExtendServlet"),
            data={
                "USER_SESSION_GUID": page_json["browserTabId"],
                "actionId": "2",
            },
            timeout=self.timeout,
        ).raise_for_status()

        credential_values = {
            "partner": partner_number,
            "username": username,
            "password": password,
        }
        for logical_name, field_name in login_fields.items():
            self.session.post(
                self._absolute_url("/oneshield/FieldProcessorServlet"),
                data={
                    "value": credential_values[logical_name],
                    "name": field_name,
                    "MT_LOCALE_ID": hvars.get("MT_LOCALE_ID", "101"),
                    "EXCHANGE_ID": hvars.get("EXCHANGE_ID", "1218"),
                    "pageActionId": "2",
                    "USER_SESSION_GUID": page_json["browserTabId"],
                },
                timeout=self.timeout,
            ).raise_for_status()

        login_event = self.find_gateway_event(page="auto_new_quote", tx_name="Action.3")
        login_submit = self._captured_request(login_event)
        form = dict(login_submit.form)
        form.update(hvars)
        form.update(
            {
                "dragon-ui-page": "true",
                "osst": page_json["browserTabId"],
                "OBJECT_TREE": page_json["objectTree"],
                "WORKFLOW_CONTEXT": page_json["workflowContext"],
                "FormIsSubmitted": "false",
                "SELECTED_NODE": "",
                "TX_NAME": "Action.3",
                "CURRENT_SKIN": str(page_json.get("currentSkin", "4104")),
                "CURRENT_OBJECT": page_json["workflowContext"].split(",")[1],
                "USER_SESSION_GUID": page_json["browserTabId"],
                "namefields": ",".join(login_fields.values()),
                "namefieldslookuplist": "",
                login_fields["partner"]: partner_number,
                login_fields["username"]: username,
                login_fields["password"]: password,
            }
        )
        response = self._send_form(login_submit, form)
        self._update_state_from_response(response, login_event)
        return response

    def rate_quote(self) -> requests.Response:
        """Post the captured Auto Rate Quote GatewayServlet action."""
        return self.post_gateway_action(page="auto_premium_summary", tx_name="Action.1753948")

    def bind_policy(self) -> requests.Response:
        """Post the captured Auto Bind GatewayServlet action."""
        return self.post_gateway_action(page="auto_verify_billing", tx_name="Action.1780148")

    def request_issue(self) -> requests.Response:
        """Post the captured Request Issue action before delivery/billing/bind."""
        return self.post_gateway_action(page="auto_premium_summary", tx_name="Action.305905")

    def open_auto_rating_detail(self, test_data: dict[str, Any] | None = None) -> requests.Response:
        """Open Rating Detail from the live Auto Premium Summary response.

        For UW-referred quotes the current page is the Underwriting Referral tab,
        not the Premium Summary tab — but the Summary tab is still available in the
        tab bar.  Before switching to Rating Detail, navigate to Summary first so
        that the premium regex has a chance to match a '$' value in the response
        text.  The matched value is stored in self._captured_summary_premium and
        used by _build_auto_result() when the final response carries no premium.
        """
        summary_tx = self._state_button_action("tabBarButtons", "summary")
        if summary_tx:
            summary_resp = self.post_gateway_action_from_template(
                page="auto_premium_summary",
                template_tx_name="Action.305905",
                tx_name=summary_tx,
                test_data=test_data,
            )
            self._captured_summary_premium = self._first_match(
                r"\$ ?[0-9,]+\.\d{2}", summary_resp.text
            )

        tx_name = self._state_button_action("tabBarButtons", "rating detail")
        return self.post_gateway_action_from_template(
            page="auto_premium_summary",
            template_tx_name="Action.305905",
            tx_name=tx_name,
            test_data=test_data,
        )

    def get_rating_detail_factors(self) -> dict[str, Any]:
        """Parse rating factors from the current Rating Detail page state.

        Returns a dict with:
          - base_rates: list of {coverage, value} for all Base Rate rows
          - factors: all rows as list of dicts with column-label keys
          - total_out: highest 'Out' value seen (approximate total premium contribution)
        """
        grid_rows = self._collect_grid_rows("premium debug information")
        rows = grid_rows["rows"]

        base_rates = [
            {"coverage": r.get("Coverage", ""), "value": r.get("F.Value", "")}
            for r in rows if r.get("Factor") == "Base Rate"
        ]
        out_vals = []
        for r in rows:
            try:
                out_vals.append(float(str(r.get("Out", "")).replace(",", "")))
            except (ValueError, TypeError):
                pass

        return {
            "base_rates": base_rates,
            "factors": rows,
            "total_out": max(out_vals) if out_vals else None,
            "summary_premium": getattr(self, "_captured_summary_premium", None) or "",
            "row_count": len(rows),
            "total_rows": grid_rows["total_rows"],
            "loaded_pages": grid_rows["loaded_pages"],
            "complete": grid_rows["complete"],
            "business_values": self._rating_business_values(rows),
        }

    def _collect_grid_rows(
        self,
        label_contains: str,
        max_pages: int = 20,
    ) -> dict[str, Any]:
        """Collect all available rows for a paged OneShield grid/list block.

        OneShield only loads the current grid page into `valueRecords`. When the
        block exposes list-navigation metadata, use the same block-level "next"
        action that the UI uses and append each returned page until totalRows is
        satisfied or the server stops returning a new page.
        """
        snapshot = self._visible_grid_by_label(label_contains)
        if not snapshot:
            return {
                "rows": [],
                "total_rows": 0,
                "loaded_pages": 0,
                "complete": True,
            }

        rows = list(snapshot["rows"])
        total_rows = self._to_int(snapshot.get("total_rows")) or len(rows)
        loaded_pages = 1 if rows else 0
        page_signatures = {self._rows_signature(rows)} if rows else set()

        while total_rows and len(rows) < total_rows and loaded_pages < max_pages:
            block = self._visible_grid_block_by_label(label_contains)
            if not block:
                break

            if block.get("datamart") is True:
                snapshot = self._load_datamart_grid_page(block, list_action="91")
            elif isinstance(block.get("listNavNext"), dict):
                self._post_grid_navigation(block, direction="next")
                snapshot = self._visible_grid_by_label(label_contains)
            else:
                break

            if not snapshot:
                break

            page_rows = list(snapshot["rows"])
            signature = self._rows_signature(page_rows)
            if not page_rows or signature in page_signatures:
                break

            rows.extend(page_rows)
            page_signatures.add(signature)
            loaded_pages += 1
            total_rows = self._to_int(snapshot.get("total_rows")) or total_rows

        return {
            "rows": rows,
            "total_rows": total_rows,
            "loaded_pages": loaded_pages,
            "complete": not total_rows or len(rows) >= total_rows,
        }

    def _load_datamart_grid_page(
        self,
        block: dict[str, Any],
        list_action: str,
    ) -> dict[str, Any]:
        """Load the next page for a datamart grid through DataSearchServlet."""
        grid = block.get("grid", {})
        raw_columns = [
            column
            for column in grid.get("columns", [])
            if isinstance(column, dict) and column.get("dataIndex")
        ]
        public_columns = [
            self._grid_column(column)
            for column in raw_columns
            if not self._internal_grid_column(self._grid_column(column))
        ]
        diagnostics = self.state.get("diagnostics", {})
        hvars = self._hvars(self.state)
        workflow_context = str(self.state.get("workflowContext", ""))
        action_id = workflow_context.split(",")[0] if "," in workflow_context else workflow_context
        params = {
            "transactionId": str(
                diagnostics.get("transactionId")
                or hvars.get("DRAGON_TRANSACTION_ID", "")
            ),
            "USER_SESSION_GUID": str(self.state.get("browserTabId", "")),
            "blockId": str(block.get("id", "")),
            "listObjectId": str(block.get("listObjectId") or block.get("objectId", "")),
            "actionId": action_id,
            "listAction": list_action,
            "multiSortString": "",
            "dataIndices": ",".join(str(column.get("dataIndex", "")) for column in raw_columns),
            "cellBvIds": ",".join(str(column.get("cellBvId", "")) for column in raw_columns),
            "cellFESs": ",".join(str(column.get("fes", "")) for column in raw_columns),
        }
        response = self.session.post(
            self._absolute_url("/oneshield/DataSearchServlet"),
            data=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        page_grid = {"valueRecords": payload.get("valueRecords", [])}
        return {
            "label": str(block.get("label", "")).strip(),
            "total_rows": payload.get("totalRows"),
            "start_row": payload.get("startRow"),
            "end_row": payload.get("endRow"),
            "rows": self._grid_rows(page_grid, public_columns),
        }

    def _post_grid_navigation(
        self,
        block: dict[str, Any],
        direction: str,
    ) -> requests.Response:
        nav_keys = {
            "first": ("listNavFirst", "first"),
            "previous": ("listNavPrevious", "prev"),
            "next": ("listNavNext", "next"),
            "last": ("listNavLast", "last"),
        }
        if direction not in nav_keys:
            raise ValueError(f"Unsupported grid navigation direction: {direction!r}")

        nav_key, button_label = nav_keys[direction]
        nav = block.get(nav_key)
        if not isinstance(nav, dict):
            raise LookupError(f"Current grid block has no {nav_key!r} metadata")

        event = self.find_gateway_event(page="auto_premium_summary", tx_name="Action.305905")
        request = self._captured_request(event)
        form = self._stateful_form(request.form, {}, event)
        button = self._state_layout_block_button(button_label)
        tx_name = str(button.get("actionIdText", "")).strip()
        if not tx_name:
            raise LookupError(f"Current layout block button {button_label!r} has no actionIdText")

        form["TX_NAME"] = tx_name
        form["validateFlag"] = str(button.get("validationType", form.get("validateFlag", "0")))

        nav_object_id = str(nav.get("objectId") or block.get("objectId") or "").strip()
        if nav_object_id:
            form["CURRENT_OBJECT"] = nav_object_id

        nav_name = str(nav.get("name", "")).strip()
        if nav_name:
            form.setdefault(nav_name, "")
            self._append_namefield(form, nav_name)

        response = self._send_form(request, form)
        self._update_state_from_response(response)
        self.replay_trace.append(self._action_diagnostics("rating_detail_grid", tx_name, response))
        return response

    def _rating_business_values(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """Return the small assertion-oriented summary from Rating Detail rows."""
        coverage_premiums: dict[str, float] = {}
        policy_term_rows = []
        base_rate_rows = []

        for row in rows:
            factor = row.get("Factor")
            coverage = str(row.get("Coverage", "")).strip()
            if factor == "Base Rate":
                base_rate_rows.append(
                    {
                        "coverage": coverage,
                        "value": self._maybe_float(row.get("F.Value")),
                    }
                )
            if factor == "Policy Term Factor":
                out = self._maybe_float(row.get("Out"))
                policy_term_rows.append({"coverage": coverage, "out": out})
                if out is not None:
                    coverage_premiums[coverage] = out

        calculated_total = (
            round(sum(coverage_premiums.values()), 2)
            if coverage_premiums
            else None
        )
        return {
            "base_rates": base_rate_rows,
            "policy_term_factors": policy_term_rows,
            "coverage_premiums": coverage_premiums,
            "calculated_total_premium": calculated_total,
        }

    def add_auto_loss_payee_row(self, test_data: dict[str, Any]) -> requests.Response:
        """Add the vehicle additional-interest row required for non-owned Autos."""
        event = self.find_gateway_event(page="auto_vehicle", tx_name="Action.128505")
        request = self._captured_request(event)
        button = self._state_block_button("Loss Payee / Additional Interest", "Add")
        tx_name = str(button.get("actionIdText", "")).strip() or "Action.189"
        current_object = str(button.get("objectId", "")).strip()
        form = self._stateful_form(request.form, test_data, event)
        form["TX_NAME"] = tx_name
        if current_object:
            form["CURRENT_OBJECT"] = current_object
            self._add_block_object_reference_fields(form, current_object)
        response = self._send_form(request, form)
        self._update_state_from_response(response)
        self.replay_trace.append(self._action_diagnostics("auto_vehicle", tx_name, response))
        return response

    def post_gateway_action(self, page: str, tx_name: str) -> requests.Response:
        """Find a GatewayServlet form post by logical page and TX_NAME, then send it."""
        event = self.find_gateway_event(page=page, tx_name=tx_name)
        return self.replay_event(event)

    def post_gateway_action_from_template(
        self,
        page: str,
        template_tx_name: str,
        tx_name: str,
        test_data: dict[str, Any] | None = None,
    ) -> requests.Response:
        """Post a live action using a same-page captured form as the template."""
        event = self.find_gateway_event(page=page, tx_name=template_tx_name)
        request = self._captured_request(event)
        form = self._stateful_form(request.form, test_data or {}, event)
        form["TX_NAME"] = tx_name
        response = self._send_form(request, form)
        self._update_state_from_response(response)
        self.replay_trace.append(self._action_diagnostics(page, tx_name, response))
        return response

    def continue_soft_uw_to_premium_summary(
        self,
        test_data: dict[str, Any],
        comment: str = "Approved by API regression sweep - risk accepted.",
    ) -> requests.Response:
        """Override editable UW rows and continue to the rated Premium Summary."""
        if not self._state_page_contains("underwriting"):
            raise RuntimeError(
                f"Soft-UW continuation requires an underwriting page, got {self._state_page_name()!r}"
            )

        response = self._post_live_action(
            ">>> accept",
            test_data,
            lambda form: self._set_soft_uw_override_fields(form, comment),
        )
        if self._state_page_contains("underwriting"):
            raise RuntimeError(
                "UW accept did not leave the referral page; one or more rules may be hard stops."
            )

        if self._state_page_contains("contact information", "contact permission"):
            self._set_contact_permission_and_continue(test_data)

        if not self._state_page_contains("premium", "summary"):
            raise RuntimeError(
                "Soft-UW continuation did not reach Premium Summary; "
                f"current page is {self._state_page_name()!r}"
            )

        if self._has_live_action("re-rate"):
            response = self._post_live_action("re-rate", test_data)

        if not self._state_page_contains("premium", "summary"):
            raise RuntimeError(
                "Soft-UW re-rate did not return to Premium Summary; "
                f"current page is {self._state_page_name()!r}"
            )
        return response

    def _set_contact_permission_and_continue(self, test_data: dict[str, Any]) -> None:
        permission = self._state_layout_cell(
            ("Contact Permission", "Contact Permissions", "Preferred Contact Method")
        )
        permission_value = "Email"
        if not permission:
            permission = self._state_layout_cell(
                ("Email", "Email Contact Permission", "Email Permission")
            )
            permission_value = "Yes"
        if permission and self._has_live_action("save changes"):
            self._post_live_action(
                "save changes",
                test_data,
                lambda form: self._set_form_cell_value(
                    form,
                    permission,
                    permission_value,
                ),
            )
        elif self._has_live_action("save"):
            self._post_live_action(
                "save",
                test_data,
                (
                    lambda form: self._set_form_cell_value(
                        form,
                        permission,
                        permission_value,
                    )
                )
                if permission
                else None,
            )

        if self._has_live_action(">>> next"):
            self._post_live_action(
                ">>> next",
                test_data,
                (
                    lambda form: self._set_form_cell_value(
                        form,
                        permission,
                        permission_value,
                    )
                )
                if permission and not self._has_live_action("save changes")
                else None,
            )
        elif self._has_live_action("next"):
            self._post_live_action(
                "next",
                test_data,
                (
                    lambda form: self._set_form_cell_value(
                        form,
                        permission,
                        permission_value,
                    )
                )
                if permission and not self._has_live_action("save changes")
                else None,
            )

    def _set_soft_uw_override_fields(self, form: dict[str, str], comment: str) -> None:
        block = self._visible_grid_block_by_label("underwriting issues")
        if not block:
            raise RuntimeError("Underwriting issues grid was not found in the live UI model.")

        grid = block.get("grid", {})
        editor_rows = grid.get("editorCells", [])
        records = grid.get("valueRecords", [])
        if not records or len(editor_rows) < len(records):
            raise RuntimeError("UW rows do not expose editable cell metadata.")

        for index in range(len(records)):
            row_editors = editor_rows[index]
            if not isinstance(row_editors, dict):
                raise RuntimeError(f"UW row {index + 1} has no editable cell map.")

            cells = [
                cell
                for cell in row_editors.values()
                if isinstance(cell, dict)
            ]
            override = self._editor_cell_by_label(cells, "Overridden?")
            comments = self._editor_cell_by_label(cells, "Underwriter's Comments")
            if (
                not override
                or override.get("readOnly") is True
                or not comments
                or comments.get("readOnly") is True
            ):
                raise RuntimeError(
                    f"UW row {index + 1} is not editable by the current user."
                )

            self._set_form_cell_value(form, override, "Yes")
            self._set_form_cell_value(form, comments, comment)

    def _editor_cell_by_label(
        self,
        cells: list[dict[str, Any]],
        label: str,
    ) -> dict[str, Any] | None:
        expected = self._ui_label_key(label)
        for cell in cells:
            candidates = [
                cell.get("label"),
                (cell.get("mouseoverMesg") or {}).get("content")
                if isinstance(cell.get("mouseoverMesg"), dict)
                else None,
            ]
            if any(
                self._ui_label_key(str(candidate or "")) == expected
                for candidate in candidates
            ):
                return cell
        return None

    def _post_live_action(
        self,
        label: str,
        test_data: dict[str, Any],
        mutate_form: Any | None = None,
    ) -> requests.Response:
        button = self._state_action_button(label)
        event = self.find_gateway_event(
            page="auto_premium_summary",
            tx_name="Action.305905",
        )
        request = self._captured_request(event)
        form = self._stateful_form(request.form, test_data, event)
        form["TX_NAME"] = str(button["actionIdText"])
        form["validateFlag"] = str(button.get("validationType", form.get("validateFlag", "0")))
        if mutate_form:
            mutate_form(form)
        response = self._send_form(request, form)
        self._update_state_from_response(response)
        self.replay_trace.append(
            self._action_diagnostics("auto_soft_uw", form["TX_NAME"], response)
        )
        return response

    def _has_live_action(self, label: str) -> bool:
        try:
            self._state_action_button(label)
            return True
        except LookupError:
            return False

    def _state_action_button(self, label: str) -> dict[str, Any]:
        expected = self._ui_label_key(label)
        for button in self.state.get("actionBarButtons", []):
            if not isinstance(button, dict) or not button.get("enabled", True):
                continue
            if self._ui_label_key(str(button.get("label", ""))) == expected:
                if button.get("actionIdText"):
                    return button
                raise LookupError(f"Current action {label!r} has no actionIdText")
        raise LookupError(f"Current page has no enabled action {label!r}")

    def replay_event(self, event: dict[str, Any], test_data: dict[str, Any] | None = None) -> requests.Response:
        """Replay one captured event using the current live OneShield state."""
        request = self._captured_request(event)
        form = self._stateful_form(request.form, test_data or {}, event)
        response = self._send_form(request, form)
        self._update_state_from_response(response, event)
        self.replay_trace.append(self._event_diagnostics(event, response))
        return response

    def run_captured_auto_flow(
        self,
        test_data: dict[str, Any],
        stop_after: str = "rate",
        allow_bind: bool = False,
        fast_mode: bool = True,
        continue_soft_uw: bool = False,
    ) -> dict[str, Any]:
        """Run the captured Personal Auto API flow with current session state.

        This is not a generic OneShield API yet. It replays the known-good
        captured Auto flow, substitutes simple test-data values, and refreshes
        stateful OneShield values after each response.

        fast_mode skips FieldProcessorServlet events in the main replay loop.
        GatewayServlet payloads already carry all field values, so the intermediate
        field-echo posts are typically redundant. Validated safe for stop_after=rate.
        """
        if stop_after == "bind" and not allow_bind:
            raise ValueError("Binding is disabled by default. Pass allow_bind=True only for deliberate bind tests.")

        self.replay_trace = []
        self.login()
        response_by_stage: dict[str, requests.Response] = {}
        ui_data_by_stage: dict[str, dict[str, Any]] = {}
        stop_events = {
            "rate": ("auto_premium_summary", "Action.1753948"),
            "rating-detail": ("auto_premium_summary", "Action.469805"),
            "request-issue": ("auto_premium_summary", "Action.305905"),
            "billing-plan": ("auto_delivery_preferences", "Action.1262048"),
            "verify-billing": ("auto_billing_plan", "Action.1504046"),
            "bind": ("auto_verify_billing", "Action.1780148"),
        }
        target = stop_events[stop_after]
        blocked_reason = ""
        loss_payee_row_added = False

        for event in self._auto_replay_events(skip_field_processor=fast_mode):
            tx_name = self._event_tx_name(event)
            if event.get("page") == "auto_new_quote" and tx_name == "Action.3":
                continue
            if (
                not loss_payee_row_added
                and self._requires_auto_loss_payee(test_data)
                and (event.get("page"), tx_name) == ("auto_vehicle", "Action.128505")
            ):
                self.add_auto_loss_payee_row(test_data)
                loss_payee_row_added = True
            response = self.replay_event(event, test_data)
            if (event.get("page"), tx_name) == ("auto_vehicle", "Action.189"):
                loss_payee_row_added = True
            event_stage = next(
                (
                    name
                    for name, marker in stop_events.items()
                    if marker == (event.get("page"), tx_name)
                ),
                "",
            )
            if not event_stage and self._state_page_contains("underwriting"):
                response_by_stage["rate"] = response
                ui_data_by_stage["rate"] = self._state_ui_data()
                if continue_soft_uw:
                    ui_data_by_stage["uw-referral"] = ui_data_by_stage["rate"]
                    try:
                        response = self.continue_soft_uw_to_premium_summary(test_data)
                    except RuntimeError as exc:
                        blocked_reason = str(exc)
                        break
                    response_by_stage["rate"] = response
                    ui_data_by_stage["rate"] = self._state_ui_data()
                    if stop_after == "rating-detail":
                        response = self.open_auto_rating_detail(test_data)
                        response_by_stage["rating-detail"] = response
                        ui_data_by_stage["rating-detail"] = self._state_ui_data()
                    break
                if stop_after == "rating-detail":
                    rd_response = self.open_auto_rating_detail(test_data)
                    response_by_stage["rating-detail"] = rd_response
                    ui_data_by_stage["rating-detail"] = self._state_ui_data()
                elif stop_after != "rate":
                    blocked_reason = self._underwriting_block_before_stage(stop_after)
                break
            if (event.get("page"), tx_name) in stop_events.values():
                stage = event_stage
                response_by_stage[stage] = response
                ui_data_by_stage[stage] = self._state_ui_data()
                blocked_reason = self._blocking_reason_after_stage(stage)
                if blocked_reason:
                    break
                if stage == "rate" and self._state_page_contains("underwriting"):
                    if continue_soft_uw:
                        ui_data_by_stage["uw-referral"] = ui_data_by_stage["rate"]
                        try:
                            response = self.continue_soft_uw_to_premium_summary(test_data)
                        except RuntimeError as exc:
                            blocked_reason = str(exc)
                            break
                        response_by_stage["rate"] = response
                        ui_data_by_stage["rate"] = self._state_ui_data()
                        if stop_after == "rating-detail":
                            response = self.open_auto_rating_detail(test_data)
                            response_by_stage["rating-detail"] = response
                            ui_data_by_stage["rating-detail"] = self._state_ui_data()
                        break
                    if stop_after not in ("rate", "rating-detail"):
                        blocked_reason = self._underwriting_block_before_stage(stop_after)
                        break
                if stage == "rate" and stop_after == "rating-detail":
                    response = self.open_auto_rating_detail(test_data)
                    response_by_stage["rating-detail"] = response
                    ui_data_by_stage["rating-detail"] = self._state_ui_data()
                    blocked_reason = self._blocking_reason_after_stage("rating-detail")
                    break
            if (event.get("page"), tx_name) == target:
                break

        result = self._build_auto_result(
            test_data,
            response_by_stage.get(stop_after),
            stop_after,
            blocked_reason,
            ui_data_by_stage,
        )
        if stop_after == "bind" and result["policy_number"]:
            result["report_path"] = self.save_api_auto_summary(result["summary"])
        return result

    def save_api_auto_summary(self, details: dict[str, Any]) -> str:
        """Append an API-created Auto policy summary row."""
        return save_summary_to_csv(
            details,
            folder_name="policy_summary",
            file_name="policy_reports_api_auto.csv",
        )

    def find_gateway_request(self, page: str, tx_name: str) -> CapturedRequest:
        """Return the captured GatewayServlet request for a page/action pair."""
        event = self.find_gateway_event(page, tx_name)
        return self._captured_request(event)

    def find_gateway_event(self, page: str, tx_name: str) -> dict[str, Any]:
        """Return the captured GatewayServlet event for a page/action pair."""
        for event in self.capture["events"]:
            if event.get("kind") != "api_call" or event.get("page") != page:
                continue
            request = event["request"]
            if not request["path"].startswith("/oneshield/GatewayServlet"):
                continue
            form = self._parse_form(request.get("post_data"))
            if form.get("TX_NAME") == tx_name:
                return event
        raise LookupError(f"No GatewayServlet request found for page={page!r}, TX_NAME={tx_name!r}")

    def summarize_key_actions(self) -> list[dict[str, Any]]:
        """Return the captured login/rate/bind request identifiers."""
        actions = [
            ("login_submit", "auto_new_quote", "Action.3"),
            ("coverage_prepare", "auto_coverages_rating", "1534748"),
            ("rate_quote", "auto_premium_summary", "Action.1753948"),
            ("request_issue", "auto_premium_summary", "Action.305905"),
            ("bind", "auto_verify_billing", "Action.1780148"),
        ]
        summary = []
        for name, page, tx_name in actions:
            request = self.find_gateway_request(page, tx_name)
            summary.append(
                {
                    "name": name,
                    "page": page,
                    "method": request.method,
                    "path": request.path,
                    "tx_name": request.form.get("TX_NAME"),
                    "workflow_context": request.form.get("WORKFLOW_CONTEXT"),
                    "current_object": request.form.get("CURRENT_OBJECT"),
                    "dragon_transaction_id": request.form.get("DRAGON_TRANSACTION_ID"),
                }
            )
        return summary

    def export_key_payloads(self) -> dict[str, dict[str, Any]]:
        """Return decoded request bodies for the key replay actions."""
        actions = [
            ("login_submit", "auto_new_quote", "Action.3"),
            ("coverage_prepare", "auto_coverages_rating", "1534748"),
            ("rate_quote", "auto_premium_summary", "Action.1753948"),
            ("request_issue", "auto_premium_summary", "Action.305905"),
            ("bind", "auto_verify_billing", "Action.1780148"),
        ]
        payloads = {}
        for name, page, tx_name in actions:
            request = self.find_gateway_request(page, tx_name)
            payloads[name] = {
                "method": request.method,
                "url": self._absolute_url(request.path),
                "path": request.path,
                "page": page,
                "tx_name": tx_name,
                "form": request.form,
            }
        return payloads

    def _login_prefetch_requests(self) -> list[CapturedRequest]:
        return [
            self._captured_request(event)
            for event in self.capture["events"]
            if event.get("kind") == "api_call"
            and event.get("page") == "login"
            and event["request"]["method"] == "GET"
            and event["request"]["path"] in {"/splash.html", "/oneshield/?oswt=EmployeePortal"}
        ]

    def _extract_page_json(self, html: str) -> dict[str, Any]:
        match = re.search(r"\bpageJSON\s*=\s*", html)
        if not match:
            raise ValueError("Could not find pageJSON assignment in EmployeePortal response")
        decoder = json.JSONDecoder()
        page_json, _ = decoder.raw_decode(html[match.end() :].lstrip())
        return page_json

    def _hvars(self, page_json: dict[str, Any]) -> dict[str, str]:
        return {
            item["name"]: str(item.get("value", ""))
            for item in page_json.get("hvars", [])
            if "name" in item
        }

    def _login_field_names(self, page_json: dict[str, Any]) -> dict[str, str]:
        labels = {
            "PARTNER NUMBER": "partner",
            "USERNAME": "username",
            "PASSWORD": "password",
        }
        found: dict[str, str] = {}

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                label = str(value.get("label", "")).upper()
                var_name = value.get("varName")
                if label in labels and var_name:
                    found[labels[label]] = str(var_name)
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(page_json.get("layout", {}))
        missing = sorted(set(labels.values()) - set(found))
        if missing:
            raise ValueError(f"Could not find login field varName(s): {', '.join(missing)}")
        return found

    def _login_field_processor_requests(self) -> list[CapturedRequest]:
        return [
            self._captured_request(event)
            for event in self.capture["events"]
            if event.get("kind") == "api_call"
            and event.get("page") == "login"
            and event["request"]["method"] == "POST"
            and event["request"]["path"].startswith("/oneshield/FieldProcessorServlet")
        ]

    def _auto_replay_events(self, skip_field_processor: bool = False) -> list[dict[str, Any]]:
        _fp_path = "/oneshield/FieldProcessorServlet"
        events = [
            event
            for event in self.capture["events"]
            if event.get("kind") == "api_call"
            and event.get("request", {}).get("method") == "POST"
            and event.get("request", {}).get("path", "").split("?")[0]
            in {"/oneshield/GatewayServlet", _fp_path}
            and event.get("page")
            in {
                "auto_new_quote",
                "auto_customer",
                "auto_quote_registration",
                "auto_quote_summary",
                "auto_driver",
                "auto_vehicle",
                "auto_coverages_rating",
                "auto_premium_summary",
                "auto_delivery_preferences",
                "auto_billing_plan",
                "auto_verify_billing",
            }
        ]
        if skip_field_processor:
            return [e for e in events if e.get("request", {}).get("path", "").split("?")[0] != _fp_path]
        return events

    def _event_tx_name(self, event: dict[str, Any]) -> str:
        return self._parse_form(event["request"].get("post_data")).get("TX_NAME", "")

    def _stateful_form(
        self,
        captured_form: dict[str, str],
        test_data: dict[str, Any],
        event: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        self._map_context_object(captured_form)
        form = {
            self._replace_dynamic_tokens(str(key)): self._replace_dynamic_tokens(str(value))
            for key, value in captured_form.items()
        }
        form = self._substitute_auto_data(form, test_data)
        if self.state:
            for key, value in self._hvars(self.state).items():
                if key in {"CURRENT_OBJECT", "namefields", "namefieldslookuplist"}:
                    form.setdefault(key, value)
                else:
                    form[key] = value
            form.update(
                {
                    "osst": str(self.state.get("browserTabId", form.get("osst", ""))),
                    "USER_SESSION_GUID": str(self.state.get("browserTabId", form.get("USER_SESSION_GUID", ""))),
                    "OBJECT_TREE": str(self.state.get("objectTree", form.get("OBJECT_TREE", ""))),
                    "WORKFLOW_CONTEXT": str(self.state.get("workflowContext", form.get("WORKFLOW_CONTEXT", ""))),
                    "CURRENT_SKIN": str(self.state.get("currentSkin", form.get("CURRENT_SKIN", "4104"))),
                }
            )
            if form.get("CURRENT_OBJECT"):
                form["CURRENT_OBJECT"] = self._replace_dynamic_tokens(form["CURRENT_OBJECT"])
            if not form.get("CURRENT_OBJECT") and form.get("WORKFLOW_CONTEXT"):
                form["CURRENT_OBJECT"] = form["WORKFLOW_CONTEXT"].split(",")[1]
            selected_node = self._selected_tree_node_for_event(event, test_data) if event else ""
            if selected_node:
                form["SELECTED_NODE"] = selected_node
            self._override_current_auto_form_fields(form, test_data)
        return form

    def _override_current_auto_form_fields(self, form: dict[str, str], test_data: dict[str, Any]) -> None:
        """Submit test-data values that OneShield exposes as live layout fields."""
        if not test_data or not self.state:
            return

        layout_fields = [
            ("Gender", ("Gender",), test_data.get("Gender")),
            ("MaritalStatus", ("Marital Status",), test_data.get("MaritalStatus")),
            ("DriverStatus", ("Driver Status",), test_data.get("DriverStatus")),
            ("EmploymentCategory", ("Employment Category",), test_data.get("EmploymentCategory")),
            ("Occupation", ("Occupation",), test_data.get("Occupation")),
            ("LicenseStatus", ("License Status",), test_data.get("LicenseStatus")),
            (
                "SR22",
                (
                    "SR-22/ Certificate of Insurance Required?",
                    "Certificate of Insurance Required?",
                    "Certificate of Insurance Required",
                ),
                test_data.get("SR22"),
            ),
            ("VehicleUse", ("Vehicle Use",), test_data.get("VehicleUse")),
            ("Ownership", ("Ownership",), test_data.get("Ownership")),
            ("PolicyCoverage", ("Policy Coverage Option",), test_data.get("PolicyCoverage")),
            # Discount fields
            ("FullTimeStudent", ("Full-Time Student?",), test_data.get("FullTimeStudent")),
            (
                "VehicleWithStudentAtSchool",
                ("Vehicle with Student at School?",),
                test_data.get("VehicleWithStudentAtSchool"),
            ),
            (
                "GoodStudent",
                ('If Yes, is current grade average "B" or better?',),
                test_data.get("GoodStudent"),
            ),
            (
                "DefensiveDriver",
                ("Has a Defensive Driver Course been completed in last 3 years ?",),
                test_data.get("DefensiveDriver"),
            ),
            ("DistanceToWork", ("Distance to Work",), test_data.get("DistanceToWork")),
        ]
        if str(test_data.get("SR22", "")).strip().lower() == "yes":
            layout_fields.append(
                (
                    "SR22FilingState",
                    ("SR-22 Filing State", "SR22 Filing State"),
                    test_data.get("SR22FilingState")
                    or test_data.get("SR-22 Filing State")
                    or test_data.get("State"),
                )
            )
        if self._requires_auto_loss_payee(test_data):
            layout_fields.extend(
                [
                    (
                        "LossPayeeType",
                        ("Interest Type",),
                        test_data.get("LossPayeeType") or test_data.get("Ownership"),
                    ),
                    (
                        "LossPayeeName",
                        (
                            "Loss Payee/Additional Interest Name",
                            "Loss Payee / Additional Interest Name",
                        ),
                        test_data.get("LossPayeeName", "Leasing Company"),
                    ),
                ]
            )

        for _data_key, labels, display_value in layout_fields:
            if display_value is None:
                continue
            cell = self._state_layout_cell(labels)
            if cell:
                self._set_form_cell_value(form, cell, str(display_value))

    def _requires_auto_loss_payee(self, test_data: dict[str, Any]) -> bool:
        ownership = str(test_data.get("Ownership", "")).strip().lower()
        return bool(ownership and ownership != "owned")

    def _add_block_object_reference_fields(self, form: dict[str, str], object_id: str) -> None:
        """Retain OneShield block object references when a one-to-many Add runs."""
        for suffix in ("32785808", "31814434"):
            var_name = f"bv_{object_id}_{suffix}"
            form[var_name] = object_id
            self._append_namefield(form, var_name)

    def _state_layout_cell(self, labels: tuple[str, ...]) -> dict[str, Any] | None:
        expected = {self._ui_label_key(label) for label in labels}

        def walk(value: Any) -> dict[str, Any] | None:
            if isinstance(value, dict):
                label = self._ui_label_key(str(value.get("label", "")))
                if label in expected and value.get("varName"):
                    return value
                for child in value.values():
                    found = walk(child)
                    if found:
                        return found
            elif isinstance(value, list):
                for child in value:
                    found = walk(child)
                    if found:
                        return found
            return None

        return walk(self.state.get("layout", {}))

    def _set_form_cell_value(self, form: dict[str, str], cell: dict[str, Any], display_value: str) -> None:
        var_name = str(cell.get("varName", "")).strip()
        if not var_name.startswith("bv_"):
            return

        submit_value = self._cell_submit_value(cell, display_value)
        form[var_name] = submit_value
        self._append_namefield(form, var_name)

        if form.get("name") == var_name:
            form["value"] = submit_value

        bv_id = str(cell.get("bvId", "")).strip()
        if bv_id and form.get("AJX_RULE_BV") == bv_id:
            form["AJX_RULE_BV_VAL"] = submit_value
        self._replace_ajax_bv_value(form, bv_id, submit_value)

    def _cell_submit_value(self, cell: dict[str, Any], display_value: str) -> str:
        desired = self._ui_label_key(display_value)
        for lookup in cell.get("lookups", []):
            if not isinstance(lookup, dict):
                continue
            if self._ui_label_key(str(lookup.get("displayValue", ""))) == desired:
                return str(lookup.get("code", display_value))
        return display_value

    def _append_namefield(self, form: dict[str, str], var_name: str) -> None:
        if "namefields" not in form:
            return
        fields = [field for field in str(form.get("namefields", "")).split(",") if field]
        if var_name not in fields:
            fields.append(var_name)
            form["namefields"] = ",".join(fields)

    def _replace_ajax_bv_value(self, form: dict[str, str], bv_id: str, value: str) -> None:
        if not bv_id or not form.get("AJX_BV_IDS") or "AJX_BV_VALS" not in form:
            return
        ids = str(form["AJX_BV_IDS"]).split("\x04")
        values = str(form["AJX_BV_VALS"]).split("\x04")
        if len(ids) != len(values):
            return
        changed = False
        for index, ajax_bv_id in enumerate(ids):
            if ajax_bv_id == bv_id:
                values[index] = value
                changed = True
        if changed:
            form["AJX_BV_VALS"] = "\x04".join(values)

    def _ui_label_key(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    def _selected_tree_node_for_event(
        self,
        event: dict[str, Any] | None,
        test_data: dict[str, Any],
    ) -> str:
        if not event or self._event_tx_name(event) != "117":
            return ""
        page = event.get("page")
        full_name = f"{test_data.get('FirstName', '')} {test_data.get('LastName', '')}".strip()
        targets = {
            "auto_driver": {"label": full_name, "order": 2012001, "parent_label": "Automobile Policy"},
            "auto_vehicle": {"label": "Vehicle_1", "order": 2021001, "parent_label": "Automobile Policy"},
            "auto_coverages_rating": {
                "label": "Coverages",
                "order": 2160000,
                "parent_label": "Automobile Policy",
            },
        }
        target = targets.get(str(page))
        if not target:
            return ""
        return self._find_tree_node_id(**target)

    def _find_tree_node_id(
        self,
        label: str,
        order: int | None = None,
        parent_label: str | None = None,
    ) -> str:
        def walk(value: Any, parents: list[str]) -> str:
            if isinstance(value, dict):
                node_label = str(value.get("label", "")).strip()
                node_order = value.get("order")
                parent_matches = parent_label is None or parent_label in parents
                order_matches = order is None or node_order == order
                if node_label == label and order_matches and parent_matches:
                    return str(value.get("nodeObjectId", ""))
                next_parents = parents + ([node_label] if node_label else [])
                for child in value.values():
                    found = walk(child, next_parents)
                    if found:
                        return found
            elif isinstance(value, list):
                for child in value:
                    found = walk(child, parents)
                    if found:
                        return found
            return ""

        return walk(self.state.get("tree", {}), [])

    def _map_context_object(self, captured_form: dict[str, str]) -> None:
        if not self.state:
            return
        self._update_id_map_from_chunks(
            str(captured_form.get("OBJECT_TREE", "")),
            str(self.state.get("objectTree", "")),
        )
        captured_context = str(captured_form.get("WORKFLOW_CONTEXT", "")).split(",")
        live_context = str(self.state.get("workflowContext", "")).split(",")
        if len(captured_context) > 1 and len(live_context) > 1:
            self.id_map[captured_context[1]] = live_context[1]

    def _substitute_auto_data(self, form: dict[str, str], test_data: dict[str, Any]) -> dict[str, str]:
        if not test_data:
            return form
        email = str(test_data.get("Email", "")).replace("{timestamp}", str(int(time.time() * 1000)))
        value_map = {
            "James": test_data.get("FirstName"),
            "Smith": test_data.get("LastName"),
            "James Smith": f"{test_data.get('FirstName', '')} {test_data.get('LastName', '')}".strip(),
            "01101": test_data.get("ZIP"),
            "Springfield": test_data.get("City"),
            "230 Old Taunton Ave": test_data.get("Address"),
            "11/10/1992": test_data.get("DOB"),
            "921-549-5577": test_data.get("PhoneNum"),
            "(921)-549-5577": test_data.get("PhoneNum"),
            "jsmith_1779192798103@auto.com": email,
        }
        for key, value in list(form.items()):
            replacement = value_map.get(value)
            if replacement is not None:
                form[key] = str(replacement)
                continue
            updated_value = value
            for old, new in value_map.items():
                if new is not None and old in updated_value:
                    updated_value = updated_value.replace(old, str(new))
            form[key] = updated_value
        return form

    def _update_state_from_response(self, response: requests.Response, captured_event: dict[str, Any] | None = None) -> None:
        page_json = self._response_page_json(response)
        if not page_json:
            return
        if captured_event:
            captured_json = self._captured_response_json(captured_event)
            self._update_id_map(captured_json, page_json)
        self.state = page_json

    def _response_page_json(self, response: requests.Response) -> dict[str, Any] | None:
        try:
            parsed = response.json()
        except ValueError:
            text = response.text
            if "pageJSON" not in text:
                return None
            parsed = self._extract_page_json(text)
        return parsed if isinstance(parsed, dict) and "workflowContext" in parsed else None

    def _captured_response_json(self, event: dict[str, Any]) -> dict[str, Any] | None:
        body = event.get("response", {}).get("body")
        if isinstance(body, dict) and "workflowContext" in body:
            return body
        if isinstance(body, dict) and "preview" in body:
            try:
                parsed, _ = json.JSONDecoder().raw_decode(body["preview"])
                return parsed if isinstance(parsed, dict) else None
            except ValueError:
                return None
        if isinstance(body, str):
            try:
                parsed = json.loads(body)
                return parsed if isinstance(parsed, dict) else None
            except ValueError:
                return None
        return None

    def _update_id_map(self, captured_json: dict[str, Any] | None, live_json: dict[str, Any]) -> None:
        if not captured_json:
            return
        self._update_id_map_from_chunks(
            "\n".join([str(captured_json.get("objectTree", "")), str(captured_json.get("workflowContext", ""))]),
            "\n".join([str(live_json.get("objectTree", "")), str(live_json.get("workflowContext", ""))]),
        )
        captured_context = str(captured_json.get("workflowContext", "")).split(",")
        live_context = str(live_json.get("workflowContext", "")).split(",")
        if len(captured_context) > 1 and len(live_context) > 1:
            self.id_map[captured_context[1]] = live_context[1]

    def _update_id_map_from_chunks(self, captured_chunk: str, live_chunk: str) -> None:
        captured_ids = self._ids_from_chunk(captured_chunk)
        live_ids = self._ids_from_chunk(live_chunk)
        if not captured_ids or not live_ids:
            return
        for old, new in zip(captured_ids, live_ids):
            self.id_map[old] = new

    def _state_ids(self, state: dict[str, Any]) -> list[str]:
        chunks = [
            str(state.get("objectTree", "")),
            str(state.get("workflowContext", "")),
        ]
        return self._ids_from_chunk("\n".join(chunks))

    def _ids_from_chunk(self, chunk: str) -> list[str]:
        ids: list[str] = []
        seen: set[str] = set()
        for value in re.findall(r"(?<!\d)\d{6,}(?!\d)", chunk):
            if value not in seen:
                ids.append(value)
                seen.add(value)
        return ids

    def _replace_ids(self, value: str) -> str:
        for old, new in sorted(self.id_map.items(), key=lambda item: len(item[0]), reverse=True):
            value = value.replace(old, new)
        return value

    def _replace_dynamic_tokens(self, value: str) -> str:
        return self._replace_field_var_names(self._replace_ids(value))

    def _replace_field_var_names(self, value: str) -> str:
        if "bv_" not in value or not self.state:
            return value
        candidates_by_suffix = self._layout_field_candidates()
        if not candidates_by_suffix:
            return value

        def replace(match: re.Match[str]) -> str:
            old_name = match.group(0)
            old_object_id = match.group(1)
            suffix = match.group(2)
            candidates = candidates_by_suffix.get(suffix, [])
            if not candidates:
                return old_name

            mapped_object_id = self.id_map.get(old_object_id)
            if mapped_object_id:
                exact = [
                    candidate for candidate in candidates if self._field_object_id(candidate) == mapped_object_id
                ]
                if exact:
                    return exact[0]

            if len(candidates) == 1:
                self.id_map[old_object_id] = self._field_object_id(candidates[0])
                return candidates[0]

            current_context = str(self.state.get("workflowContext", "")).split(",")
            if len(current_context) > 1:
                current_matches = [
                    candidate for candidate in candidates if self._field_object_id(candidate) == current_context[1]
                ]
                if current_matches:
                    return current_matches[0]

            return old_name

        return FIELD_VAR_PATTERN.sub(replace, value)

    def _layout_field_candidates(self) -> dict[str, list[str]]:
        candidates: dict[str, list[str]] = {}

        def add_var_name(value: str) -> None:
            for match in FIELD_VAR_PATTERN.finditer(value):
                var_name = match.group(0)
                suffix = match.group(2)
                bucket = candidates.setdefault(suffix, [])
                if var_name not in bucket:
                    bucket.append(var_name)

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
            elif isinstance(value, str) and "bv_" in value:
                add_var_name(value)

        walk(self.state.get("layout", {}))
        return candidates

    def _field_object_id(self, var_name: str) -> str:
        match = FIELD_VAR_PATTERN.search(var_name)
        return match.group(1) if match else ""

    def _build_auto_result(
        self,
        test_data: dict[str, Any],
        response: requests.Response | None,
        stop_after: str,
        blocked_reason: str = "",
        stage_ui_data: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        response_text = response.text if response is not None else ""
        policy_number = self._first_match(r"PA\d+-\d+", response_text)
        premium = (
            self._first_match(r"\$ ?[0-9,]+\.\d{2}", response_text)
            or getattr(self, "_captured_summary_premium", None)
            or ""
        )
        diagnostics = self._state_diagnostics()
        summary = {
            "Source": "api_auto",
            "Stop After": stop_after,
            "TC_ID": test_data.get("TC_ID"),
            "Policy Number": policy_number,
            "Status": "Bound" if policy_number else "",
            "Premium": premium,
            "Customer Name": f"{test_data.get('FirstName', '')} {test_data.get('LastName', '')}".strip(),
            "Program": test_data.get("Program"),
            "Billing Method": test_data.get("BillingMethod"),
            "Employment Category": test_data.get("EmploymentCategory"),
            "Vehicle Use": test_data.get("VehicleUse"),
            "Ownership": test_data.get("Ownership"),
            "Policy Coverage Option": test_data.get("PolicyCoverage"),
            "Vehicle Type": test_data.get("VehicleType"),
            "Vehicle Year": test_data.get("Year"),
            "Vehicle Make": test_data.get("Make"),
            "Vehicle Model": test_data.get("Model"),
            "Full-Time Student": test_data.get("FullTimeStudent"),
            "Good Student": test_data.get("GoodStudent"),
            "Defensive Driver": test_data.get("DefensiveDriver"),
            "Distance to Work": test_data.get("DistanceToWork"),
        }
        rating_factors = (
            self.get_rating_detail_factors()
            if stop_after == "rating-detail" and not blocked_reason
            else {}
        )
        return {
            "stop_after": stop_after,
            "completed": bool(policy_number) if stop_after == "bind" else not blocked_reason,
            "blocked_reason": blocked_reason,
            "policy_number": policy_number,
            "premium": premium,
            "last_page": diagnostics["page_name"],
            "workflow_context": diagnostics["workflow_context"],
            "messages": diagnostics["messages"],
            "trace": self.replay_trace,
            "summary": summary,
            "rating_factors": rating_factors,
            "soft_uw_continued": any(
                item.get("page") == "auto_soft_uw"
                and item.get("tx_name") not in {"Action.469805"}
                for item in self.replay_trace
            ),
            "ui_data": self._state_ui_data(),
            "stage_ui_data": stage_ui_data or {},
        }

    def _blocking_reason_after_stage(self, stage: str) -> str:
        if stage == "rate" and not self._state_page_contains("premium", "underwriting"):
            messages = "; ".join(self._state_messages())
            return (
                "rate did not reach Premium Summary or Underwriting Referral; "
                f"current page is {self._state_page_name()!r}. {messages}"
            ).strip()
        if stage == "rating-detail" and not self._state_page_contains("rating", "underwriting"):
            messages = "; ".join(self._state_messages())
            return (
                "rating detail did not reach a Rating page or Underwriting Referral; "
                f"current page is {self._state_page_name()!r}. {messages}"
            ).strip()
        if stage == "request-issue" and not self._state_page_contains("delivery", "underwriting"):
            messages = "; ".join(self._state_messages())
            return (
                "request issue did not reach Delivery Preferences or Underwriting Referral; "
                f"current page is {self._state_page_name()!r}. {messages}"
            ).strip()
        if stage == "billing-plan" and not self._state_page_contains("billing plan", "underwriting"):
            messages = "; ".join(self._state_messages())
            return (
                "delivery next did not reach Billing Plan or Underwriting Referral; "
                f"current page is {self._state_page_name()!r}. {messages}"
            ).strip()
        if stage == "verify-billing" and not self._state_page_contains("verify billing", "underwriting"):
            messages = "; ".join(self._state_messages())
            return (
                "billing next did not reach Verify Billing or Underwriting Referral; "
                f"current page is {self._state_page_name()!r}. {messages}"
            ).strip()
        if stage == "bind" and not self._state_page_contains("policy", "current summary"):
            messages = "; ".join(self._state_messages())
            return (
                "bind did not reach Policy Current Summary; "
                f"current page is {self._state_page_name()!r}. {messages}"
            ).strip()
        return ""

    def _underwriting_block_before_stage(self, stage: str) -> str:
        messages = "; ".join(self._state_messages())
        return (
            f"underwriting referral reached before {stage}; "
            f"current page is {self._state_page_name()!r}. {messages}"
        ).strip()

    def _state_page_contains(self, *parts: str) -> bool:
        page_name = self._state_page_name().lower()
        return any(part.lower() in page_name for part in parts)

    def _state_page_name(self) -> str:
        sub_title = self.state.get("pageSubTitle")
        if isinstance(sub_title, dict):
            return str(sub_title.get("pageName", ""))
        return str(sub_title or "")

    def _state_messages(self) -> list[str]:
        message_list = self.state.get("messageList")
        if not isinstance(message_list, dict):
            return []
        messages = []
        for message in message_list.get("messages", []):
            if isinstance(message, dict):
                content = str(message.get("content") or message.get("message") or "").strip()
                if content:
                    messages.append(content)
        return messages

    def _state_diagnostics(self) -> dict[str, Any]:
        return {
            "page_name": self._state_page_name(),
            "workflow_context": str(self.state.get("workflowContext", "")),
            "object_tree": str(self.state.get("objectTree", "")),
            "messages": self._state_messages(),
        }

    def _state_ui_data(self) -> dict[str, Any]:
        """Return assertable UI data without session-bearing pageJSON internals."""
        fields = self._visible_layout_fields()
        return {
            "page_name": self._state_page_name(),
            "fields": fields,
            "field_values": self._field_values_by_label(fields),
            "grids": self._visible_layout_grids(),
            "actions": self._visible_button_labels("actionBarButtons"),
            "tabs": self._visible_button_labels("tabBarButtons"),
            "messages": self._state_messages(),
        }

    def _visible_layout_fields(self) -> list[dict[str, Any]]:
        fields: list[dict[str, Any]] = []

        def walk(value: Any, block_label: str = "", visible: bool = True) -> None:
            if isinstance(value, dict):
                if value.get("visible") is False or value.get("visibility") is False:
                    visible = False

                next_block_label = block_label
                if "cellRows" in value and value.get("label"):
                    next_block_label = str(value["label"]).strip()

                if visible and "value" in value and value.get("label"):
                    lookup_display = self._selected_lookup_display(value)
                    raw_value = value.get("value", "")
                    fields.append(
                        {
                            "block": block_label,
                            "label": re.sub(r"<[^>]+>", "", str(value["label"])).strip(),
                            "value": raw_value,
                            "display_value": lookup_display if lookup_display else raw_value,
                            "read_only": bool(value.get("readOnly", False)),
                            "mandatory": bool(value.get("mandatory", False)),
                            "provider": str(value.get("uiProvider", "")),
                        }
                    )

                for child in value.values():
                    walk(child, next_block_label, visible)
            elif isinstance(value, list):
                for child in value:
                    walk(child, block_label, visible)

        walk(self.state.get("layout", {}))
        return fields

    def _visible_layout_grids(self) -> list[dict[str, Any]]:
        return [
            self._grid_snapshot(block)
            for block in self._visible_grid_blocks()
        ]

    def _visible_grid_blocks(self) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []

        def walk(value: Any, visible: bool = True) -> None:
            if isinstance(value, dict):
                if value.get("visible") is False or value.get("visibility") is False:
                    visible = False
                if visible and isinstance(value.get("grid"), dict):
                    blocks.append(value)
                for child in value.values():
                    walk(child, visible)
            elif isinstance(value, list):
                for child in value:
                    walk(child, visible)

        walk(self.state.get("layout", {}))
        return blocks

    def _visible_grid_by_label(self, label_contains: str) -> dict[str, Any] | None:
        block = self._visible_grid_block_by_label(label_contains)
        return self._grid_snapshot(block) if block else None

    def _visible_grid_block_by_label(self, label_contains: str) -> dict[str, Any] | None:
        expected = label_contains.lower()
        for block in self._visible_grid_blocks():
            label = str(block.get("label", "")).strip().lower()
            if expected in label:
                return block
        return None

    def _grid_snapshot(self, block: dict[str, Any]) -> dict[str, Any]:
        grid = block["grid"]
        columns = [
            self._grid_column(column)
            for column in grid.get("columns", [])
            if isinstance(column, dict)
        ]
        public_columns = [
            column for column in columns if not self._internal_grid_column(column)
        ]
        rows = self._grid_rows(grid, public_columns)
        total_rows = grid.get("totalRows")
        loaded_rows = len(rows)
        total_rows_int = self._to_int(total_rows)
        provider = block.get("provider", {})
        return {
            "label": str(block.get("label", "")).strip(),
            "provider": str(provider.get("impl", "") if isinstance(provider, dict) else provider),
            "total_rows": total_rows,
            "loaded_rows": loaded_rows,
            "complete": total_rows_int is None or loaded_rows >= total_rows_int,
            "columns": public_columns,
            "fields": [
                self._grid_field(field)
                for field in grid.get("fields", [])
            ],
            "rows": rows,
        }

    def _grid_column(self, column: dict[str, Any]) -> dict[str, Any]:
        return {
            "label": str(
                column.get("label")
                or column.get("text")
                or column.get("header")
                or column.get("headerText")
                or column.get("title")
                or ""
            ).strip(),
            "field": str(
                column.get("dataIndex")
                or column.get("field")
                or column.get("name")
                or column.get("mapping")
                or ""
            ).strip(),
            "hidden": bool(column.get("hidden", False)),
        }

    def _internal_grid_column(self, column: dict[str, Any]) -> bool:
        label = str(column.get("label", "")).replace(" ", "").replace("_", "").lower()
        return (
            bool(column.get("hidden")) and not label
        ) or label in {"id", "objectid", "rowobjectid"} or self._internal_ui_key(
            str(column.get("field", ""))
        )

    def _grid_field(self, field: Any) -> Any:
        if not isinstance(field, dict):
            return field
        return {
            key: value
            for key, value in field.items()
            if key in {"name", "mapping", "type"}
        }

    def _grid_rows(self, grid: dict[str, Any], columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
        field_labels = {
            column["field"]: column["label"] or column["field"]
            for column in columns
            if column["field"]
        }
        rows = []
        for record in grid.get("valueRecords", []):
            if not isinstance(record, dict):
                continue
            rows.append(
                {
                    label: self._sanitize_grid_value(record[field])
                    for field, label in field_labels.items()
                    if field in record
                }
            )
        return rows

    def _sanitize_grid_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: self._sanitize_grid_value(child)
                for key, child in value.items()
                if not self._internal_ui_key(str(key))
            }
        if isinstance(value, list):
            return [self._sanitize_grid_value(child) for child in value]
        return value

    def _internal_ui_key(self, key: str) -> bool:
        normalized = key.replace("_", "").lower()
        return (
            normalized == "id"
            or normalized.endswith("objectid")
            or normalized == "immutablestaticidprefix"
        )

    def _selected_lookup_display(self, cell: dict[str, Any]) -> str:
        lookups = cell.get("lookups")
        if not isinstance(lookups, list):
            return ""
        selected = [
            str(lookup.get("displayValue", "")).strip()
            for lookup in lookups
            if isinstance(lookup, dict) and lookup.get("selected")
        ]
        return ", ".join(value for value in selected if value)

    def _field_values_by_label(self, fields: list[dict[str, Any]]) -> dict[str, list[Any]]:
        values: dict[str, list[Any]] = {}
        for field in fields:
            label = field["label"]
            value = field["display_value"]
            bucket = values.setdefault(label, [])
            if value not in bucket:
                bucket.append(value)
        return values

    def _visible_button_labels(self, key: str) -> list[str]:
        buttons = self.state.get(key)
        if not isinstance(buttons, list):
            return []
        return [
            str(button["label"]).strip()
            for button in buttons
            if isinstance(button, dict) and button.get("enabled", True) and button.get("label")
        ]

    def _state_button_action(self, key: str, label: str) -> str:
        buttons = self.state.get(key)
        if not isinstance(buttons, list):
            raise LookupError(f"Current page has no {key!r} button list")

        for button in buttons:
            if not isinstance(button, dict) or not button.get("enabled", True):
                continue
            if str(button.get("label", "")).strip().lower() == label.lower():
                tx_name = str(button.get("actionIdText", "")).strip()
                if tx_name:
                    return tx_name
                raise LookupError(f"Current {label!r} button has no actionIdText")

        raise LookupError(f"Current page has no enabled {label!r} button in {key!r}")

    def _state_layout_block_button(self, label: str) -> dict[str, Any]:
        buttons = self.state.get("layoutBlockButtons")
        if not isinstance(buttons, list):
            raise LookupError("Current page has no layoutBlockButtons list")

        for button in buttons:
            if not isinstance(button, dict) or not button.get("enabled", True):
                continue
            if str(button.get("label", "")).strip().lower() == label.lower():
                return button

        raise LookupError(f"Current page has no enabled layout block button {label!r}")

    def _state_block_button(self, block_label: str, button_label: str) -> dict[str, Any]:
        expected_block_label = self._ui_label_key(block_label)
        expected_button_label = self._ui_label_key(button_label)

        def find_button(value: Any) -> dict[str, Any] | None:
            if isinstance(value, dict):
                if self._ui_label_key(str(value.get("label", ""))) == expected_block_label:
                    for button_key in ("blockLevelButtons", "blockRowLevelButtons"):
                        for button in value.get(button_key, []):
                            if not isinstance(button, dict) or not button.get("enabled", True):
                                continue
                            if self._ui_label_key(str(button.get("label", ""))) == expected_button_label:
                                return button
                for child in value.values():
                    found = find_button(child)
                    if found:
                        return found
            elif isinstance(value, list):
                for child in value:
                    found = find_button(child)
                    if found:
                        return found
            return None

        button = find_button(self.state.get("layout", {}))
        if button:
            return button
        raise LookupError(f"Current layout has no enabled {button_label!r} button in {block_label!r}")

    def _event_diagnostics(self, event: dict[str, Any], response: requests.Response) -> dict[str, Any]:
        return self._action_diagnostics(event.get("page"), self._event_tx_name(event), response)

    def _action_diagnostics(self, page: str | None, tx_name: str, response: requests.Response) -> dict[str, Any]:
        diagnostics = self._state_diagnostics()
        return {
            "page": page,
            "tx_name": tx_name,
            "status_code": response.status_code,
            "response_url": response.url,
            "page_name": diagnostics["page_name"],
            "workflow_context": diagnostics["workflow_context"],
            "messages": diagnostics["messages"],
        }

    def _first_match(self, pattern: str, text: str) -> str:
        match = re.search(pattern, text)
        return match.group(0) if match else ""

    def _to_int(self, value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _maybe_float(self, value: Any) -> float | None:
        try:
            return float(str(value).replace(",", ""))
        except (TypeError, ValueError):
            return None

    def _rows_signature(self, rows: list[dict[str, Any]]) -> str:
        return json.dumps(rows, sort_keys=True, default=str)

    def _send(self, request: CapturedRequest) -> requests.Response:
        if request.method == "GET":
            response = self.session.get(
                self._absolute_url(request.path),
                headers=self._safe_headers(request.headers),
                timeout=self.timeout,
            )
        else:
            response = self._send_form(request, dict(request.form))
        response.raise_for_status()
        return response

    def _send_form(self, request: CapturedRequest, form: dict[str, str]) -> requests.Response:
        response = self.session.post(
            self._absolute_url(request.path),
            data=form,
            headers=self._safe_headers(request.headers),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response

    def _captured_request(
        self,
        event: dict[str, Any],
        form: dict[str, str] | None = None,
    ) -> CapturedRequest:
        request = event["request"]
        return CapturedRequest(
            page=event["page"],
            method=request["method"],
            url=request["url"],
            path=request["path"],
            headers=request.get("headers", {}),
            form=form if form is not None else self._parse_form(request.get("post_data")),
        )

    def _absolute_url(self, path: str) -> str:
        return urljoin(f"{self.base_url}/", path)

    def _parse_form(self, post_data: str | None) -> dict[str, str]:
        if not post_data:
            return {}
        return dict(parse_qsl(post_data, keep_blank_values=True))

    def _safe_headers(self, headers: dict[str, str]) -> dict[str, str]:
        blocked = {"cookie", "host", "content-length"}
        return {
            name: value
            for name, value in headers.items()
            if name.lower() not in blocked and value != "***"
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay/analyze captured OneShield API traffic.")
    parser.add_argument("--capture", default=str(DEFAULT_CAPTURE), help="ApiFlowRecorder JSON artifact.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="OneShield base URL.")
    parser.add_argument("--auto-data", default=str(DEFAULT_AUTO_DATA), help="Personal Auto test data JSON.")
    parser.add_argument("--tc-id", default="TC_ID_0001", help="Test case ID from --auto-data.")
    parser.add_argument(
        "--stop-after",
        choices=["rate", "rating-detail", "request-issue", "billing-plan", "verify-billing", "bind"],
        default="rate",
        help="Last stage for --action run-auto.",
    )
    parser.add_argument(
        "--allow-live-create",
        action="store_true",
        default=False,
        help="Required for --action run-auto because it creates live OneShield quote/customer records.",
    )
    parser.add_argument(
        "--allow-bind",
        action="store_true",
        default=False,
        help="Required with --action run-auto --stop-after bind because it can bind a policy.",
    )
    parser.add_argument(
        "--action",
        choices=["summary", "export-payloads", "login", "rate", "request-issue", "bind", "run-auto"],
        default="summary",
        help="Action to execute. Defaults to printing key captured request identifiers.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_PAYLOAD_EXPORT),
        help="Output path for --action export-payloads.",
    )
    args = parser.parse_args()

    client = OneShieldApiReplay(args.capture, args.base_url)
    try:
        if args.action == "summary":
            print(json.dumps(client.summarize_key_actions(), indent=2))
        elif args.action == "export-payloads":
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(client.export_key_payloads(), indent=2), encoding="utf-8")
            print(f"wrote {output_path}")
        elif args.action == "login":
            response = client.login()
            print(f"login status={response.status_code} url={response.url}")
        elif args.action == "rate":
            raise SystemExit("Use --action run-auto --stop-after rate so live OneShield state is built first.")
        elif args.action == "request-issue":
            raise SystemExit(
                "Use --action run-auto --stop-after request-issue so live OneShield state is built first."
            )
        elif args.action == "bind":
            raise SystemExit(
                "Use --action run-auto --stop-after bind --allow-live-create --allow-bind for deliberate bind tests."
            )
        elif args.action == "run-auto":
            if not args.allow_live_create:
                raise SystemExit(
                    "--action run-auto is blocked by default because it creates live OneShield quote/customer records. "
                    "Re-run with --allow-live-create after choosing a disposable test case."
                )
            if args.stop_after == "bind" and not args.allow_bind:
                raise SystemExit(
                    "--stop-after bind is blocked by default. Re-run with --allow-bind only when binding is intended."
                )
            test_data = load_auto_test_data(args.auto_data, args.tc_id)
            result = client.run_captured_auto_flow(test_data, stop_after=args.stop_after, allow_bind=args.allow_bind)
            print(json.dumps(result, indent=2))
    finally:
        client.close()


def load_auto_test_data(path: str | Path, tc_id: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for row in data.get("testCases", []):
        if row.get("TC_ID") == tc_id:
            return row
    raise LookupError(f"No auto test data row found for TC_ID={tc_id!r} in {path}")


def load_all_auto_tc_ids(path: str | Path = DEFAULT_AUTO_DATA) -> list[str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [row["TC_ID"] for row in data.get("testCases", []) if "TC_ID" in row]


if __name__ == "__main__":
    main()
