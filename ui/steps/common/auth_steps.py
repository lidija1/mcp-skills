"""Authentication and login step definitions."""
from pytest_bdd import given


@given('The user is logged in with valid credentials')
def user_login(login_page, log, api_flow_recorder):
    """
    Log in the user with credentials from environment variables.
    """
    log.info("Starting login process...")
    api_flow_recorder.mark_page("login")
    login_page.navigate()
    login_page.click_splash_button()
    login_page.fill_credentials_from_env()
    login_page.click_login()
    api_flow_recorder.mark_page("post_login_home")
    log.info("Successfully logged in.")
