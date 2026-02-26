import json

import requests
import pytest


@pytest.mark.api
def test_practice_get():
    BASE_URL = "https://httpbin.org/spec.json"
    response = requests.get(BASE_URL)
    print(response.status_code)
    print(response.headers)
    print(response.text)


@pytest.mark.api
def test_response_time_builtin():
    """Using built-in response.elapsed attribute (EASIEST WAY)"""
    BASE_URL = "https://httpbin.org/spec.json"

    response = requests.get(BASE_URL)

    # response.elapsed - returns a timedelta object representing the time taken for the request to complete
    print(f"\n{'=' * 50}")
    print(f"⏱️  Response Time: {response.elapsed}")
    print(f"⏱️  Response Time (milliseconds): {response.elapsed.total_seconds() * 1000:.2f} ms")
    print(f"{'=' * 50}\n")

    print("")
    print(f"Status code: {response.status_code}\n")

    # Assertion - check that response time is less than 2 seconds
    assert response.elapsed.total_seconds() < 2, f"Response too slow: {response.elapsed.total_seconds()}s"


@pytest.mark.api
def test_get_everything():
    """
    httpbin.org/get returns data by your request not some random data!

    This is debugging endpoint that returns all the details about your request:
    - args: Query parameters
    - headers: HTTP headers that you sent
    - origin: Your IP address
    - url: URL that you called

    This is the best endpoint to practice with because you can see exactly what you sent and what you got back.
    """
    BASE_URL = "https://httpbin.org/get"
    response = requests.get(BASE_URL)

    print(f"\n{'='*60}")
    print(f"⏱️  Elapsed time: {response.elapsed.total_seconds() * 1000:.2f} ms")
    print(f"{'='*60}\n")

    data = response.json()

    # Print only the most important information in a readable format
    print("📊 KEY INFORMATION FROM THE RESPONSE:")
    print(f"  🌐 Your IP Address: {data.get('origin')}")
    print(f"  🔗 URL Called: {data.get('url')}")
    print(f"  📨 User-Agent: {data.get('headers', {}).get('User-Agent')}")
    print(f"  🕐 Status Code: {response.status_code}\n")

    # Ako trebam sve podatke
    print("📋 FULL JSON RESPONSE:")
    print(json.dumps(data, indent=2))


@pytest.mark.api
def test_get_real_data():
    """
    For REAL content use jsonPlaceholder

    JSONPlaceholder is fake JSON API that returns the same data every time, so you can practice with it and know exactly what to expect.
    It is great for testing because you can practice with real data structure without worrying about data changing or being unavailable.
    """
    BASE_URL = "https://jsonplaceholder.typicode.com/users/1"
    response = requests.get(BASE_URL)

    print(f"\n{'='*60}")
    print(f"⏱️  Elapsed time: {response.elapsed.total_seconds() * 1000:.2f} ms")
    print(f"{'='*60}\n")

    data = response.json()

    # Print only the most important information in a readable format
    print("👤 USER INFORMATION:")
    print(f"  ID: {data.get('id')}")
    print(f"  Name: {data.get('name')}")
    print(f"  Email: {data.get('email')}")
    print(f"  Phone: {data.get('phone')}")
    print(f"  Website: {data.get('website')}")
    print(f"  Company: {data.get('company', {}).get('name')}\n")

    print("📋 FULL JSON RESPONSE:")
    print(json.dumps(data, indent=2))

    # Validations
    assert response.status_code == 200
    assert data['id'] == 1
    assert 'name' in data
    assert 'email' in data


