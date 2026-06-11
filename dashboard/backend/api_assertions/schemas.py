"""Pydantic schemas for dashboard API assertion runs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


AssertionOperator = Literal["exists", "equals", "approx", "lt", "lte", "gt", "gte", "between", "contains", "not_contains"]


class ApiAssertion(BaseModel):
    type: str
    operator: AssertionOperator = "exists"
    expected: Any = None
    tolerance: float | None = None
    min_value: float | None = None
    max_value: float | None = None
    evidence_path: str = ""
    field_name: str = ""  # for field_value assertions: the UI field label to look up


class ApiAssertionSpec(BaseModel):
    # Validated at runtime by lob_config.get_lob_config(); not a Literal so new
    # LOBs require only a LobConfig entry, not a schema change.
    lob: str = "auto"
    prompt: str
    persona_prompt: str
    stage: str = "rate"
    assertions: list[ApiAssertion] = Field(default_factory=list)


class AssertionFinding(BaseModel):
    type: str
    operator: str
    expected: Any = None
    actual: Any = None
    evidence_path: str = ""
    passed: bool
    message: str = ""


class ApiAssertionRunResult(BaseModel):
    spec: ApiAssertionSpec
    persona: dict[str, Any]
    flow_result: dict[str, Any]
    findings: list[AssertionFinding]
    passed: bool
