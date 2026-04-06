"""
Accessibility Audit Engine.

Drives a Playwright browser and runs six categories of accessibility checks:

  1. alt_text       — <img> elements missing or empty alt attributes
  2. form_labels    — <input> / <select> / <textarea> without an accessible name
  3. heading_order  — skipped heading levels and missing h1
  4. keyboard       — non-interactive elements with click handlers (no keyboard access),
                      positive tabindex values that break natural tab order,
                      and interactive elements that are explicitly hidden from AT
  5. aria           — basic ARIA hygiene (landmark coverage, empty role values,
                      aria-hidden on focusable elements)
  6. page_meta      — missing <title>, missing lang attribute on <html>

Usage (standalone):
    from mcp_tools.accessibility.engine import AccessibilityEngine
    report = engine.audit("https://example.com")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# Severity constants
# ---------------------------------------------------------------------------

CRITICAL = "critical"
WARNING  = "warning"
INFO     = "info"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AccessibilityIssue:
    check: str          # Category: alt_text | form_labels | heading_order | keyboard | aria | page_meta
    severity: str       # critical | warning | info
    description: str    # Human-readable summary
    element: str        # Abbreviated outerHTML or selector
    suggestion: str     # Remediation hint


@dataclass
class HeadingNode:
    level: int
    text: str
    element: str        # Abbreviated outerHTML


@dataclass
class AuditReport:
    url: str
    title: str
    language: str
    issues: list[AccessibilityIssue]
    headings: list[HeadingNode]
    aria_snapshot: str  # Playwright accessibility tree (text serialisation)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == INFO)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class AccessibilityEngine:
    """Run accessibility checks against a live URL using Playwright."""

    def __init__(self, headed: bool = False, timeout_ms: int = 15_000):
        self.headed = headed
        self.timeout_ms = timeout_ms

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def audit(self, url: str, checks: Optional[list[str]] = None) -> AuditReport:
        """
        Navigate to *url* and run accessibility checks.

        *checks* is an optional list of category names to run.  If omitted,
        all six categories are executed.

        Returns an :class:`AuditReport`.
        """
        all_checks = {"alt_text", "form_labels", "heading_order", "keyboard", "aria", "page_meta"}
        active = set(checks) & all_checks if checks else all_checks

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=not self.headed)
            context = browser.new_context()
            page = context.new_page()
            page.set_default_timeout(self.timeout_ms)

            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_load_state("networkidle", timeout=self.timeout_ms)

            issues: list[AccessibilityIssue] = []
            headings: list[HeadingNode] = []

            if "page_meta" in active:
                issues.extend(self._check_page_meta(page))

            if "alt_text" in active:
                issues.extend(self._check_alt_text(page))

            if "form_labels" in active:
                issues.extend(self._check_form_labels(page))

            if "heading_order" in active:
                headings, heading_issues = self._check_heading_order(page)
                issues.extend(heading_issues)

            if "keyboard" in active:
                issues.extend(self._check_keyboard(page))

            if "aria" in active:
                issues.extend(self._check_aria(page))

            title = page.title()
            language = page.evaluate("() => document.documentElement.lang || ''")
            aria_snapshot = self._get_aria_snapshot(page)

            context.close()
            browser.close()

        return AuditReport(
            url=url,
            title=title,
            language=language,
            issues=issues,
            headings=headings,
            aria_snapshot=aria_snapshot,
        )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_page_meta(self, page) -> list[AccessibilityIssue]:
        """Check <title> and lang attribute."""
        issues: list[AccessibilityIssue] = []
        data: dict[str, Any] = page.evaluate("""() => ({
            title: document.title,
            lang: document.documentElement.getAttribute('lang') || '',
            hasTitle: !!document.title,
        })""")

        if not data["hasTitle"] or not data["title"].strip():
            issues.append(AccessibilityIssue(
                check="page_meta",
                severity=CRITICAL,
                description="Page is missing a <title> element.",
                element="<head>",
                suggestion="Add a descriptive <title> that summarises page purpose.",
            ))

        if not data["lang"]:
            issues.append(AccessibilityIssue(
                check="page_meta",
                severity=CRITICAL,
                description='<html> element is missing a lang attribute.',
                element="<html>",
                suggestion='Add lang="en" (or the appropriate BCP-47 language tag) to <html>.',
            ))

        return issues

    def _check_alt_text(self, page) -> list[AccessibilityIssue]:
        """Check every <img> for alt text."""
        issues: list[AccessibilityIssue] = []
        images: list[dict] = page.evaluate("""() =>
            Array.from(document.querySelectorAll('img')).map(img => ({
                src: img.src,
                hasAlt: img.hasAttribute('alt'),
                alt: img.getAttribute('alt') || '',
                isDecorative: img.getAttribute('role') === 'presentation'
                              || img.getAttribute('aria-hidden') === 'true',
                html: img.outerHTML.substring(0, 200),
            }))
        """)

        for img in images:
            if img["isDecorative"]:
                continue
            if not img["hasAlt"]:
                issues.append(AccessibilityIssue(
                    check="alt_text",
                    severity=CRITICAL,
                    description=f'Image is missing alt attribute: {img["src"][-60:]}',
                    element=img["html"],
                    suggestion='Add alt="" for decorative images or a meaningful description for informative ones.',
                ))
            elif not img["alt"].strip():
                # alt="" is OK only if truly decorative (already filtered above)
                # Flag empty alt on images that don't carry role="presentation"
                issues.append(AccessibilityIssue(
                    check="alt_text",
                    severity=WARNING,
                    description=f'Image has empty alt text but is not marked as decorative: {img["src"][-60:]}',
                    element=img["html"],
                    suggestion='If decorative add role="presentation" or aria-hidden="true"; otherwise provide meaningful alt text.',
                ))

        return issues

    def _check_form_labels(self, page) -> list[AccessibilityIssue]:
        """Check that every visible form control has an accessible name."""
        issues: list[AccessibilityIssue] = []
        controls: list[dict] = page.evaluate("""() =>
            Array.from(document.querySelectorAll('input, select, textarea')).map(el => {
                const type = (el.getAttribute('type') || 'text').toLowerCase();
                const id = el.id || '';
                const hasLabelFor = id
                    ? !!document.querySelector('label[for="' + id + '"]')
                    : false;
                const hasWrappingLabel = !!el.closest('label');
                const hasAriaLabel = !!el.getAttribute('aria-label');
                const hasAriaLabelledBy = !!el.getAttribute('aria-labelledby');
                const hasTitle = !!el.getAttribute('title');
                const isHidden = el.offsetParent === null && el.type !== 'hidden'
                    ? false : el.type === 'hidden';
                return {
                    tag: el.tagName.toLowerCase(),
                    type: type,
                    id: id,
                    name: el.name || '',
                    hasLabelFor: hasLabelFor,
                    hasWrappingLabel: hasWrappingLabel,
                    hasAriaLabel: hasAriaLabel,
                    hasAriaLabelledBy: hasAriaLabelledBy,
                    hasTitle: hasTitle,
                    isHidden: isHidden,
                    placeholder: el.placeholder || '',
                    html: el.outerHTML.substring(0, 200),
                };
            })
        """)

        skip_types = {"hidden", "submit", "reset", "button", "image"}
        for ctrl in controls:
            if ctrl["isHidden"] or ctrl["type"] in skip_types:
                continue
            has_accessible_name = (
                ctrl["hasLabelFor"]
                or ctrl["hasWrappingLabel"]
                or ctrl["hasAriaLabel"]
                or ctrl["hasAriaLabelledBy"]
                or ctrl["hasTitle"]
            )
            if not has_accessible_name:
                severity = CRITICAL
                desc = (
                    f'Form control <{ctrl["tag"]} type="{ctrl["type"]}"> '
                    f'(name="{ctrl["name"]}") has no accessible label.'
                )
                suggestion = (
                    "Associate a <label for> pointing to the control's id, "
                    "wrap it in a <label>, or add aria-label / aria-labelledby."
                )
                if ctrl["placeholder"]:
                    severity = WARNING
                    suggestion += (
                        f' Placeholder "{ctrl["placeholder"]}" is not a substitute '
                        "for a label — it disappears as soon as the user starts typing."
                    )
                issues.append(AccessibilityIssue(
                    check="form_labels",
                    severity=severity,
                    description=desc,
                    element=ctrl["html"],
                    suggestion=suggestion,
                ))

        return issues

    def _check_heading_order(self, page) -> tuple[list[HeadingNode], list[AccessibilityIssue]]:
        """Extract heading structure and flag skipped levels / missing h1."""
        raw: list[dict] = page.evaluate("""() =>
            Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6')).map(h => ({
                level: parseInt(h.tagName[1]),
                text: h.textContent.trim().substring(0, 120),
                html: h.outerHTML.substring(0, 200),
            }))
        """)

        headings = [HeadingNode(level=h["level"], text=h["text"], element=h["html"]) for h in raw]
        issues: list[AccessibilityIssue] = []

        if not headings:
            issues.append(AccessibilityIssue(
                check="heading_order",
                severity=WARNING,
                description="No heading elements found on the page.",
                element="<body>",
                suggestion="Use <h1>–<h6> to provide a navigable document outline for screen-reader users.",
            ))
            return headings, issues

        # Check for missing h1
        if not any(h.level == 1 for h in headings):
            issues.append(AccessibilityIssue(
                check="heading_order",
                severity=CRITICAL,
                description="Page has no <h1> element.",
                element=headings[0].element,
                suggestion="Every page should have exactly one <h1> that identifies the main content.",
            ))

        # Check for more than one h1
        h1s = [h for h in headings if h.level == 1]
        if len(h1s) > 1:
            issues.append(AccessibilityIssue(
                check="heading_order",
                severity=WARNING,
                description=f"Page contains {len(h1s)} <h1> elements — typically only one is expected.",
                element=h1s[1].element,
                suggestion="Use a single <h1> for the primary page title; lower-level headings for sub-sections.",
            ))

        # Check for skipped levels
        prev_level = 0
        for h in headings:
            if prev_level > 0 and h.level > prev_level + 1:
                issues.append(AccessibilityIssue(
                    check="heading_order",
                    severity=WARNING,
                    description=(
                        f"Heading level skipped: <h{prev_level}> → <h{h.level}> "
                        f'("{h.text[:60]}")'
                    ),
                    element=h.element,
                    suggestion=f"Use <h{prev_level + 1}> here instead of <h{h.level}>.",
                ))
            prev_level = h.level

        return headings, issues

    def _check_keyboard(self, page) -> list[AccessibilityIssue]:
        """
        Check for keyboard-accessibility pitfalls:
          - Elements with onclick but no keyboard handler and no native focusability
          - Elements with tabindex > 0 (breaks natural tab order)
          - Focusable elements with aria-hidden="true"
        """
        issues: list[AccessibilityIssue] = []

        results: dict[str, list] = page.evaluate("""() => {
            const NATIVE_FOCUSABLE = new Set(['a', 'button', 'input', 'select', 'textarea', 'details', 'summary']);

            // Click handlers without keyboard access
            const clickNoKeyboard = Array.from(document.querySelectorAll('[onclick]'))
                .filter(el => {
                    const tag = el.tagName.toLowerCase();
                    if (NATIVE_FOCUSABLE.has(tag)) return false;
                    const ti = el.getAttribute('tabindex');
                    return ti === null || parseInt(ti) < 0;
                })
                .map(el => ({ html: el.outerHTML.substring(0, 200), tag: el.tagName.toLowerCase() }));

            // Positive tabindex
            const positiveTabindex = Array.from(document.querySelectorAll('[tabindex]'))
                .filter(el => parseInt(el.getAttribute('tabindex')) > 0)
                .map(el => ({
                    html: el.outerHTML.substring(0, 200),
                    tabindex: el.getAttribute('tabindex'),
                }));

            // Focusable + aria-hidden
            const hiddenFocusable = Array.from(
                document.querySelectorAll('[aria-hidden="true"] a, [aria-hidden="true"] button, [aria-hidden="true"] input')
            ).map(el => ({ html: el.outerHTML.substring(0, 200) }));

            // Links with no accessible name
            const emptyLinks = Array.from(document.querySelectorAll('a'))
                .filter(a => {
                    const text = a.textContent.trim();
                    const ariaLabel = a.getAttribute('aria-label') || '';
                    const ariaLabelledBy = a.getAttribute('aria-labelledby') || '';
                    const hasImg = a.querySelector('img[alt]');
                    return !text && !ariaLabel && !ariaLabelledBy && !hasImg;
                })
                .map(a => ({ html: a.outerHTML.substring(0, 200), href: a.href }));

            // Buttons with no accessible name
            const emptyButtons = Array.from(document.querySelectorAll('button'))
                .filter(btn => {
                    const text = btn.textContent.trim();
                    const ariaLabel = btn.getAttribute('aria-label') || '';
                    const ariaLabelledBy = btn.getAttribute('aria-labelledby') || '';
                    return !text && !ariaLabel && !ariaLabelledBy;
                })
                .map(btn => ({ html: btn.outerHTML.substring(0, 200) }));

            return { clickNoKeyboard, positiveTabindex, hiddenFocusable, emptyLinks, emptyButtons };
        }""")

        for el in results.get("clickNoKeyboard", []):
            issues.append(AccessibilityIssue(
                check="keyboard",
                severity=CRITICAL,
                description=f'<{el["tag"]}> has an onclick handler but is not keyboard-accessible.',
                element=el["html"],
                suggestion=(
                    "Use a <button> or <a> element instead, or add tabindex=\"0\" "
                    "and a matching onkeydown/onkeypress handler."
                ),
            ))

        for el in results.get("positiveTabindex", []):
            issues.append(AccessibilityIssue(
                check="keyboard",
                severity=WARNING,
                description=f'Element has tabindex="{el["tabindex"]}" which disrupts the natural tab order.',
                element=el["html"],
                suggestion='Use tabindex="0" to include the element in the natural tab order, or tabindex="-1" if it should only be programmatically focused.',
            ))

        for el in results.get("hiddenFocusable", []):
            issues.append(AccessibilityIssue(
                check="keyboard",
                severity=CRITICAL,
                description="Focusable element is inside an aria-hidden container — keyboard focus can become trapped.",
                element=el["html"],
                suggestion='Remove aria-hidden from the container or ensure focusable children are also hidden (display:none / visibility:hidden).',
            ))

        for el in results.get("emptyLinks", []):
            issues.append(AccessibilityIssue(
                check="keyboard",
                severity=CRITICAL,
                description=f'Link has no accessible name (href="{el["href"][-80:]}").',
                element=el["html"],
                suggestion="Add descriptive link text, an aria-label, or an aria-labelledby reference.",
            ))

        for el in results.get("emptyButtons", []):
            issues.append(AccessibilityIssue(
                check="keyboard",
                severity=CRITICAL,
                description="Button has no accessible name.",
                element=el["html"],
                suggestion="Add visible text content or an aria-label attribute.",
            ))

        return issues

    def _check_aria(self, page) -> list[AccessibilityIssue]:
        """Basic ARIA hygiene checks."""
        issues: list[AccessibilityIssue] = []

        results: dict[str, list] = page.evaluate("""() => {
            const LANDMARK_SELECTORS = [
                'main', 'nav', 'header', 'footer', 'aside', 'section[aria-label]',
                '[role="main"]', '[role="navigation"]', '[role="banner"]',
                '[role="contentinfo"]', '[role="complementary"]', '[role="search"]',
            ];

            // Check for at least one landmark
            const hasLandmark = LANDMARK_SELECTORS.some(sel => document.querySelector(sel));

            // role="" empty strings
            const emptyRoles = Array.from(document.querySelectorAll('[role]'))
                .filter(el => !el.getAttribute('role').trim())
                .map(el => ({ html: el.outerHTML.substring(0, 200) }));

            // aria-labelledby pointing to non-existent id
            const brokenLabelledBy = Array.from(document.querySelectorAll('[aria-labelledby]'))
                .filter(el => {
                    const ids = el.getAttribute('aria-labelledby').split(/\\s+/);
                    return ids.some(id => !document.getElementById(id));
                })
                .map(el => ({
                    html: el.outerHTML.substring(0, 200),
                    value: el.getAttribute('aria-labelledby'),
                }));

            // aria-describedby pointing to non-existent id
            const brokenDescribedBy = Array.from(document.querySelectorAll('[aria-describedby]'))
                .filter(el => {
                    const ids = el.getAttribute('aria-describedby').split(/\\s+/);
                    return ids.some(id => !document.getElementById(id));
                })
                .map(el => ({
                    html: el.outerHTML.substring(0, 200),
                    value: el.getAttribute('aria-describedby'),
                }));

            // aria-required on wrong elements (not form controls)
            const badAriaRequired = Array.from(document.querySelectorAll('[aria-required]'))
                .filter(el => {
                    const tag = el.tagName.toLowerCase();
                    return !['input','select','textarea'].includes(tag);
                })
                .map(el => ({ html: el.outerHTML.substring(0, 200) }));

            return { hasLandmark, emptyRoles, brokenLabelledBy, brokenDescribedBy, badAriaRequired };
        }""")

        if not results.get("hasLandmark"):
            issues.append(AccessibilityIssue(
                check="aria",
                severity=WARNING,
                description="No ARIA landmark regions found (<main>, <nav>, <header>, etc.).",
                element="<body>",
                suggestion=(
                    "Wrap page sections with semantic HTML5 landmarks "
                    "(<main>, <nav>, <header>, <footer>, <aside>) so screen-reader users can skip to content."
                ),
            ))

        for el in results.get("emptyRoles", []):
            issues.append(AccessibilityIssue(
                check="aria",
                severity=WARNING,
                description='Element has an empty role="" attribute.',
                element=el["html"],
                suggestion="Remove the role attribute or set it to a valid ARIA role value.",
            ))

        for el in results.get("brokenLabelledBy", []):
            issues.append(AccessibilityIssue(
                check="aria",
                severity=CRITICAL,
                description=f'aria-labelledby="{el["value"]}" references an id that does not exist in the DOM.',
                element=el["html"],
                suggestion="Ensure every id listed in aria-labelledby is present and contains the intended label text.",
            ))

        for el in results.get("brokenDescribedBy", []):
            issues.append(AccessibilityIssue(
                check="aria",
                severity=WARNING,
                description=f'aria-describedby="{el["value"]}" references an id that does not exist in the DOM.',
                element=el["html"],
                suggestion="Ensure every id listed in aria-describedby points to an existing visible element.",
            ))

        return issues

    # ------------------------------------------------------------------
    # Accessibility tree snapshot
    # ------------------------------------------------------------------

    def _get_aria_snapshot(self, page) -> str:
        """Return a serialised accessibility tree from Playwright."""
        try:
            snapshot = page.accessibility.snapshot(interesting_only=True)
            if snapshot is None:
                return "(empty accessibility tree)"
            return self._serialise_node(snapshot, indent=0)
        except Exception as exc:
            return f"(snapshot unavailable: {exc})"

    def _serialise_node(self, node: dict, indent: int) -> str:
        """Recursively serialise an accessibility node to a readable string."""
        role  = node.get("role", "")
        name  = node.get("name", "")
        value = node.get("value", "")
        level = node.get("level", "")

        parts = [role]
        if level:
            parts.append(f"[level={level}]")
        if name:
            parts.append(f'"{name}"')
        if value:
            parts.append(f"= {value!r}")

        prefix = "  " * indent
        line = prefix + " ".join(str(p) for p in parts if p)
        children = node.get("children", []) or []
        child_lines = [self._serialise_node(c, indent + 1) for c in children]
        return "\n".join([line] + child_lines)
