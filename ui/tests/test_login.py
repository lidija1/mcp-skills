import pytest
from pytest_bdd import scenario, given
from playwright.sync_api import Page

from ui.pages.login_page import LoginPage


@scenario('../features/login.feature', 'Successfully login with valid credentials on OneShield')
def test_login_process(login_page):
    pass