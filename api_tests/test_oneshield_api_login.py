"""OneShield API smoke tests."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.api


def test_oneshield_api_login(oneshield_api_client):
    response = oneshield_api_client.login()

    assert response.status_code == 200
    assert "Invalid Session Page" not in response.text
    assert "pageName" in response.text
