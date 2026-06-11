from dashboard.backend.api_assertions.assertion_engine import evaluate_assertions
from dashboard.backend.api_assertions.parser import parse_plain_english_api_assertion


def test_negative_underwriting_prompt_does_not_create_positive_page_assertion():
    spec = parse_plain_english_api_assertion(
        "35-year-old clean driver should NOT trigger underwriting"
    )

    assert not any(
        assertion.type == "page_contains" and assertion.expected == "underwriting"
        for assertion in spec.assertions
    )
    assert any(
        assertion.type == "page_not_contains"
        and assertion.operator == "not_contains"
        and assertion.expected == "underwriting"
        for assertion in spec.assertions
    )
    assert any(
        assertion.type == "uw_condition_count" and assertion.expected == 0.0
        for assertion in spec.assertions
    )


def test_negative_underwriting_assertions_pass_on_premium_page_without_uw_rows():
    spec = parse_plain_english_api_assertion(
        "35-year-old clean driver should NOT trigger underwriting"
    )

    findings = evaluate_assertions(
        spec.assertions,
        persona={},
        flow_result={
            "last_page": "QUOTE | PREMIUM SUMMARY | AGENT",
            "stage_ui_data": {"rate": {"grids": []}},
            "ui_data": {"grids": []},
        },
    )

    assert findings
    assert all(finding.passed for finding in findings)


def test_negative_underwriting_assertions_fail_on_underwriting_page():
    spec = parse_plain_english_api_assertion(
        "35-year-old clean driver should NOT trigger underwriting"
    )

    findings = evaluate_assertions(
        spec.assertions,
        persona={},
        flow_result={
            "last_page": "QUOTE | UNDERWRITING REFERRAL | UNDERWRITER",
            "stage_ui_data": {
                "rate": {
                    "grids": [
                        {
                            "rows": [
                                {
                                    "Type": "Underwriting",
                                    "Description": "All drivers under 25 years of age",
                                }
                            ]
                        }
                    ]
                }
            },
            "ui_data": {"grids": []},
        },
    )

    assert findings
    assert any(not finding.passed for finding in findings)
