"""
Test payload catalog.

Each payload describes a single input value to probe a form field with.
`expect_valid=True`  means "this should pass validation (no error expected)".
`expect_valid=False` means "this should be rejected by the form".
`expect_valid=None`  means "ambiguous — depends on the specific app rules".
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Payload:
    description: str
    value: Optional[str]          # None → leave field untouched / blank
    category: str                 # empty | malformed | boundary | injection | valid
    expect_valid: Optional[bool]  # True / False / None (ambiguous)


# ---------------------------------------------------------------------------
# Per-type payload factories
# ---------------------------------------------------------------------------


def for_field(
    field_type: str,
    required: bool = False,
    min_val: Optional[str] = None,
    max_val: Optional[str] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
) -> list[Payload]:
    """Return the appropriate payload list for a given HTML input type."""

    common = _common_payloads(required)

    dispatch = {
        "email":    _email,
        "tel":      _tel,
        "date":     _date,
        "number":   lambda: _number(min_val, max_val),
        "range":    lambda: _number(min_val, max_val),
        "password": lambda: _password(min_length, max_length),
        "url":      _url,
        "textarea": lambda: _text(min_length, max_length),
        "text":     lambda: _text(min_length, max_length),
        "search":   lambda: _text(min_length, max_length),
        "select":   _select,
        "checkbox": _checkbox,
        "radio":    _checkbox,
    }

    factory = dispatch.get(field_type)
    type_specific = factory() if factory else []

    return common + type_specific


# ---------------------------------------------------------------------------
# Common (apply to every field type)
# ---------------------------------------------------------------------------

def _common_payloads(required: bool) -> list[Payload]:
    return [
        Payload("Empty / blank", "", "empty", not required),
        Payload("Whitespace only", "   ", "empty", False),
    ]


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

def _email() -> list[Payload]:
    return [
        # ── valid ──────────────────────────────────────────────────────────
        Payload("Valid simple email", "test@example.com", "valid", True),
        Payload("Valid with subdomain", "user@mail.example.co.uk", "valid", True),
        Payload("Valid with + alias", "user+tag@example.com", "valid", True),
        # ── malformed ──────────────────────────────────────────────────────
        Payload("Missing @", "notanemail", "malformed", False),
        Payload("Missing domain", "user@", "malformed", False),
        Payload("Missing TLD", "user@domain", "malformed", False),
        Payload("Double @", "user@@domain.com", "malformed", False),
        Payload("Space in local part", "user name@domain.com", "malformed", False),
        Payload("Leading dot in local", ".user@domain.com", "malformed", None),
        Payload("Trailing dot in local", "user.@domain.com", "malformed", None),
        Payload("Consecutive dots", "user..name@domain.com", "malformed", False),
        Payload("Missing local part", "@domain.com", "malformed", False),
        Payload("Unicode domain", "user@xn--nxasmq6b.com", "valid", None),
        # ── boundary ───────────────────────────────────────────────────────
        Payload("Local part exactly 64 chars", "a" * 64 + "@example.com", "boundary", True),
        Payload("Local part 65 chars (over RFC limit)", "a" * 65 + "@example.com", "boundary", False),
        Payload("Total length 254 chars (RFC max)", "a" * 242 + "@example.com", "boundary", True),
        Payload("Total length 255 chars (over RFC max)", "a" * 243 + "@example.com", "boundary", False),
        # ── injection ──────────────────────────────────────────────────────
        Payload("SQL injection attempt", "'; DROP TABLE users; --@x.com", "injection", False),
        Payload("XSS in local part", '<script>alert(1)</script>@x.com', "injection", False),
        Payload("Null byte", "user\x00@example.com", "injection", False),
        Payload("CRLF injection", "user@example.com\r\nBcc: victim@example.com", "injection", False),
    ]


# ---------------------------------------------------------------------------
# Tel / phone
# ---------------------------------------------------------------------------

def _tel() -> list[Payload]:
    return [
        Payload("Valid US format", "555-123-4567", "valid", True),
        Payload("Valid with country code", "+1-555-123-4567", "valid", True),
        Payload("Letters instead of digits", "abc-def-ghij", "malformed", False),
        Payload("Too short (4 digits)", "1234", "boundary", False),
        Payload("Too long (20 digits)", "1" * 20, "boundary", False),
        Payload("All zeros", "000-000-0000", "boundary", None),
        Payload("Dots as separator", "555.123.4567", "malformed", None),
        Payload("Parens format", "(555) 123-4567", "malformed", None),
        Payload("No separator", "5551234567", "malformed", None),
        Payload("SQL injection", "555'; DROP TABLE--", "injection", False),
    ]


# ---------------------------------------------------------------------------
# Date
# ---------------------------------------------------------------------------

def _date() -> list[Payload]:
    return [
        Payload("Valid ISO date", "2000-06-15", "valid", True),
        Payload("Leap year Feb 29", "2000-02-29", "boundary", True),
        Payload("Non-leap year Feb 29", "2001-02-29", "boundary", False),
        Payload("Month 0", "2000-00-15", "malformed", False),
        Payload("Month 13", "2000-13-01", "malformed", False),
        Payload("Day 0", "2000-06-00", "malformed", False),
        Payload("Day 32", "2000-01-32", "malformed", False),
        Payload("Feb 30", "2000-02-30", "malformed", False),
        Payload("Wrong separator (dots)", "15.06.2000", "malformed", False),
        Payload("US format MM/DD/YYYY", "06/15/2000", "malformed", None),
        Payload("Plain text", "not-a-date", "malformed", False),
        Payload("Year only", "2000", "malformed", False),
        Payload("Far future", "9999-12-31", "boundary", None),
        Payload("Far past", "0001-01-01", "boundary", None),
        Payload("Epoch", "1970-01-01", "boundary", None),
        Payload("SQL injection", "2000-01-01'; DROP TABLE--", "injection", False),
    ]


# ---------------------------------------------------------------------------
# Number / range
# ---------------------------------------------------------------------------

def _number(min_val: Optional[str], max_val: Optional[str]) -> list[Payload]:
    payloads = [
        Payload("Valid integer", "1", "valid", True),
        Payload("Zero", "0", "boundary", None),
        Payload("Negative one", "-1", "boundary", None),
        Payload("Decimal 0.5", "0.5", "boundary", None),
        Payload("Very large (999999999)", "999999999", "boundary", None),
        Payload("Letters", "abc", "malformed", False),
        Payload("Mixed alpha-numeric", "12abc", "malformed", False),
        Payload("Special chars", "!@#", "malformed", False),
        Payload("Leading zeros", "007", "malformed", None),
        Payload("Scientific notation", "1e10", "malformed", None),
        Payload("SQL injection", "1; DROP TABLE--", "injection", False),
    ]

    if min_val is not None:
        try:
            mn = float(min_val)
            payloads += [
                Payload(f"At min ({mn})", str(mn), "boundary", True),
                Payload(f"1 below min ({mn - 1})", str(mn - 1), "boundary", False),
                Payload(f"Slightly below min ({mn - 0.001})", f"{mn - 0.001:.4f}", "boundary", False),
            ]
        except (ValueError, TypeError):
            pass

    if max_val is not None:
        try:
            mx = float(max_val)
            payloads += [
                Payload(f"At max ({mx})", str(mx), "boundary", True),
                Payload(f"1 above max ({mx + 1})", str(mx + 1), "boundary", False),
                Payload(f"Slightly above max ({mx + 0.001})", f"{mx + 0.001:.4f}", "boundary", False),
            ]
        except (ValueError, TypeError):
            pass

    return payloads


# ---------------------------------------------------------------------------
# Text / textarea / search
# ---------------------------------------------------------------------------

def _text(min_length: Optional[int], max_length: Optional[int]) -> list[Payload]:
    payloads = [
        Payload("Single character", "a", "boundary", min_length is None or min_length <= 1),
        Payload("Normal word", "Hello", "valid", True),
        Payload("Special punctuation", "Hello, World!", "valid", None),
        Payload("Newline character", "line1\nline2", "malformed", None),
        Payload("Tab character", "col1\tcol2", "malformed", None),
        Payload("Unicode / emoji", "Hello 🎉", "malformed", None),
        Payload("Arabic RTL text", "مرحبا", "malformed", None),
        # ── injection ──────────────────────────────────────────────────────
        Payload("SQL injection", "'; DROP TABLE users; --", "injection", False),
        Payload("XSS basic", '<script>alert("xss")</script>', "injection", False),
        Payload("XSS img onerror", '<img src=x onerror=alert(1)>', "injection", False),
        Payload("Path traversal", "../../etc/passwd", "injection", False),
        Payload("Null byte", "normal\x00text", "injection", False),
        Payload("LDAP injection", "*)(&(objectclass=*)", "injection", False),
    ]

    if max_length is not None:
        try:
            ml = int(max_length)
            payloads += [
                Payload(f"At maxlength ({ml} chars)", "a" * ml, "boundary", True),
                Payload(f"1 over maxlength ({ml + 1} chars)", "a" * (ml + 1), "boundary", False),
                Payload(f"10× maxlength ({ml * 10} chars)", "a" * (ml * 10), "boundary", False),
            ]
        except (ValueError, TypeError):
            pass
    else:
        payloads += [
            Payload("Very long string (500 chars)", "a" * 500, "boundary", None),
            Payload("Extreme length (5000 chars)", "a" * 5000, "boundary", False),
        ]

    if min_length is not None:
        try:
            ml = int(min_length)
            if ml > 1:
                payloads += [
                    Payload(f"1 below minlength ({ml - 1} chars)", "a" * (ml - 1), "boundary", False),
                    Payload(f"At minlength ({ml} chars)", "a" * ml, "boundary", True),
                ]
        except (ValueError, TypeError):
            pass

    return payloads


# ---------------------------------------------------------------------------
# Password
# ---------------------------------------------------------------------------

def _password(min_length: Optional[int], max_length: Optional[int]) -> list[Payload]:
    payloads = [
        Payload("Common password", "password", "malformed", False),
        Payload("Common password with numbers", "password123", "malformed", False),
        Payload("All lowercase", "abcdefgh", "malformed", False),
        Payload("All uppercase", "ABCDEFGH", "malformed", False),
        Payload("All digits", "12345678", "malformed", False),
        Payload("No special char", "Password123", "malformed", None),
        Payload("Good complexity", "P@ssw0rd!", "valid", True),
        Payload("SQL injection", "' OR '1'='1' --", "injection", False),
        Payload("Unicode password", "Pässwörд123!", "malformed", None),
    ]

    if min_length is not None:
        try:
            ml = int(min_length)
            payloads += [
                Payload(f"1 below min length ({ml - 1} chars)", "A1!" + "a" * (ml - 4), "boundary", False),
                Payload(f"At min length ({ml} chars)", "A1!" + "a" * (ml - 3), "boundary", True),
            ]
        except (ValueError, TypeError):
            pass

    if max_length is not None:
        try:
            ml = int(max_length)
            payloads += [
                Payload(f"At max length ({ml} chars)", "A1!" + "a" * (ml - 3), "boundary", True),
                Payload(f"1 over max length ({ml + 1} chars)", "A1!" + "a" * (ml - 2), "boundary", False),
            ]
        except (ValueError, TypeError):
            pass

    return payloads


# ---------------------------------------------------------------------------
# URL
# ---------------------------------------------------------------------------

def _url() -> list[Payload]:
    return [
        Payload("Valid HTTPS URL", "https://example.com", "valid", True),
        Payload("Valid HTTP URL", "http://example.com", "valid", True),
        Payload("Missing protocol", "www.example.com", "malformed", False),
        Payload("FTP protocol", "ftp://example.com", "malformed", None),
        Payload("No TLD", "https://example", "malformed", None),
        Payload("IP address", "https://192.168.1.1", "valid", None),
        Payload("Localhost", "http://localhost", "malformed", None),
        Payload("JavaScript URL (XSS)", "javascript:alert(1)", "injection", False),
        Payload("Data URL (XSS)", "data:text/html,<script>alert(1)</script>", "injection", False),
        Payload("Very long URL (2100 chars)", "https://example.com/" + "a" * 2080, "boundary", False),
    ]


# ---------------------------------------------------------------------------
# Select
# ---------------------------------------------------------------------------

def _select() -> list[Payload]:
    return [
        # Probed differently (by index) in the engine — these mark intent.
        Payload("First option (index 0)", "__index:0__", "boundary", None),
        Payload("Last option (last index)", "__index:-1__", "boundary", None),
        Payload("No selection / default", "", "empty", None),
    ]


# ---------------------------------------------------------------------------
# Checkbox / radio
# ---------------------------------------------------------------------------

def _checkbox() -> list[Payload]:
    return [
        Payload("Checked", "checked", "valid", True),
        Payload("Unchecked", "", "empty", None),
    ]
