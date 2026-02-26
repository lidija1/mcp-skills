import pytest
import requests


@pytest.fixture(scope="session")
def api_session():
    """Creates a session with predefined headers and cookies for API testing."""
    s = requests.Session()
    s.headers.update({'accept': 'application/json, text/plain, */*',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'x-kp-channel': 'desktop_react',
        'x-kp-session': 'nuo2u47vogo683lasldj7u7m07',
        'x-kp-signature': '0338aeed1aee9fcda9ab814deac649bae4aa6921', # WARNING: This can expire, you might need to update it if you get 401 Unauthorized
        'referer': 'https://www.kupujemprodajem.com/',})

    s.cookies.set('KUPUJEMPRODAJEM', 'nuo2u47vogo683lasldj7u7m07')
    # you may enter login credentials here if needed, for example:
    # login_url = "https://www.kupujemprodajem.com/api/web/v1/auth/login"
    # login_payload = {"username": "your_username", "password": "your_password"}
    # s.post(login_url, json=login_payload)
    yield s
    s.close() # Closing the session after tests are done