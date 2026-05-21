"""Shared fixtures for OneShield API tests."""

from __future__ import annotations

import os

import pytest

from api_tests.oneshield_api_replay import DEFAULT_BASE_URL, DEFAULT_CAPTURE, OneShieldApiReplay


def pytest_addoption(parser):
    parser.addoption(
        "--oneshield-api-capture",
        action="store",
        default=str(DEFAULT_CAPTURE),
        help="ApiFlowRecorder JSON artifact to use for OneShield API replay tests.",
    )
    parser.addoption(
        "--oneshield-base-url",
        action="store",
        default=os.getenv("ONESHIELD_BASE_URL", DEFAULT_BASE_URL),
        help="OneShield base URL for API replay tests.",
    )


_REQUIRED_CREDS = ("PARTNER_NUM", "USERNAMEE", "PASSWORD")


@pytest.fixture
def oneshield_api_client(request):
    """Create a OneShield API replay client backed by the captured UI traffic.

    Skips automatically when required credentials are absent so that CI runs
    without .env do not fail, they simply skip all API tests.
    """
    missing = [v for v in _REQUIRED_CREDS if not os.getenv(v)]
    if missing:
        pytest.skip(f"Missing OneShield env var(s): {', '.join(missing)}")

    client = OneShieldApiReplay(
        capture_path=request.config.getoption("--oneshield-api-capture"),
        base_url=request.config.getoption("--oneshield-base-url"),
    )
    yield client
    client.close()
