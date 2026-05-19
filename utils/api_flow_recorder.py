"""Network recorder for mapping OneShield UI pages to backend calls."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SENSITIVE_HEADER_NAMES = {
    "authorization",
    "cookie",
    "set-cookie",
    "proxy-authorization",
    "x-csrf-token",
    "x-xsrf-token",
}

DEFAULT_RESOURCE_TYPES = {"document", "xhr", "fetch"}
MAX_BODY_CHARS = 20000


class ApiFlowRecorder:
    """Capture Playwright network traffic and group it by business page label."""

    def __init__(
        self,
        page,
        output_path: str | Path | None = None,
        enabled: bool = False,
        include_static: bool = False,
    ):
        self.page = page
        self.output_path = Path(output_path) if output_path else None
        self.enabled = enabled
        self.include_static = include_static
        self.current_page = "bootstrap"
        self.started_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        self._events: list[dict[str, Any]] = []
        self._attached = False

    def start(self) -> None:
        if not self.enabled or self._attached:
            return
        self.page.on("response", self._capture_response)
        self._attached = True

    def mark_page(self, label: str) -> None:
        if not label:
            return
        self.current_page = label
        if self.enabled:
            self._events.append(
                {
                    "kind": "page_marker",
                    "page": label,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "url": self._safe_current_url(),
                }
            )

    def finish(self) -> Path | None:
        if not self.enabled or not self.output_path:
            return None
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        artifact = {
            "started_at": self.started_at,
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "browser_url": self._safe_current_url(),
            "events": self._events,
            "pages": self._group_calls_by_page(),
        }
        self.output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
        return self.output_path

    def _capture_response(self, response) -> None:
        request = response.request
        if not self._should_capture(request):
            return

        record = {
            "kind": "api_call",
            "page": self.current_page,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "request": {
                "method": request.method,
                "url": request.url,
                "path": self._url_path(request.url),
                "resource_type": request.resource_type,
                "headers": self._redact_headers(request.headers),
                "post_data": self._parse_body(request.post_data),
            },
            "response": {
                "status": response.status,
                "ok": response.ok,
                "headers": self._redact_headers(response.headers),
                "body": self._read_response_body(response),
            },
        }
        self._events.append(record)

    def _should_capture(self, request) -> bool:
        if self.include_static:
            return True
        if request.resource_type not in DEFAULT_RESOURCE_TYPES:
            return False
        parsed = urlparse(request.url)
        path = parsed.path.lower()
        static_extensions = (
            ".css",
            ".js",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".ico",
            ".woff",
            ".woff2",
        )
        return not path.endswith(static_extensions)

    def _read_response_body(self, response) -> Any:
        content_type = response.headers.get("content-type", "")
        if not any(part in content_type.lower() for part in ("json", "xml", "text", "html")):
            return None
        try:
            body = response.text()
        except Exception as error:
            return {"unavailable": str(error)}
        return self._parse_body(body)

    def _parse_body(self, body: str | None) -> Any:
        if body is None:
            return None
        if len(body) > MAX_BODY_CHARS:
            return {
                "truncated": True,
                "length": len(body),
                "preview": body[:MAX_BODY_CHARS],
            }
        stripped = body.strip()
        if not stripped:
            return ""
        try:
            return json.loads(stripped)
        except Exception:
            return stripped

    def _redact_headers(self, headers: dict[str, str]) -> dict[str, str]:
        redacted = {}
        for name, value in headers.items():
            if name.lower() in SENSITIVE_HEADER_NAMES:
                redacted[name] = "***"
            else:
                redacted[name] = value
        return redacted

    def _group_calls_by_page(self) -> dict[str, list[dict[str, Any]]]:
        pages: dict[str, list[dict[str, Any]]] = {}
        for event in self._events:
            if event.get("kind") != "api_call":
                continue
            page_name = event.get("page", "unknown")
            pages.setdefault(page_name, []).append(event)
        return pages

    def _safe_current_url(self) -> str:
        try:
            return self.page.url
        except Exception:
            return ""

    def _url_path(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path
        if parsed.query:
            return f"{path}?{parsed.query}"
        return path
