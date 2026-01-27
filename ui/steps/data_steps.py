"""Data loading step definitions."""
from pytest_bdd import given, parsers
from utils.excel_reader import ExcelReader
from utils.json_reader import DataLoader


@given(
    parsers.parse('the data is loaded "{excel_path}", "{sheet_name}", "{tc_id}"'),
    target_fixture="test_data"
)
def load_excel_data(excel_path, sheet_name, tc_id, log):
    """
    Load test data from Excel file and filter by TC_ID.
    Returns a dictionary with test data for the specified test case.
    """
    log.info(f"Loading data for TC_ID: {tc_id} from {excel_path}")
    all_data = ExcelReader.get_excel_data(excel_path, sheet_name)
    
    # Filter row by TC_ID column
    current_row = next(
        (row for row in all_data if str(row.get("TC_ID", "")).strip() == str(tc_id).strip()),
        None
    )

    if current_row is None:
        available = [r.get("TC_ID", "") for r in all_data[:10]]
        raise AssertionError(f"TC_ID '{tc_id}' not found. First TC_ID values: {available}")
    
    log.info(f"Successfully loaded data for TC_ID: {tc_id}")
    return current_row


@given(
    parsers.parse('the data is loaded "{json_path}", "{tc_id}"'),
    target_fixture="test_data"
)
def load_json_data(json_path, tc_id, log):
    """
    Load test data from JSON file and filter by TC_ID.
    Returns a dictionary with test data for the specified test case.
    """
    log.info(f"Loading data for TC_ID: {tc_id} from {json_path}")
    
    # DataLoader returns the whole JSON
    data = DataLoader.get_data(json_path)
    
    # Based on the structure of AutoData.json, test cases are in "testCases" key
    test_cases = data.get("testCases", [])
    
    # Filter row by TC_ID
    current_row = next(
        (row for row in test_cases if str(row.get("TC_ID", "")).strip() == str(tc_id).strip()),
        None
    )

    if current_row is None:
        available = [r.get("TC_ID", "") for r in test_cases[:10]]
        raise AssertionError(f"TC_ID '{tc_id}' not found in JSON. First TC_ID values: {available}")
    
    log.info(f"Successfully loaded JSON data for TC_ID: {tc_id}")
    return current_row


