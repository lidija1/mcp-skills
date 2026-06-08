"""
CHATBOT TOOL REGISTRY — approved MCP tool whitelist.

ARCHITECTURE BOUNDARY: Chatbot logic ends here. All user intent is translated
into a validated tool call from this registry. The chatbot may NOT access the
automation framework, browser, database, filesystem, or credentials except
through the approved tools listed below.

Tool dispatch is in chat_router.py. This module only defines the schema and
validates parameters before any dispatch.
"""
from __future__ import annotations
from typing import Any

POLICY_LOBS = ["auto", "homeowner"]
UW_LOBS = ["auto", "homeowner"]

REGISTRY: dict[str, dict] = {
    "run_quick_policy": {
        "description": "Run a full policy flow (AI persona generation + browser automation) for a single scenario.",
        "params": {
            "lob": {"type": "str", "required": True, "allowed_values": POLICY_LOBS},
            "description": {"type": "str", "required": True, "max_len": 500},
        },
        "requires_confirmation": False,
        "creates_job": True,
    },
    "create_persona": {
        "description": "Generate an insurance customer persona (AI only, no browser). Returns the profile JSON.",
        "params": {
            "lob": {"type": "str", "required": True, "allowed_values": POLICY_LOBS},
            "description": {"type": "str", "required": True, "max_len": 500},
        },
        "requires_confirmation": False,
        "creates_job": True,
    },
    "run_batch_policies": {
        "description": "Run multiple policy flows as a batch. Maximum 10 scenarios via chat.",
        "params": {
            "scenarios": {
                "type": "list",
                "required": True,
                "max_items": 10,
                "item_schema": {
                    "lob": {"type": "str", "required": True, "allowed_values": POLICY_LOBS},
                    "description": {"type": "str", "required": True, "max_len": 500},
                },
            },
        },
        "requires_confirmation": True,
        "creates_job": True,
    },
    "run_uw_audit": {
        "description": "Run the full underwriting rules audit for a line of business.",
        "params": {
            "lob": {"type": "str", "required": True, "allowed_values": UW_LOBS},
        },
        "requires_confirmation": True,
        "creates_job": True,
    },
    "run_rule_cases": {
        "description": "Run test cases for a specific underwriting rule.",
        "params": {
            "lob": {"type": "str", "required": True, "allowed_values": UW_LOBS},
            "rule_id": {"type": "str", "required": True, "max_len": 64},
        },
        "requires_confirmation": False,
        "creates_job": True,
    },
    "run_custom_boundary": {
        "description": "Run a custom UW boundary test with a specific persona and expected outcome.",
        "params": {
            "lob": {"type": "str", "required": True, "allowed_values": UW_LOBS},
            "description": {"type": "str", "required": True, "max_len": 500},
            "expected_outcome": {
                "type": "str",
                "required": True,
                "allowed_values": ["approved", "referred", "declined"],
            },
            "expected_conditions": {
                "type": "list",
                "required": False,
                "max_items": 10,
                "item_type": "str",
            },
        },
        "requires_confirmation": False,
        "creates_job": True,
    },
    "list_uw_rules": {
        "description": "List all registered underwriting rules. Returns inline — no job created.",
        "params": {
            "lob": {
                "type": "str",
                "required": False,
                "allowed_values": [*UW_LOBS, ""],
            },
        },
        "requires_confirmation": False,
        "creates_job": False,
    },
    "run_full_audit": {
        "description": "Run the full system audit across ALL lines of business. Long-running.",
        "params": {},
        "requires_confirmation": True,
        "creates_job": True,
    },
    "create_persona_variations": {
        "description": (
            "Generate N distinct persona variations from a single base description "
            "(AI only, no browser). Use when the user asks for multiple / N different "
            "personas based on one description."
        ),
        "params": {
            "lob": {"type": "str", "required": True, "allowed_values": POLICY_LOBS},
            "base_description": {"type": "str", "required": True, "max_len": 500},
            "count": {"type": "int", "required": False, "min": 1, "max": 100, "default": 5},
        },
        "requires_confirmation": False,
        "creates_job": True,
    },
    "run_api_assertion": {
        "description": (
            "Run a plain-English Auto UW test assertion. Generates an Auto persona, "
            "runs browserless Sandbox replay, and returns compact PASS/FAIL"
            "with expected and actual values."
        ),
        "params": {
            "prompt": {"type": "str", "required": True, "max_len": 1000},
        },
        "requires_confirmation": False,
        "creates_job": True,
    },
    "run_assert_flow": {
        "description": (
            "Assert that a persona's premium or total cost matches an expected dollar value. "
            "Generates a persona, replays the Sandbox flow, and returns PASS/FAIL with"
            "actual vs expected value inline in chat. Use when the user gives a specific dollar amount."
        ),
        "params": {
            "persona_description": {"type": "str", "required": True, "max_len": 500},
            "expected_value": {"type": "float", "required": True, "min": 0},
            "assertion_type": {
                "type": "str",
                "required": False,
                "allowed_values": ["premium", "total_cost"],
                "default": "premium",
            },
            "operator": {
                "type": "str",
                "required": False,
                "allowed_values": ["approx", "equals", "eq", "gt", "greater_than", "lt", "less_than"],
                "default": "approx",
            },
            "tolerance_pct": {"type": "float", "required": False, "min": 0, "max": 50, "default": 5.0},
        },
        "requires_confirmation": False,
        "creates_job": True,
    },
}


class ToolValidationError(ValueError):
    pass


def get_tool(name: str) -> dict | None:
    return REGISTRY.get(name)


def validate_params(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """
    Validate and coerce params against the registry schema.

    Returns cleaned params dict. Raises ToolValidationError on failure.

    SECURITY: Called twice — once before returning 'confirm', once again on the
    confirmed dispatch path (defense in depth so the client cannot bypass
    validation by skipping the confirmation step).
    """
    tool = REGISTRY.get(tool_name)
    if not tool:
        raise ToolValidationError(f"Unknown tool: {tool_name!r}")

    schema = tool["params"]
    cleaned: dict[str, Any] = {}

    for param_name, spec in schema.items():
        val = params.get(param_name)
        required = spec.get("required", False)

        if val is None or val == "":
            if required:
                raise ToolValidationError(f"Missing required parameter: {param_name!r}")
            _type = spec["type"]
            cleaned[param_name] = spec.get(
                "default",
                0 if _type == "int" else 0.0 if _type == "float" else [] if _type == "list" else "",
            )
            continue

        if spec["type"] == "str":
            val = str(val).strip()
            allowed = spec.get("allowed_values")
            if allowed and val not in allowed:
                raise ToolValidationError(
                    f"Invalid value for {param_name!r}: {val!r}. Must be one of {allowed}."
                )
            max_len = spec.get("max_len")
            if max_len and len(val) > max_len:
                raise ToolValidationError(
                    f"Parameter {param_name!r} is too long (max {max_len} chars)."
                )

        elif spec["type"] == "int":
            try:
                val = int(val)
            except (TypeError, ValueError):
                raise ToolValidationError(f"Parameter {param_name!r} must be an integer.")
            min_val = spec.get("min")
            max_val = spec.get("max")
            if min_val is not None and val < min_val:
                raise ToolValidationError(f"Parameter {param_name!r} must be >= {min_val}.")
            if max_val is not None and val > max_val:
                raise ToolValidationError(f"Parameter {param_name!r} must be <= {max_val}.")

        elif spec["type"] == "float":
            try:
                val = float(val)
            except (TypeError, ValueError):
                raise ToolValidationError(f"Parameter {param_name!r} must be a number.")
            min_val = spec.get("min")
            max_val = spec.get("max")
            if min_val is not None and val < min_val:
                raise ToolValidationError(f"Parameter {param_name!r} must be >= {min_val}.")
            if max_val is not None and val > max_val:
                raise ToolValidationError(f"Parameter {param_name!r} must be <= {max_val}.")

        elif spec["type"] == "list":
            if not isinstance(val, list):
                raise ToolValidationError(f"Parameter {param_name!r} must be a list.")
            max_items = spec.get("max_items")
            if max_items and len(val) > max_items:
                raise ToolValidationError(
                    f"Parameter {param_name!r} has too many items (max {max_items} via chat)."
                )
            item_schema = spec.get("item_schema")
            item_type = spec.get("item_type")
            cleaned_items = []
            for i, item in enumerate(val):
                if item_schema:
                    if not isinstance(item, dict):
                        raise ToolValidationError(
                            f"Item {i} in {param_name!r} must be an object."
                        )
                    cleaned_item = {}
                    for k, ispec in item_schema.items():
                        iv = item.get(k, "")
                        if ispec.get("required") and not iv:
                            raise ToolValidationError(
                                f"Item {i} in {param_name!r} is missing required key {k!r}."
                            )
                        iv = str(iv).strip()
                        ia = ispec.get("allowed_values")
                        if ia and iv not in ia:
                            raise ToolValidationError(
                                f"Item {i} in {param_name!r}: {k!r} must be one of {ia}."
                            )
                        il = ispec.get("max_len")
                        if il and len(iv) > il:
                            raise ToolValidationError(
                                f"Item {i} in {param_name!r}: {k!r} is too long."
                            )
                        cleaned_item[k] = iv
                    cleaned_items.append(cleaned_item)
                elif item_type == "str":
                    cleaned_items.append(str(item).strip())
                else:
                    cleaned_items.append(item)
            val = cleaned_items

        cleaned[param_name] = val

    for key in params:
        if key not in schema:
            raise ToolValidationError(f"Unexpected parameter: {key!r}")

    return cleaned


def registry_summary_for_prompt() -> str:
    """Compact tool catalogue for the AI system prompt."""
    lines = ["Available tools (name → description → required params):"]
    for name, spec in REGISTRY.items():
        req = [k for k, v in spec["params"].items() if v.get("required")]
        note = " ⚠️ requires confirmation" if spec["requires_confirmation"] else ""
        lines.append(f"  {name}: {spec['description']}{note}")
        if req:
            lines.append(f"    required params: {', '.join(req)}")
    return "\n".join(lines)
