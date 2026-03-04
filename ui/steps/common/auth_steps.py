"""Authentication and login step definitions."""
from pytest_bdd import given


@given('The user is logged in with valid credentials')
def user_login(login_page, log):
    """
    Log in the user with credentials from environment variables.
    """
    log.info("Starting login process...")
    login_page.navigate()
    login_page.click_splash_button()
    login_page.fill_credentials_from_env()
    login_page.click_login()
    log.info("Successfully logged in.")