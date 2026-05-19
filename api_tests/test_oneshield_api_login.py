"""OneShield API smoke tests."""

from __future__ import annotations

import os

import pytest


@pytest.mark.api
def test_oneshield_api_login(oneshield_api_client):
    missing = [name for name in ("PARTNER_NUM", "USERNAMEE", "PASSWORD") if not os.getenv(name)]
    if missing:
        pytest.skip(f"Missing OneShield login env var(s): {', '.join(missing)}")

    response = oneshield_api_client.login()

    assert response.status_code == 200
    assert "Invalid Session Page" not in response.text
    assert "pageName" in response.text
