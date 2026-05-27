"""
CHAT API ROUTER — sole entry point for chatbot-dispatched tool calls.

ARCHITECTURE BOUNDARY: This is where chatbot logic ends. The pipeline is:

  User message
    → parse_intent()          NL → { tool, params, reply }
    → validate_params()       whitelist gate (tool_registry.py)
    → _DISPATCH[tool](jid, cleaned_params)   ← only tools in REGISTRY reach here
    → job_store.*             shared job state visible in the Jobs panel
    → FastAPI BackgroundTasks launch

The chatbot layer has NO access to:
  - The Playwright / pytest-bdd automation framework directly
  - The file system, credentials, or internal environment variables
  - Any tool NOT listed in REGISTRY (tool_registry.py)

Confirmation-required tools return status="confirm" with the tool_call spec.
The frontend shows Confirm/Cancel; a confirmed POST re-validates (defense in
depth — client cannot bypass the registry by skipping the confirm step).
"""
import json
import concurrent.futures

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

import job_store
from tool_registry import REGISTRY, ToolValidationError, validate_params
from intent_parser import parse_intent

# MCP tool imports — same imports main.py uses; chatbot only reaches them
# through the dispatch table below, never directly.
from mcp_tools.policy_flow_generator.flow_runner import run_flow
from mcp_tools.policy_flow_generator.persona_generator import generate_persona, generate_persona_variations
from mcp_tools.policy_flow_generator.result_formatter import format_batch_summary, format_result
from mcp_tools.uw_rules_validator.report_formatter import format_audit_report, format_boundary_report
from mcp_tools.uw_rules_validator.rule_registry import CASES_BY_LOB, CASES_BY_RULE, RULE_METADATA
from mcp_tools.uw_rules_validator.validator import validate_case

router = APIRouter(prefix="/api/chat", tags=["chat"])

_MAX_MESSAGE_CHARS = 1000


# ── Pydantic models ──────────────────────────────────────────────────────────

class ChatMessageReq(BaseModel):
    message: str = ""
    confirmed_tool: str | None = None
    confirmed_params: dict | None = None


class ChatMessageResp(BaseModel):
    reply: str
    status: str           # "ok" | "confirm" | "job" | "error"
    tool_call: dict | None = None   # populated when status == "confirm"
    job_id: str | None = None       # populated when status == "job"
    job_label: str | None = None


# ── Shared helpers ────────────────────────────────────────────────────────────

LOB_DISPLAY = {
    "auto": "Personal Auto",
    "cyber": "Cyber",
    "homeowner": "Homeowner",
}


def _run_flow_threaded(lob: str, persona: dict, progress_callback=None) -> dict:
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(run_flow, lob, persona, progress_callback).result()


def _make_policy_progress_callback(jid: str, lob: str):
    detail = LOB_DISPLAY.get(lob.lower(), lob.upper())

    def _update(phase: str, status_detail: str | None = None):
        job_store.update_job_status(jid, phase, status_detail or detail)

    return _update


def _empty_result(lob: str, error: str) -> dict:
    return {
        "lob": lob,
        "tc_id": "ERR",
        "persona_type": "unknown",
        "overall_status": "failed",
        "outcome": "error",
        "uw_conditions": [],
        "steps": [],
        "total_duration_s": 0,
        "premium": None,
        "error": error,
        "screenshot_path": None,
    }


def _format_persona_report(lob: str, description: str, persona_json: str) -> str:
    """Wrap generated persona JSON in the markdown shape the dashboard report parser expects."""
    try:
        persona = json.loads(persona_json)
        pretty_json = json.dumps(persona, indent=2)
    except json.JSONDecodeError:
        pretty_json = persona_json

    return (
        "## Generated Customer Profile\n\n"
        f"**Line of Business:** {lob.upper()}\n\n"
        f"**Source Description:** {description}\n\n"
        "```json\n"
        f"{pretty_json}\n"
        "```\n"
    )


# ── Tool dispatch table ───────────────────────────────────────────────────────
# ARCHITECTURE BOUNDARY: only tools listed in REGISTRY may appear here.

def _dispatch_run_quick_policy(jid: str, params: dict):
    def _run():
        try:
            job_store.update_job_status(jid, "Generating profile", LOB_DISPLAY.get(params["lob"], params["lob"].upper()))
            persona_json = generate_persona(params["lob"], params["description"])
            data = json.loads(persona_json)
            if "error" in data:
                job_store.fail_job(jid, data["error"])
                return
            result = _run_flow_threaded(params["lob"], data, _make_policy_progress_callback(jid, params["lob"]))
            persona_section = _format_persona_report(params["lob"], params["description"], persona_json) + "\n\n---\n\n"
            job_store.complete_job(jid, persona_section + format_result(result))
        except Exception as exc:
            job_store.fail_job(jid, str(exc))
    return _run


def _dispatch_create_persona(jid: str, params: dict):
    def _run():
        try:
            persona_json = generate_persona(params["lob"], params["description"])
            data = json.loads(persona_json)
            if "error" in data:
                job_store.fail_job(jid, data["error"])
                return
            job_store.complete_job(
                jid,
                _format_persona_report(params["lob"], params["description"], persona_json),
            )
        except Exception as exc:
            job_store.fail_job(jid, str(exc))
    return _run


def _dispatch_run_batch_policies(jid: str, params: dict):
    def _run():
        try:
            results = []
            for s in params["scenarios"][:10]:
                lob = s.get("lob", "auto").lower()
                pjson = generate_persona(lob, s.get("description", ""))
                try:
                    p = json.loads(pjson)
                    r = _empty_result(lob, p.get("error", "persona error")) if "error" in p else _run_flow_threaded(lob, p)
                except Exception as ex:
                    r = _empty_result(lob, str(ex))
                results.append(r)
            job_store.complete_job(jid, format_batch_summary(results))
        except Exception as exc:
            job_store.fail_job(jid, str(exc))
    return _run


def _dispatch_run_uw_audit(jid: str, params: dict):
    def _run():
        try:
            lob = params["lob"].lower()
            findings = []
            for case in CASES_BY_LOB.get(lob, []):
                result = _run_flow_threaded(lob, case["persona"])
                findings.extend(validate_case(case, result))
            job_store.complete_job(jid, format_audit_report(lob, findings))
        except Exception as exc:
            job_store.fail_job(jid, str(exc))
    return _run


def _dispatch_run_rule_cases(jid: str, params: dict):
    def _run():
        try:
            lob = params["lob"].lower()
            findings = []
            for case in CASES_BY_RULE.get(params["rule_id"], []):
                result = _run_flow_threaded(lob, case["persona"])
                findings.extend(validate_case(case, result))
            job_store.complete_job(jid, format_audit_report(lob, findings, rule_filter=params["rule_id"]))
        except Exception as exc:
            job_store.fail_job(jid, str(exc))
    return _run


def _dispatch_run_custom_boundary(jid: str, params: dict):
    def _run():
        try:
            lob = params["lob"]
            pjson = generate_persona(lob, params["description"])
            persona = json.loads(pjson)
            if "error" in persona:
                job_store.fail_job(jid, persona["error"])
                return
            result = _run_flow_threaded(lob, persona)
            findings = validate_case(
                {
                    "case_id": "custom_boundary",
                    "rule_id": "CUSTOM",
                    "rule_name": "Custom Boundary Test",
                    "lob": lob,
                    "case_type": "boundary",
                    "severity": "high",
                    "description": params["description"],
                    "persona": persona,
                    "expected_outcome": params["expected_outcome"],
                    "expected_conditions": params.get("expected_conditions", []),
                    "min_conditions": None,
                },
                result,
            )
            report = format_boundary_report(
                lob,
                params["description"],
                params["expected_outcome"],
                params.get("expected_conditions", []),
                result,
                findings,
            )
            job_store.complete_job(jid, report)
        except Exception as exc:
            job_store.fail_job(jid, str(exc))
    return _run


def _dispatch_create_persona_variations(jid: str, params: dict):
    def _run():
        try:
            lob = params["lob"]
            base_description = params["base_description"]
            count = int(params.get("count") or 5)
            raw = generate_persona_variations(lob, base_description, count)

            import json as _json
            personas = _json.loads(raw)

            if isinstance(personas, dict) and "error" in personas:
                job_store.fail_job(jid, personas["error"])
                return

            if not isinstance(personas, list):
                personas = [personas]

            sections = []
            for i, p in enumerate(personas, 1):
                name = f"{p.get('FirstName', '')} {p.get('LastName', '')}".strip()
                note = p.get("_note", "")
                clean = {k: v for k, v in p.items() if not k.startswith("_")}
                heading = f"### Variation {i}" + (f" — {name}" if name else "")
                note_line = f"\n_{note}_\n" if note else ""
                sections.append(
                    f"{heading}\n{note_line}\n```json\n{_json.dumps(clean, indent=2)}\n```"
                )

            report = (
                f"## {len(personas)} {lob.upper()} Persona Variations\n\n"
                f"**Base:** {base_description}\n\n"
                + "\n\n---\n\n".join(sections)
            )
            job_store.complete_job(jid, report)
        except Exception as exc:
            job_store.fail_job(jid, str(exc))
    return _run


def _dispatch_run_full_audit(jid: str, params: dict):
    def _run():
        try:
            findings = []
            for lob_key, cases in CASES_BY_LOB.items():
                for case in cases:
                    result = _run_flow_threaded(lob_key, case["persona"])
                    findings.extend(validate_case(case, result))
            job_store.complete_job(jid, format_audit_report("all", findings))
        except Exception as exc:
            job_store.fail_job(jid, str(exc))
    return _run


_DISPATCH = {
    "run_quick_policy":          _dispatch_run_quick_policy,
    "create_persona":            _dispatch_create_persona,
    "run_batch_policies":        _dispatch_run_batch_policies,
    "run_uw_audit":              _dispatch_run_uw_audit,
    "run_rule_cases":            _dispatch_run_rule_cases,
    "run_custom_boundary":       _dispatch_run_custom_boundary,
    "run_full_audit":            _dispatch_run_full_audit,
    "create_persona_variations": _dispatch_create_persona_variations,
    # list_uw_rules has creates_job=False — handled inline, not in this table
}


def _job_label(tool_name: str, params: dict) -> str:
    labels = {
        "run_quick_policy":          lambda p: f"Chat - Quick Policy - {p.get('lob', '').upper()}",
        "create_persona":            lambda p: f"Chat - Build Profile - {p.get('lob', '').upper()}",
        "run_batch_policies":        lambda p: f"Chat - Batch Test - {len(p.get('scenarios', []))} scenarios",
        "run_uw_audit":              lambda p: f"Chat - UW Audit - {p.get('lob', '').upper()}",
        "run_rule_cases":            lambda p: f"Chat - Rule Test - {p.get('rule_id', '')}",
        "run_custom_boundary":       lambda p: f"Chat - Edge Case - {p.get('lob', '').upper()}",
        "run_full_audit":            lambda _: "Chat - Full System Audit",
        "create_persona_variations": lambda p: f"Chat - {p.get('count', 5)} {p.get('lob', '').upper()} Variations",
    }
    fn = labels.get(tool_name)
    return fn(params) if fn else f"Chat - {tool_name}"


def _list_uw_rules_inline(lob: str) -> str:
    """Return the UW rules markdown table. Mirrors /api/uw/rules logic."""
    target = lob.lower().strip() if lob else None
    lob_display = {"auto": "Personal Auto", "cyber": "Cyber", "homeowner": "Homeowner"}
    sev_icon = {"critical": "🔴", "high": "🟠", "warning": "🟡"}
    lob_groups: dict = {}
    for rule in RULE_METADATA.values():
        if target and rule["lob"] != target:
            continue
        lob_groups.setdefault(rule["lob"], []).append(rule)
    lines = ["# Registered UW Rules\n"]
    for lob_key in ["auto", "cyber", "homeowner"]:
        rules = lob_groups.get(lob_key, [])
        if not rules:
            continue
        lines.append(f"## {lob_display.get(lob_key, lob_key.upper())}\n")
        lines.append("| Rule ID | Rule Name | Severity | Cases |")
        lines.append("|---------|-----------|----------|-------|")
        for rule in sorted(rules, key=lambda r: r["rule_id"]):
            cases = CASES_BY_RULE.get(rule["rule_id"], [])
            pos = sum(1 for c in cases if c["case_type"] == "positive")
            neg = sum(1 for c in cases if c["case_type"] == "negative")
            bnd = sum(1 for c in cases if c["case_type"] == "boundary")
            icon = sev_icon.get(rule["severity"], "")
            lines.append(
                f"| `{rule['rule_id']}` | {rule['rule_name']} | {icon} {rule['severity']} "
                f"| +{pos} pos, -{neg} neg, ~{bnd} boundary |"
            )
        lines.append("")
    return "\n".join(lines)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/greeting")
def chat_greeting():
    return {
        "greeting": (
            "Hi! I'm your insurance testing assistant. I can run policy flows, "
            "generate customer profiles, and audit underwriting rules — all through "
            "approved automation tools. How can I help?"
        ),
        "capabilities": list(REGISTRY.keys()),
    }


@router.post("/message", response_model=ChatMessageResp)
def chat_message(req: ChatMessageReq, bg: BackgroundTasks):
    """
    Main chat endpoint. Two paths:

    Confirmed path (req.confirmed_tool is set):
      Re-validates params (defense in depth) and dispatches immediately.

    Intent-parse path:
      1. parse_intent()   — NL → { tool, params, reply }
      2. validate_params() — whitelist gate
      3a. creates_job=False → return inline result (list_uw_rules)
      3b. requires_confirmation=True → return status="confirm" with tool_call
      3c. immediate dispatch → return status="job" with job_id

    ARCHITECTURE BOUNDARY: tool dispatch only occurs after the tool name appears
    in REGISTRY and params pass validate_params().
    """
    # ── Confirmed dispatch path ──────────────────────────────────────────────
    if req.confirmed_tool:
        tool_name = req.confirmed_tool
        if tool_name not in REGISTRY:
            return ChatMessageResp(reply=f"Unknown tool: {tool_name!r}", status="error")
        try:
            # Re-validate on confirm — client cannot bypass registry
            cleaned = validate_params(tool_name, req.confirmed_params or {})
        except ToolValidationError as exc:
            return ChatMessageResp(reply=str(exc), status="error")

        tool_spec = REGISTRY[tool_name]

        if not tool_spec["creates_job"]:
            return ChatMessageResp(reply=_list_uw_rules_inline(cleaned.get("lob", "")), status="ok")

        dispatch_fn = _DISPATCH.get(tool_name)
        if not dispatch_fn:
            return ChatMessageResp(reply=f"No dispatch handler for {tool_name!r}.", status="error")

        label = _job_label(tool_name, cleaned)
        jid = job_store.new_job(
            label,
            execution_type="chat_execution",
            metadata={"tool": tool_name, "params": cleaned},
        )
        bg.add_task(dispatch_fn(jid, cleaned))
        return ChatMessageResp(
            reply=f"Started. Job `{jid}` is running — check the Jobs panel for results.",
            status="job",
            job_id=jid,
            job_label=label,
        )

    # ── Intent-parse path ────────────────────────────────────────────────────
    message = (req.message or "").strip()
    if not message:
        return ChatMessageResp(reply="Please enter a message.", status="error")
    if len(message) > _MAX_MESSAGE_CHARS:
        return ChatMessageResp(
            reply=f"Message too long (max {_MAX_MESSAGE_CHARS} characters).", status="error"
        )

    try:
        intent = parse_intent(message)
    except Exception as exc:
        return ChatMessageResp(reply=f"Could not parse your request: {exc}", status="error")

    tool_name = intent.get("tool")
    reply_text = intent.get("reply", "")
    raw_params = intent.get("params") or {}

    if not tool_name:
        return ChatMessageResp(reply=reply_text or "I'm not sure how to help with that.", status="ok")

    if tool_name not in REGISTRY:
        return ChatMessageResp(
            reply=f"That action ({tool_name!r}) is not in the approved tool list.",
            status="ok",
        )

    try:
        cleaned = validate_params(tool_name, raw_params)
    except ToolValidationError as exc:
        return ChatMessageResp(reply=str(exc), status="error")

    tool_spec = REGISTRY[tool_name]

    if not tool_spec["creates_job"]:
        return ChatMessageResp(reply=_list_uw_rules_inline(cleaned.get("lob", "")), status="ok")

    if tool_spec["requires_confirmation"]:
        return ChatMessageResp(
            reply=reply_text or f"Ready to run **{tool_name}**. Confirm to proceed.",
            status="confirm",
            tool_call={"tool": tool_name, "params": cleaned},
        )

    dispatch_fn = _DISPATCH.get(tool_name)
    if not dispatch_fn:
        return ChatMessageResp(reply=f"No dispatch handler for {tool_name!r}.", status="error")

    label = _job_label(tool_name, cleaned)
    jid = job_store.new_job(
        label,
        execution_type="chat_execution",
        metadata={"tool": tool_name, "params": cleaned},
    )
    bg.add_task(dispatch_fn(jid, cleaned))
    return ChatMessageResp(
        reply=reply_text or "Job started — check the Jobs panel for results.",
        status="job",
        job_id=jid,
        job_label=label,
    )
