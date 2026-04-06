"""
Form Intelligence Engine.

Drives a Playwright browser through three phases:
  1. Structural analysis  — DOM introspection of all form fields
  2. Empty submission     — submit the whole form blank, capture required-field errors
  3. Per-field probing    — for each field, inject each payload and capture validation

Usage (standalone):
    from mcp_tools.form_intelligence.engine import FormIntelligenceEngine
    engine = FormIntelligenceEngine()
    report = engine.probe("https://example.com/form")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from playwright.sync_api import Page, sync_playwright

from .payloads import Payload, for_field


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FieldInfo:
    selector: str
    field_type: str          # text | email | tel | date | number | select | textarea | …
    label: str = ""
    name: str = ""
    el_id: str = ""
    required: bool = False
    min_val: Optional[str] = None
    max_val: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    placeholder: str = ""
    options: list[str] = field(default_factory=list)  # for <select>


@dataclass
class FieldResult:
    payload: Payload
    validation_messages: list[str]       # errors captured from the DOM
    native_validity: str                 # HTML5 validationMessage
    passed_client_validation: bool       # True = no error messages found
    error: Optional[str] = None          # if Playwright itself threw


@dataclass
class FieldProbeReport:
    field: FieldInfo
    results: list[FieldResult]

    @property
    def issues(self) -> list[str]:
        found = []
        for r in self.results:
            if r.error:
                continue
            if r.payload.expect_valid is True and not r.passed_client_validation:
                found.append(
                    f"OVER-VALIDATION — accepted as valid but rejected: "
                    f"[{r.payload.description}] value={r.payload.value!r} "
                    f"errors={r.validation_messages}"
                )
            elif r.payload.expect_valid is False and r.passed_client_validation:
                found.append(
                    f"MISSING VALIDATION — should be invalid but no error shown: "
                    f"[{r.payload.description}] value={r.payload.value!r}"
                )
        return found


@dataclass
class ProbeReport:
    url: str
    field_count: int
    test_count: int
    empty_submission_errors: dict[str, list[str]]  # selector → errors on blank submit
    field_reports: list[FieldProbeReport]
    all_issues: list[str]
    elapsed_seconds: float


# ---------------------------------------------------------------------------
# DOM analysis helpers (JS executed in the browser)
# ---------------------------------------------------------------------------

_ANALYZE_JS = """
() => {
    const SKIP_TYPES = new Set(['hidden', 'submit', 'button', 'reset', 'image', 'file']);

    function getLabel(el) {
        if (el.id) {
            const lbl = document.querySelector('label[for="' + el.id + '"]');
            if (lbl) return lbl.textContent.trim();
        }
        const wrap = el.closest('label');
        if (wrap) return wrap.textContent.replace(el.value || '', '').trim();
        // aria-label / aria-labelledby
        if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
        const lblId = el.getAttribute('aria-labelledby');
        if (lblId) {
            const lbl = document.getElementById(lblId);
            if (lbl) return lbl.textContent.trim();
        }
        return el.placeholder || el.name || el.id || '(unlabelled)';
    }

    function buildSelector(el) {
        if (el.id) return '#' + CSS.escape(el.id);
        if (el.name) return el.tagName.toLowerCase() + '[name="' + el.name + '"]';
        // Fall back to nth-of-type within closest form/body
        const scope = el.closest('form') || document.body;
        const siblings = [...scope.querySelectorAll(el.tagName)];
        return el.tagName.toLowerCase() + ':nth-of-type(' + (siblings.indexOf(el) + 1) + ')';
    }

    const elements = [...document.querySelectorAll(
        'input, select, textarea'
    )].filter(el => {
        if (el.tagName === 'INPUT' && SKIP_TYPES.has(el.type)) return false;
        if (el.offsetParent === null && el.type !== 'hidden') return false; // invisible
        return true;
    });

    return elements.map(el => {
        const options = el.tagName === 'SELECT'
            ? [...el.options].map(o => o.text.trim()).filter(Boolean)
            : [];

        return {
            selector:    buildSelector(el),
            field_type:  el.type || el.tagName.toLowerCase(),
            label:       getLabel(el),
            name:        el.name || '',
            el_id:       el.id || '',
            required:    el.required || el.getAttribute('aria-required') === 'true',
            min_val:     el.min || null,
            max_val:     el.max || null,
            min_length:  el.minLength > 0 ? el.minLength : null,
            max_length:  el.maxLength > 0 ? el.maxLength : null,
            pattern:     el.pattern || null,
            placeholder: el.placeholder || '',
            options:     options,
        };
    });
}
"""

_COLLECT_ERRORS_JS = """
(selector) => {
    const el = selector ? document.querySelector(selector) : null;

    const msgs = new Set();

    // 1. Native HTML5 validation message
    if (el && el.validationMessage) msgs.add(el.validationMessage);

    // 2. aria-describedby  (points to error containers)
    if (el) {
        const described = el.getAttribute('aria-describedby') || '';
        described.split(/\\s+/).filter(Boolean).forEach(id => {
            const node = document.getElementById(id);
            if (node) {
                const t = node.textContent.trim();
                if (t) msgs.add(t);
            }
        });
    }

    // 3. Nearby error elements using common class/role patterns
    const errorSelectors = [
        '[role="alert"]',
        '.error-message', '.error', '.field-error', '.validation-error',
        '.invalid-feedback', '.form-error', '.help-block.error',
        '.x-form-error-msg',    // ExtJS
        '[data-error]',
    ];

    errorSelectors.forEach(sel => {
        document.querySelectorAll(sel).forEach(node => {
            const r = node.getBoundingClientRect();
            // Only count visible nodes
            if (r.width > 0 || r.height > 0) {
                const t = node.textContent.trim();
                if (t) msgs.add(t);
            }
        });
    });

    return [...msgs];
}
"""


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class FormIntelligenceEngine:
    """
    Probes a web form using Playwright and returns a structured ProbeReport.
    """

    def __init__(self, headless: bool = True, slow_mo: int = 0, timeout_ms: int = 5000):
        self.headless = headless
        self.slow_mo = slow_mo
        self.timeout_ms = timeout_ms

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, url: str) -> list[FieldInfo]:
        """Navigate to a URL and return discovered form fields (no testing)."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless, slow_mo=self.slow_mo)
            page = browser.new_context().new_page()
            try:
                self._navigate(page, url)
                return self._discover_fields(page)
            finally:
                browser.close()

    def probe(
        self,
        url: str,
        valid_defaults: Optional[dict[str, str]] = None,
        submit_selector: Optional[str] = None,
        field_selectors: Optional[list[str]] = None,
    ) -> ProbeReport:
        """
        Full three-phase investigation.

        Args:
            url:              Target page URL.
            valid_defaults:   {selector: value} used to pre-fill OTHER fields
                              during per-field probing so only the target field
                              is invalid.
            submit_selector:  CSS selector of the submit button.  When provided,
                              the engine also submits the form to trigger
                              server-side or JS-based validation.
            field_selectors:  If set, only probe these specific fields.
        """
        t_start = time.time()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless, slow_mo=self.slow_mo)
            context = browser.new_context()
            page = context.new_page()
            page.set_default_timeout(self.timeout_ms)

            try:
                # ── Phase 1: structural analysis ──────────────────────────
                self._navigate(page, url)
                all_fields = self._discover_fields(page)

                if field_selectors:
                    sel_set = set(field_selectors)
                    fields = [f for f in all_fields if f.selector in sel_set]
                else:
                    fields = all_fields

                # ── Phase 2: empty submission ─────────────────────────────
                self._navigate(page, url)
                empty_errors = self._run_empty_submission(page, fields, submit_selector)

                # ── Phase 3: per-field probing ────────────────────────────
                field_reports: list[FieldProbeReport] = []
                for fi in fields:
                    self._navigate(page, url)
                    report = self._probe_field(page, fi, all_fields, valid_defaults, submit_selector)
                    field_reports.append(report)

                all_issues = []
                for fr in field_reports:
                    all_issues.extend(fr.issues)

                return ProbeReport(
                    url=url,
                    field_count=len(fields),
                    test_count=sum(len(fr.results) for fr in field_reports),
                    empty_submission_errors=empty_errors,
                    field_reports=field_reports,
                    all_issues=all_issues,
                    elapsed_seconds=time.time() - t_start,
                )

            finally:
                browser.close()

    def probe_single_field(
        self,
        url: str,
        field_selector: str,
        field_type: str,
        valid_defaults: Optional[dict[str, str]] = None,
    ) -> FieldProbeReport:
        """Probe one specific field without running the full form analysis."""
        fi = FieldInfo(selector=field_selector, field_type=field_type, label=field_selector)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless, slow_mo=self.slow_mo)
            page = browser.new_context().new_page()
            page.set_default_timeout(self.timeout_ms)

            try:
                self._navigate(page, url)
                all_fields = self._discover_fields(page)
                return self._probe_field(page, fi, all_fields, valid_defaults, None)
            finally:
                browser.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _navigate(self, page: Page, url: str) -> None:
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(400)

    def _discover_fields(self, page: Page) -> list[FieldInfo]:
        raw: list[dict] = page.evaluate(_ANALYZE_JS)
        fields = []
        for item in raw:
            # Convert None min_length / max_length from JS (null → None already)
            fi = FieldInfo(
                selector=item["selector"],
                field_type=item["field_type"],
                label=item["label"],
                name=item["name"],
                el_id=item["el_id"],
                required=item["required"],
                min_val=item.get("min_val"),
                max_val=item.get("max_val"),
                min_length=item.get("min_length"),
                max_length=item.get("max_length"),
                pattern=item.get("pattern"),
                placeholder=item.get("placeholder", ""),
                options=item.get("options", []),
            )
            fields.append(fi)
        return fields

    def _run_empty_submission(
        self,
        page: Page,
        fields: list[FieldInfo],
        submit_selector: Optional[str],
    ) -> dict[str, list[str]]:
        """
        Clear all fields and attempt submission.  Returns errors per selector.
        """
        for fi in fields:
            self._clear_field(page, fi)

        if submit_selector:
            try:
                page.locator(submit_selector).first.click()
                page.wait_for_timeout(600)
            except Exception:
                pass
        else:
            # Press Tab on the last field to trigger blur on everything
            try:
                page.keyboard.press("Tab")
                page.wait_for_timeout(300)
            except Exception:
                pass

        errors: dict[str, list[str]] = {}
        for fi in fields:
            msgs = page.evaluate(_COLLECT_ERRORS_JS, fi.selector)
            if msgs:
                errors[fi.selector] = msgs

        return errors

    def _probe_field(
        self,
        page: Page,
        fi: FieldInfo,
        all_fields: list[FieldInfo],
        valid_defaults: Optional[dict[str, str]],
        submit_selector: Optional[str],
    ) -> FieldProbeReport:
        payloads = for_field(
            fi.field_type,
            required=fi.required,
            min_val=fi.min_val,
            max_val=fi.max_val,
            min_length=fi.min_length,
            max_length=fi.max_length,
        )

        results: list[FieldResult] = []
        # Track whether a form submit dirtied the page (needs reload before next payload)
        page_dirty = False
        origin_url = page.url

        def _ensure_clean_page() -> None:
            nonlocal page_dirty
            if page_dirty:
                self._navigate(page, origin_url)
                # Re-apply defaults after reload
                if valid_defaults:
                    for sel, val in valid_defaults.items():
                        if sel != fi.selector:
                            try:
                                self._set_field_value(page, sel, val, "text")
                            except Exception:
                                pass
                page_dirty = False

        # Apply defaults once on the initial page load
        if valid_defaults:
            for sel, val in valid_defaults.items():
                if sel != fi.selector:
                    try:
                        self._set_field_value(page, sel, val, "text")
                    except Exception:
                        pass

        for payload in payloads:
            _ensure_clean_page()

            # Clear the target field before each payload
            self._clear_field(page, fi)
            # Dismiss any lingering error state by focusing elsewhere then back
            try:
                page.keyboard.press("Escape")
                page.wait_for_timeout(80)
            except Exception:
                pass

            error = None
            try:
                self._apply_payload(page, fi, payload)
                # Trigger blur validation
                try:
                    page.locator(fi.selector).first.press("Tab")
                except Exception:
                    pass
                page.wait_for_timeout(300)

                # Optionally click submit (only for non-valid payloads to avoid
                # successful navigation away from the page)
                if submit_selector and payload.category not in ("valid",):
                    try:
                        page.locator(submit_selector).first.click()
                        page.wait_for_timeout(500)
                        page_dirty = True
                    except Exception:
                        pass

            except Exception as exc:
                error = str(exc)

            # Collect errors
            msgs = page.evaluate(_COLLECT_ERRORS_JS, fi.selector)
            native = page.evaluate(
                "(sel) => { const el = document.querySelector(sel); return el ? el.validationMessage : ''; }",
                fi.selector,
            )

            results.append(FieldResult(
                payload=payload,
                validation_messages=msgs,
                native_validity=native or "",
                passed_client_validation=len(msgs) == 0,
                error=error,
            ))

        return FieldProbeReport(field=fi, results=results)

    def _apply_payload(self, page: Page, fi: FieldInfo, payload: Payload) -> None:
        value = payload.value

        if fi.field_type == "select":
            el = page.locator(fi.selector).first
            if value == "__index:0__" and fi.options:
                el.select_option(label=fi.options[0])
            elif value == "__index:-1__" and fi.options:
                el.select_option(label=fi.options[-1])
            elif value:
                try:
                    el.select_option(label=value)
                except Exception:
                    el.select_option(index=0)
            else:
                # deselect / pick blank option if available
                try:
                    el.select_option(value="")
                except Exception:
                    pass

        elif fi.field_type in ("checkbox", "radio"):
            el = page.locator(fi.selector).first
            if value == "checked":
                el.check()
            else:
                try:
                    el.uncheck()
                except Exception:
                    pass

        else:
            self._set_field_value(page, fi.selector, value or "", fi.field_type)

    def _set_field_value(self, page: Page, selector: str, value: str, field_type: str) -> None:
        el = page.locator(selector).first
        el.scroll_into_view_if_needed()
        el.click()
        # Clear existing content
        el.fill("")
        if value:
            # Use fill for most types; type() for fields with JS listeners
            try:
                el.fill(value)
            except Exception:
                page.keyboard.type(value)

    def _clear_field(self, page: Page, fi: FieldInfo) -> None:
        try:
            if fi.field_type == "select":
                pass  # leave at default (first option)
            elif fi.field_type in ("checkbox", "radio"):
                page.locator(fi.selector).first.uncheck()
            else:
                page.locator(fi.selector).first.fill("")
        except Exception:
            pass
