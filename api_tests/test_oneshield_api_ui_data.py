"""Unit coverage for assertable OneShield API UI snapshots."""

from __future__ import annotations

import pytest

from api_tests.oneshield_api_replay import OneShieldApiReplay

pytestmark = pytest.mark.api


def test_state_ui_data_extracts_visible_fields_and_lookup_display_values():
    client = object.__new__(OneShieldApiReplay)
    client.state = {
        "pageSubTitle": {"pageName": "premium | summary"},
        "messageList": {"messages": [{"content": "Rated"}]},
        "actionBarButtons": [{"label": " >>> request issue", "enabled": True}],
        "tabBarButtons": [
            {"label": "premium", "enabled": True},
            {
                "label": "rating detail",
                "actionIdText": "Action.469805",
                "enabled": True,
            },
            {"label": "hidden", "enabled": False},
        ],
        "layout": {
            "blockRows": [
                {
                    "blocks": [
                        {
                            "label": "premium details",
                            "visibility": True,
                            "cellRows": [
                                {
                                    "cells": [
                                        {
                                            "label": "Premium",
                                            "value": "$ 2,049.45",
                                            "visible": True,
                                            "readOnly": True,
                                            "uiProvider": "Dragon.view.widget.Label",
                                        },
                                        {
                                            "label": "Billing Method",
                                            "value": "1",
                                            "visible": True,
                                            "lookups": [
                                                {
                                                    "displayValue": "Direct Billed",
                                                    "selected": True,
                                                }
                                            ],
                                        },
                                    ]
                                }
                            ],
                        },
                        {
                            "label": "hidden block",
                            "visibility": False,
                            "cellRows": [
                                {
                                    "cells": [
                                        {
                                            "label": "Base Rate",
                                            "value": "$ 1.00",
                                            "visible": True,
                                        }
                                    ]
                                }
                            ],
                        },
                        {
                            "label": "premium debug information",
                            "visibility": True,
                            "provider": {"impl": "Dragon.view.One_Many_Block"},
                            "grid": {
                                "totalRows": 1,
                                "columns": [
                                    {"label": "Object ID", "dataIndex": "object"},
                                    {"label": "Coverage", "dataIndex": "coverage"},
                                    {"label": "Factor", "dataIndex": "factor"},
                                    {"label": "F.Value", "dataIndex": "factor_value"},
                                ],
                                "fields": [
                                    {"name": "ROW-OBJECT-ID"},
                                    {"name": "object"},
                                    {"name": "coverage"},
                                    {"name": "factor"},
                                    {"name": "factor_value"},
                                ],
                                "valueRecords": [
                                    {
                                        "ROW-OBJECT-ID": "49040247",
                                        "object": "10156094057",
                                        "coverage": "Bodily Injury",
                                        "factor": "Base Rate",
                                        "factor_value": "281",
                                    }
                                ],
                            },
                        },
                    ]
                }
            ]
        },
    }

    ui_data = client._state_ui_data()

    assert ui_data["page_name"] == "premium | summary"
    assert ui_data["field_values"]["Premium"] == ["$ 2,049.45"]
    assert ui_data["field_values"]["Billing Method"] == ["Direct Billed"]
    assert "Base Rate" not in ui_data["field_values"]
    assert ui_data["fields"][0]["block"] == "premium details"
    assert ui_data["fields"][1]["value"] == "1"
    assert ui_data["actions"] == [">>> request issue"]
    assert ui_data["tabs"] == ["premium", "rating detail"]
    assert ui_data["messages"] == ["Rated"]
    assert client._state_button_action("tabBarButtons", "rating detail") == "Action.469805"
    assert ui_data["grids"][0]["columns"] == [
        {"label": "Coverage", "field": "coverage", "hidden": False},
        {"label": "Factor", "field": "factor", "hidden": False},
        {"label": "F.Value", "field": "factor_value", "hidden": False},
    ]
    assert ui_data["grids"][0]["rows"] == [
        {
            "Coverage": "Bodily Injury",
            "Factor": "Base Rate",
            "F.Value": "281",
        }
    ]


def test_auto_form_overrides_use_live_lookup_codes_for_uw_driver_fields():
    client = object.__new__(OneShieldApiReplay)
    client.state = {
        "layout": {
            "blockRows": [
                {
                    "cells": [
                        {
                            "label": "License Status*",
                            "varName": "bv_123_29461414p29408614",
                            "bvId": "29461414p29408614",
                            "lookups": [
                                {"displayValue": "Active License", "code": "1"},
                                {"displayValue": "Revoked", "code": "4"},
                            ],
                        },
                        {
                            "label": "SR-22/ Certificate of Insurance Required?",
                            "varName": "bv_123_211573",
                            "bvId": "211573",
                            "lookups": [
                                {"displayValue": "No", "code": "2"},
                                {"displayValue": "Yes", "code": "1"},
                            ],
                        },
                    ]
                }
            ]
        }
    }
    form = {
        "name": "bv_123_211573",
        "value": "2",
        "namefields": "bv_123_29461414p29408614",
        "AJX_RULE_BV": "211573",
        "AJX_RULE_BV_VAL": "2",
        "AJX_BV_IDS": "29461414p29408614\x04211573",
        "AJX_BV_VALS": "1\x042",
    }

    client._override_current_auto_form_fields(
        form,
        {"LicenseStatus": "Revoked", "SR22": "Yes"},
    )

    assert form["bv_123_29461414p29408614"] == "4"
    assert form["bv_123_211573"] == "1"
    assert form["value"] == "1"
    assert form["AJX_RULE_BV_VAL"] == "1"
    assert form["AJX_BV_VALS"] == "4\x041"
    assert form["namefields"] == "bv_123_29461414p29408614,bv_123_211573"


def test_auto_form_overrides_use_live_lookup_codes_for_loss_payee_row():
    client = object.__new__(OneShieldApiReplay)
    client.state = {
        "layout": {
            "blockRows": [
                {
                    "cells": [
                        {
                            "label": "Ownership",
                            "varName": "bv_123_28892505",
                            "lookups": [
                                {"displayValue": "Leased", "code": "1"},
                                {"displayValue": "Owned", "code": "2"},
                            ],
                        },
                        {
                            "label": "Interest Type",
                            "varName": "bv_456_28021405",
                            "lookups": [
                                {"displayValue": "Financed", "code": "1"},
                                {"displayValue": "Leased", "code": "2"},
                            ],
                        },
                        {
                            "label": "Loss Payee/Additional Interest Name",
                            "varName": "bv_456_28933905",
                        },
                    ]
                }
            ]
        }
    }
    form = {"namefields": ""}

    client._override_current_auto_form_fields(
        form,
        {
            "Ownership": "Leased",
            "LossPayeeType": "Leased",
            "LossPayeeName": "BMW Financial Services",
        },
    )

    assert form["bv_123_28892505"] == "1"
    assert form["bv_456_28021405"] == "2"
    assert form["bv_456_28933905"] == "BMW Financial Services"
    assert form["namefields"] == (
        "bv_123_28892505,bv_456_28021405,bv_456_28933905"
    )


def test_loss_payee_add_button_keeps_live_block_object_references():
    client = object.__new__(OneShieldApiReplay)
    client.state = {
        "layout": {
            "blockRows": [
                {
                    "blocks": [
                        {
                            "label": "Loss Payee / Additional Interest",
                            "blockLevelButtons": [
                                {
                                    "label": "Add",
                                    "enabled": True,
                                    "actionIdText": "Action.189",
                                    "objectId": "987654321",
                                }
                            ],
                        }
                    ]
                }
            ]
        }
    }
    form = {"namefields": "existing"}

    button = client._state_block_button("Loss Payee / Additional Interest", "Add")
    client._add_block_object_reference_fields(form, button["objectId"])

    assert button["actionIdText"] == "Action.189"
    assert form["bv_987654321_32785808"] == "987654321"
    assert form["bv_987654321_31814434"] == "987654321"
    assert form["namefields"] == (
        "existing,bv_987654321_32785808,bv_987654321_31814434"
    )


def test_collect_grid_rows_uses_list_navigation_until_total_rows_loaded(monkeypatch):
    client = object.__new__(OneShieldApiReplay)

    def grid_state(rows):
        return {
            "layoutBlockButtons": [
                {"label": "next", "enabled": True, "actionIdText": "Action.91"},
            ],
            "layout": {
                "blockRows": [
                    {
                        "blocks": [
                            {
                                "label": "premium debug information",
                                "provider": {"impl": "Dragon.view.One_Many_Block"},
                                "objectId": "34831499900",
                                "listNavNext": {
                                    "name": "bv_34831499900_1",
                                    "objectId": "34831499900",
                                },
                                "grid": {
                                    "totalRows": 3,
                                    "columns": [
                                        {"label": "Coverage", "dataIndex": "coverage"},
                                        {"label": "Factor", "dataIndex": "factor"},
                                        {"label": "F.Value", "dataIndex": "factor_value"},
                                        {"label": "Out", "dataIndex": "out"},
                                    ],
                                    "fields": [],
                                    "valueRecords": rows,
                                },
                            }
                        ]
                    }
                ]
            },
        }

    page_1_rows = [
        {
            "coverage": "Bodily Injury",
            "factor": "Base Rate",
            "factor_value": "281",
            "out": "281",
        }
    ]
    page_2_rows = [
        {
            "coverage": "Bodily Injury",
            "factor": "Policy Term Factor",
            "factor_value": "1",
            "out": "369",
        },
        {
            "coverage": "Property Damage",
            "factor": "Policy Term Factor",
            "factor_value": "1",
            "out": "215",
        },
    ]
    client.state = grid_state(page_1_rows)

    def fake_next(_block, direction):
        assert direction == "next"
        client.state = grid_state(page_2_rows)

    monkeypatch.setattr(client, "_post_grid_navigation", fake_next)

    collected = client._collect_grid_rows("premium debug information")
    business_values = client._rating_business_values(collected["rows"])

    assert collected["complete"] is True
    assert collected["loaded_pages"] == 2
    assert len(collected["rows"]) == 3
    assert business_values["base_rates"] == [
        {"coverage": "Bodily Injury", "value": 281.0}
    ]
    assert business_values["coverage_premiums"] == {
        "Bodily Injury": 369.0,
        "Property Damage": 215.0,
    }
    assert business_values["calculated_total_premium"] == 584.0
