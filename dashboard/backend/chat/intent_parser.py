"""
CHATBOT INTENT PARSER — natural language → structured tool call.

Uses the configured chat LLM provider to translate the user's message into
{ tool, params, reply }.

ARCHITECTURE BOUNDARY: This module only produces a structured intent object.
Validation against the whitelist and all dispatch happen in chat_router.py.
The parser never accesses the browser, DB, filesystem, or credentials.
"""
import re
import json

from llm_provider import complete_json
from tool_registry import registry_summary_for_prompt

_SYSTEM_TEMPLATE = """\
You are the intent parser for an insurance testing dashboard chatbot.

Your ONLY job is to parse the user's natural-language request into a JSON object
describing which MCP tool to call, and your brief reply. Respond with raw JSON only —
no markdown fences, no extra text.

{tools}

JSON shape (all fields required):
  "tool"   — tool name from the list above, or null if no tool applies
  "params" — object of tool parameters (empty object if none)
  "reply"  — one friendly sentence: what you are about to do, or a direct answer
              if no tool is needed

═══════════════════════════════════════
ROUTING DECISION TREE
═══════════════════════════════════════

Step 1 — Does the user want to generate persona data only (no browser run)?
  • Single persona / profile / test data for ONE scenario
      → create_persona  (params: lob, description)
  • Multiple / N / several / variations / different personas from ONE base description
      → create_persona_variations  (params: lob, base_description, count)
      Extract count from words like "20 different", "15 variations", "give me 5", etc.
      Default count = 5 if not specified.

Step 2 — Does the user want API-level assertions with expected vs actual values?
  • Plain-English API assertion / expected premium / actual premium / assert value
      → run_api_assertion  (params: prompt)
      Keep the user's full message as prompt.

Step 3 — Does the user want to RUN policy flows (browser automation)?
  • Single policy run → run_quick_policy  (params: lob, description)
  • Multiple distinct scenarios → run_batch_policies  (params: scenarios list, max 10)

Step 4 — UW rules / audit?
  • List / show / query rules   → list_uw_rules  (params: lob optional)
  • Audit one LOB               → run_uw_audit  (params: lob)
  • Test specific rule by ID    → run_rule_cases  (params: lob, rule_id)
  • Custom edge-case boundary   → run_custom_boundary  (params: lob, description, expected_outcome)
  • Full system audit all LOBs  → run_full_audit  (params: none)

LOB synonyms:
  "auto" / "personal auto" / "car" / "vehicle" → "auto"
  "home" / "homeowner" / "house" / "property"  → "homeowner"
  "cyber" / "cybersecurity" / "data breach"    → "cyber"

Count extraction (for create_persona_variations):
  "20 different"     → count=20
  "generate 15"      → count=15
  "give me 5"        → count=5
  "a few"            → count=3
  "a bunch of"       → count=5
  "several"          → count=5
  not mentioned      → count=5

CRITICAL: When the user gives ONE base persona description and asks for MULTIPLE personas
(any phrasing: "generate me N", "create N different", "make N variations", "give me N personas"),
ALWAYS use create_persona_variations — not run_batch_policies, not create_persona.
Extract the base description by stripping out the count phrase.

═══════════════════════════════════════
EXAMPLES
═══════════════════════════════════════

"run a quick auto test for a young driver"
→ {{"tool":"run_quick_policy","params":{{"lob":"auto","description":"young driver"}},"reply":"Running an auto policy flow for a young driver."}}

"Create an auto persona for a 22-year-old driver with SR-22, revoked license, leased BMW, Platinum coverage. generate me 20 different personas"
→ {{"tool":"create_persona_variations","params":{{"lob":"auto","base_description":"22-year-old driver with SR-22, revoked license, leased BMW, Platinum coverage","count":20}},"reply":"Generating 20 distinct auto persona variations based on that profile."}}

"generate 5 different homeowner personas for a coastal property with prior losses"
→ {{"tool":"create_persona_variations","params":{{"lob":"homeowner","base_description":"coastal property homeowner with prior losses","count":5}},"reply":"Generating 5 coastal homeowner persona variations."}}

"give me 10 cyber profiles for a healthcare company"
→ {{"tool":"create_persona_variations","params":{{"lob":"cyber","base_description":"healthcare company cyber profile","count":10}},"reply":"Generating 10 healthcare cyber persona variations."}}

"assert that for young driver premium for gold coverage is 1000 usd"
→ {{"tool":"run_api_assertion","params":{{"prompt":"assert that for young driver premium for gold coverage is 1000 usd"}},"reply":"Running an Auto API assertion and I will report expected versus actual values."}}

"create a homeowner persona for a luxury coastal home"
→ {{"tool":"create_persona","params":{{"lob":"homeowner","description":"luxury coastal home homeowner"}},"reply":"Creating a homeowner persona for a luxury coastal home."}}

"audit cyber underwriting rules"
→ {{"tool":"run_uw_audit","params":{{"lob":"cyber"}},"reply":"I'll run the cyber UW audit — this requires confirmation."}}

"what UW rules exist?"
→ {{"tool":"list_uw_rules","params":{{}},"reply":"Here are all registered underwriting rules."}}

"run 2 scenarios: young auto driver and retired homeowner"
→ {{"tool":"run_batch_policies","params":{{"scenarios":[{{"lob":"auto","description":"young driver"}},{{"lob":"homeowner","description":"retired homeowner"}}]}},"reply":"I'll queue 2 policy scenarios for batch execution."}}

"what can you do?"
→ {{"tool":null,"params":{{}},"reply":"I can run policy tests, generate personas (single or N variations), audit underwriting rules, and more."}}
"""


def parse_intent(message: str) -> dict:
    """
    Translate a natural-language message into:
      { "tool": str | None, "params": dict, "reply": str }

    ARCHITECTURE BOUNDARY: output is a data structure only.
    Validation and dispatch happen in chat_router.py.
    """
    api_assertion = _api_assertion_intent(message)
    if api_assertion:
        return api_assertion

    system = _SYSTEM_TEMPLATE.format(tools=registry_summary_for_prompt())
    raw = complete_json(system=system, user=message, max_tokens=600)

    # Strip markdown fences if the model wraps output anyway
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Intent parser response must be a JSON object.")
    if "tool" not in parsed or "params" not in parsed or "reply" not in parsed:
        raise ValueError("Intent parser response must include tool, params, and reply.")
    if parsed.get("tool") is not None and not isinstance(parsed.get("tool"), str):
        raise ValueError("Intent parser field 'tool' must be a string or null.")
    if not isinstance(parsed.get("params"), dict):
        raise ValueError("Intent parser field 'params' must be an object.")
    if not isinstance(parsed.get("reply"), str):
        raise ValueError("Intent parser field 'reply' must be a string.")

    return {
        "tool": parsed.get("tool"),
        "params": parsed.get("params") or {},
        "reply": parsed.get("reply", ""),
    }


def _api_assertion_intent(message: str) -> dict | None:
    text = " ".join((message or "").split())
    lower = text.lower()
    has_assertion_word = any(word in lower for word in ("assert", "expected", "actual", "should be"))
    has_api_subject = any(
        word in lower
        for word in ("api", "premium", "price", "rate", "coverage", "uw referral", "underwriting referral")
    )
    if has_assertion_word and has_api_subject:
        return {
            "tool": "run_api_assertion",
            "params": {"prompt": text},
            "reply": "Running an Auto API assertion and I will report expected versus actual values.",
        }
    return None
