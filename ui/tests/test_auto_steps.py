import pytest
from pytest_bdd import scenario, given, when, then, parsers

from fixtures.ui_fixtures import excel_data
from ui.pages.new_quote_page import newQuote
from utils.excel_reader import ExcelReader

@scenario("../features/personalAuto.feature", 'Create a new personal auto policy')
def test_create_new_auto_policy():
    pass
