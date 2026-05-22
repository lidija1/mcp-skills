"""Shared fixtures for OneShield API tests."""

from __future__ import annotations

import os

import pytest

from api_tests.oneshield_api_replay import (
    DEFAULT_AUTO_DATA,
    DEFAULT_BASE_URL,
    DEFAULT_CAPTURE,
    OneShieldApiReplay,
    load_all_auto_tc_ids,
)

PREMIUM_BASELINES_PATH = (
    __import__("pathlib").Path(__file__).parent / "artifacts" / "premium_baselines.json"
)


def pytest_configure(config):
    """Auto-set xdist worker count for API tests based on the number of TC_IDs.

    Skipped when already inside a worker process, or when the user passed -n
    explicitly.  Workers are capped at the CPU count so we don't spawn more
    processes than the machine can schedule efficiently.
    """
    if hasattr(config, "workerinput"):
        return  # already inside an xdist worker — don't recurse
    try:
        current = getattr(config.option, "numprocesses", None)
        if current in (None, 0):
            tc_count = len(load_all_auto_tc_ids(DEFAULT_AUTO_DATA))
            workers = min(tc_count, os.cpu_count() or 4)
            config.option.numprocesses = workers
    except AttributeError:
        pass  # xdist not installed or option not yet registered


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
    parser.addoption(
        "--oneshield-api-allow-bind",
        action="store_true",
        default=False,
        help="Allow API pytest tests that deliberately bind a live OneShield policy.",
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
