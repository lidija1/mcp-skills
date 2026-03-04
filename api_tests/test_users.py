import allure
import pytest
import requests
import json

BASE_URL = "https://jsonplaceholder.typicode.com"

@allure.feature("User Management")
@pytest.mark.api
def test_get_single_user():
    # Send request
    response = requests.get(f"{BASE_URL}/users/1")

    # Extract data
    data = response.json()

    # Print JSON data
    print("\n===== JSON Response =====")
    print(json.dumps(data, indent=2))
    print("========================\n")

    # Validation (Interrogating the Response)
    assert response.status_code == 200
    assert "id" in data
    assert data["id"] == 1
    assert "email" in data
    assert "name" in data


@pytest.mark.api
def test_create_user():
    payload = {
        "name": "QA Student",
        "email": "qastudent@example.com"
    }
    response = requests.post(f"{BASE_URL}/users", json=payload)

    # Print JSON data
    data = response.json()
    print("\n===== POST Response =====")
    print(json.dumps(data, indent=2))
    print("========================\n")

    assert response.status_code == 201
    assert response.json()["name"] == "QA Student"
    assert response.json()["email"] == "qastudent@example.com"