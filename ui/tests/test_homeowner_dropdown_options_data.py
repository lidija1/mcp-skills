import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "reports" / "homeowner_dropdown_options.json"
DATA = ROOT / "testdata" / "static" / "homeowner" / "HomeownerDropdownOptionsData.json"
OPTION_SENTINELS = {"- Select -", "-Select-"}


def test_homeowner_dropdown_options_data_covers_live_probe():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    data = json.loads(DATA.read_text(encoding="utf-8"))

    expected = []
    for section in ("quote_summary", "location_coverage"):
        for item in source[section]:
            for option in item.get("options", []):
                if option not in OPTION_SENTINELS:
                    expected.append((item["name"], option))

    actual = [
        (case["DropdownDataKey"], case["DropdownOption"])
        for case in data["testCases"]
    ]

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    missing_descriptions = [
        case["TC_ID"]
        for case in data["testCases"]
        if not case.get("Description")
    ]

    assert not missing
    assert not extra
    assert not missing_descriptions
    assert data["metadata"]["caseCount"] == len(data["testCases"])
