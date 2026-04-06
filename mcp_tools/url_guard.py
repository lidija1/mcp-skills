"""
URL guard — blocks SSRF-prone targets and enforces a probe origin allowlist.

Two functions are exported:

  validate_url(url)
      Blocks SSRF-prone targets (private IPs, loopback, bad schemes).
      Call this in any MCP tool that opens a browser page.

  assert_probe_allowed(url)
      Extends validate_url with an origin allowlist check.
      Call this in tools that SUBMIT data to a page (form_intelligence).
      Requires PROBE_ALLOWED_ORIGINS to be set in the environment / .env,
      otherwise it fails safe and blocks all probing.

Configuration (.env):
  # Comma-separated list of allowed scheme+host origins.
  # Wildcards are NOT supported — exact origin match only.
  PROBE_ALLOWED_ORIGINS=https://yourapp.example.com,http://staging.example.com
"""

import ipaddress
import os
import re
from urllib.parse import urlparse


# Hostnames that are always blocked regardless of how they resolve.
_BLOCKED_HOSTNAMES: frozenset[str] = frozenset(
    {
        "localhost",
        "ip6-localhost",
        "ip6-loopback",
    }
)

# Private / reserved IP ranges (RFC-1918, loopback, link-local, etc.)
_BLOCKED_NETWORKS: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = (
    ipaddress.ip_network("127.0.0.0/8"),       # loopback
    ipaddress.ip_network("10.0.0.0/8"),        # RFC-1918
    ipaddress.ip_network("172.16.0.0/12"),     # RFC-1918
    ipaddress.ip_network("192.168.0.0/16"),    # RFC-1918
    ipaddress.ip_network("169.254.0.0/16"),    # link-local / cloud metadata (AWS IMDSv1, Azure)
    ipaddress.ip_network("100.64.0.0/10"),     # carrier-grade NAT
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 unique-local
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
)

_ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https"})


def validate_url(url: str) -> None:
    """
    Validate that *url* is safe to pass to a browser engine.

    Blocks:
    - Non-HTTP(S) schemes (file://, ftp://, javascript:, data:, …)
    - Localhost and loopback hostnames / IPs
    - RFC-1918 private ranges and link-local (169.254.x.x)
    - Bare IP addresses that fall into any blocked network
    - Empty or malformed URLs

    Raises:
        ValueError: with a human-readable reason if the URL is disallowed.
    """
    if not url or not url.strip():
        raise ValueError("URL must not be empty.")

    parsed = urlparse(url)

    # ── scheme check ──────────────────────────────────────────────────────────
    scheme = parsed.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"Scheme '{scheme}' is not allowed. Only http and https are permitted."
        )

    # ── host presence ─────────────────────────────────────────────────────────
    host = parsed.hostname  # lowercased, strips brackets from IPv6
    if not host:
        raise ValueError("URL must contain a valid hostname.")

    # ── blocked hostname literals ─────────────────────────────────────────────
    if host in _BLOCKED_HOSTNAMES:
        raise ValueError(
            f"Host '{host}' is not allowed (loopback/internal hostname)."
        )

    # ── IP address check ──────────────────────────────────────────────────────
    # Strip IPv6 brackets if urlparse left them in (it usually does not, but be safe)
    bare = re.sub(r"^\[|\]$", "", host)
    try:
        addr = ipaddress.ip_address(bare)
        for net in _BLOCKED_NETWORKS:
            if addr in net:
                raise ValueError(
                    f"IP address '{addr}' is in a blocked network range ({net}). "
                    "Only publicly routable addresses are permitted."
                )
    except ValueError as exc:
        # ip_address() raises ValueError for non-IP strings — re-raise only the
        # ones we set ourselves (network-blocked), ignore the "not a valid IP" case.
        if "blocked network range" in str(exc):
            raise
        # Not an IP address — hostname, proceed normally.


def _load_allowed_origins() -> frozenset[str]:
    """
    Read PROBE_ALLOWED_ORIGINS from the environment and return a frozenset of
    normalised scheme+host strings, e.g. {'https://app.example.com'}.

    Returns an empty frozenset if the variable is unset or blank, which causes
    assert_probe_allowed() to block every target (fail-safe default).
    """
    raw = os.environ.get("PROBE_ALLOWED_ORIGINS", "").strip()
    if not raw:
        return frozenset()

    origins: set[str] = set()
    for entry in raw.split(","):
        entry = entry.strip().rstrip("/")
        if not entry:
            continue
        parsed = urlparse(entry)
        scheme = parsed.scheme.lower()
        host = parsed.hostname or ""
        if scheme and host:
            # Reconstruct as scheme://host (port included when non-standard)
            port_part = f":{parsed.port}" if parsed.port else ""
            origins.add(f"{scheme}://{host}{port_part}")

    return frozenset(origins)


def assert_probe_allowed(url: str) -> None:
    """
    Verify that *url* is both SSRF-safe AND on the configured probe allowlist.

    This must be called by any tool that submits data to a remote page
    (e.g. form_intelligence probe_form / test_field).

    Resolution order:
      1. validate_url(url)         — SSRF / scheme check (raises ValueError on failure)
      2. Allowlist check           — origin must appear in PROBE_ALLOWED_ORIGINS

    If PROBE_ALLOWED_ORIGINS is not set in the environment, ALL probing is
    blocked — the safe default when the variable has never been configured.

    Raises:
        ValueError: with a human-readable reason if the URL is disallowed.
    """
    # Step 1 — SSRF guard (reuse existing check)
    validate_url(url)

    # Step 2 — allowlist check
    allowed = _load_allowed_origins()

    if not allowed:
        raise ValueError(
            "Probe target rejected: PROBE_ALLOWED_ORIGINS is not configured. "
            "Add the allowed origin(s) to your .env file before running probing tools.\n"
            "Example:  PROBE_ALLOWED_ORIGINS=https://yourapp.example.com"
        )

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    host = parsed.hostname or ""
    port_part = f":{parsed.port}" if parsed.port else ""
    request_origin = f"{scheme}://{host}{port_part}"

    if request_origin not in allowed:
        raise ValueError(
            f"Probe target '{request_origin}' is not in the allowlist. "
            f"Permitted origins: {', '.join(sorted(allowed))}. "
            "To add it, update PROBE_ALLOWED_ORIGINS in your .env file."
        )
