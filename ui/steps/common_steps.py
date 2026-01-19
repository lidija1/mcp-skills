
from pytest_bdd import given, parsers
from utils.excel_reader import ExcelReader

@given('The user is logged in with valid credentials')
def shared_user_login(login_page, log):
    log.info("Executing shared login step for multiple features.")
    """
    Ovaj korak je sada dostupan i za login.feature i za personal_auto.feature.
    Koristi 'login_page' fixture koji smo već definisali.
    """
    login_page.navigate()
    login_page.click_splash_button()
    login_page.fill_credentials_from_env()
    login_page.click_login()
    log.info("Successfully logged in.")


@given(parsers.parse('the data is loaded "{excel_path}", "{sheet_name}", "{tc_id}"'), target_fixture="test_data")
def load_excel_data(excel_path, sheet_name, tc_id, log):
    log.info("Loading data from excel file.")
    all_data = ExcelReader.get_excel_data(excel_path, sheet_name)
    # Filtriramo red po TC_ID koloni
    current_row = next(
        (row for row in all_data if str(row.get("TC_ID", "")).strip() == str(tc_id).strip()),
        None
    )

    if current_row is None:
        available = [r.get("TC_ID", "") for r in all_data[:10]]
        raise AssertionError(f"TC_ID '{tc_id}' not found. First TC_ID values: {available}")
    log.info("Successfully loaded data from excel file.")
    return current_row
