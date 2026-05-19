from __future__ import annotations

import json
import re
from pathlib import Path

from .framework import FrameworkInspection
from .models import GeneratedArtifact, LocatorCandidate, RecordedAction, RecordedPage, RecordingSession


def finalize_data_collection(session: RecordingSession) -> None:
    session.collected_data.setdefault("TC_ID", session.tc_id)
    session.collected_data.setdefault("LOB", session.lob.replace("_", " ").title())
    for page in session.pages + ([session.current_page] if session.current_page else []):
        if not page:
            continue
        for action in page.actions:
            if action.kind not in {"fill", "select_dropdown", "select_radio", "set_checkbox"}:
                continue
            key = to_data_key(action.label or action.name or action.text or action.target_key)
            if not key or key == "TcId":
                continue
            value = action.value
            if action.kind == "set_checkbox":
                value = "Yes" if action.checked else "No"
            if action.kind == "select_radio" and not value:
                value = action.name or action.text
            if "email" in key.lower():
                value = normalize_email_value(value)
            session.collected_data[key] = value or session.collected_data.get(key, "")


def normalize_email_value(value: str) -> str:
    if not value:
        return "user_{timestamp}@example.com"
    if "{timestamp}" in value:
        return value
    if "@" not in value:
        return value
    local, domain = value.split("@", 1)
    safe_local = re.sub(r"[^a-zA-Z0-9._-]+", "_", local).strip("_") or "user"
    return f"{safe_local}_{{timestamp}}@{domain}"


def generate_all_artifacts(session: RecordingSession, framework: FrameworkInspection) -> list[GeneratedArtifact]:
    finalize_data_collection(session)
    artifacts: list[GeneratedArtifact] = []
    output_root = Path(session.output_root)
    for page in session.pages:
        artifacts.append(generate_page_object_file(output_root, session, page, framework))
    artifacts.extend(generate_step_and_test_files(output_root, session, framework))
    artifacts.append(generate_feature_file(output_root, session))
    artifacts.append(generate_test_data_file(output_root, session))
    artifacts.append(generate_fixture_snippet(output_root, session))
    artifacts.append(generate_readme(output_root, session, framework))
    session.generated_files = artifacts
    return artifacts


def generate_page_object_file(output_root: Path, session: RecordingSession, page: RecordedPage, framework: FrameworkInspection) -> GeneratedArtifact:
    page_dir = output_root / "ui" / "pages" / page.output_group
    page_dir.mkdir(parents=True, exist_ok=True)
    path = page_dir / f"{page.file_stem}.py"
    path.write_text(render_page_object(session, page, framework), encoding="utf-8")
    return GeneratedArtifact("page_object", str(path))


def render_page_object(session: RecordingSession, page: RecordedPage, framework: FrameworkInspection) -> str:
    locator_lines: list[str] = []
    method_lines: list[str] = []
    orchestration: list[str] = []
    seen_locator_names: set[str] = set()
    summary_methods: list[str] = []

    for action in page.actions:
        locator_name = locator_var_name(action)
        if locator_name not in seen_locator_names:
            candidate = infer_locator(action)
            if candidate.notes:
                for note in candidate.notes:
                    locator_lines.append(f"        # TODO: {note}")
            locator_lines.append(f"        self.{locator_name} = {candidate.expression}")
            seen_locator_names.add(locator_name)
        method_lines.append(render_action_method(action, locator_name))
        orchestration.append(f"        self.{action_method_name(action)}(data)")

    for label in page.snapshot.summary_values:
        method_name = f"get_{snake_case(label)}"
        summary_methods.append(
            f"    def {method_name}(self):\n"
            f"        return self.read_summary({json.dumps(label)})\n"
        )

    orchestration_method = (
        f"    def complete_{page.business_step}(self, data):\n"
        + ("\n".join(orchestration) if orchestration else "        pass")
        + "\n"
    )

    return (
        "import allure\n\n"
        "from ui.pages.common.base_page import BasePage\n\n\n"
        f"class {page.class_name}(BasePage):\n"
        f"    \"\"\"Generated page object for {page.snapshot.header or page.snapshot.title or page.name}.\"\"\"\n\n"
        "    DEFAULT_SPINNER_SELECTOR = \"#ajax-sub-pre-loading\"\n\n"
        "    def __init__(self, page):\n"
        "        super().__init__(page)\n"
        + ("\n".join(locator_lines) if locator_lines else "        pass")
        + "\n\n"
        + render_select_option_helper()
        + "\n"
        + ("\n\n".join(method_lines) if method_lines else "    pass")
        + "\n\n"
        + orchestration_method
        + ("\n" + "\n".join(summary_methods) if summary_methods else "")
    )


def render_select_option_helper() -> str:
    return (
        "    def _select_option(self, locator, value):\n"
        "        \"\"\"ExtJS-friendly dropdown helper built on BasePage wrappers.\"\"\"\n"
        "        self.smart_click(locator)\n"
        "        option = self.page.get_by_role(\"option\", name=value, exact=True)\n"
        "        if option.count() > 0:\n"
        "            self.smart_click(option.first)\n"
        "            return\n"
        "        self.smart_fill(locator, value)\n"
    )


def render_action_method(action: RecordedAction, locator_name: str) -> str:
    method = action_method_name(action)
    data_key = to_data_key(action.label or action.name or action.text or locator_name)
    if action.kind == "fill":
        call = f"self.smart_fill(self.{locator_name}, data[{json.dumps(data_key)}])"
    elif action.kind == "select_dropdown":
        call = f"self._select_option(self.{locator_name}, data[{json.dumps(data_key)}])"
    elif action.kind == "set_checkbox":
        call = (
            f"target = str(data.get({json.dumps(data_key)}, {'\"Yes\"' if action.checked else '\"No\"'})).lower() in ('yes', 'true', '1')\n"
            f"        if self.{locator_name}.is_checked() != target:\n"
            f"            self.smart_click(self.{locator_name})"
        )
    elif action.kind == "select_radio":
        question = action.label or action.name or action.text or data_key
        call = f"self.answer_question({json.dumps(question)}, data[{json.dumps(data_key)}])"
    else:
        call = f"self.smart_click(self.{locator_name})"
        if any(token in method for token in ("next", "save", "rate", "bind", "issue")):
            call += "\n        self.spinner_wait(self.DEFAULT_SPINNER_SELECTOR)"

    return (
        f"    @allure.step({json.dumps(method.replace('_', ' ').title())})\n"
        f"    def {method}(self, data):\n"
        f"        {call}\n"
    )


def infer_locator(action: RecordedAction) -> LocatorCandidate:
    label = action.locator.get("label") or action.label
    role = action.locator.get("role") or action.role
    name = action.locator.get("name") or action.name
    text = action.locator.get("text") or action.text
    notes: list[str] = []
    if label:
        return LocatorCandidate("label", f"page.get_by_label({json.dumps(label)})", 0.95, notes)
    if role and name:
        exact = "True" if len(name) < 40 else "False"
        return LocatorCandidate(
            "role",
            f"page.get_by_role({json.dumps(role)}, name={json.dumps(name)}, exact={exact})",
            0.9,
            notes,
        )
    if text:
        notes.append(f"Locator for '{text}' fell back to visible text. Confirm it is unique and stable.")
        return LocatorCandidate("text", f"page.get_by_text({json.dumps(text)}, exact=True)", 0.55, notes)
    notes.append("No stable locator signal was captured for this element. Replace the placeholder selector.")
    return LocatorCandidate("todo", 'page.locator("TODO_REPLACE_WITH_STABLE_LOCATOR")', 0.1, notes)


def generate_step_and_test_files(output_root: Path, session: RecordingSession, framework: FrameworkInspection) -> list[GeneratedArtifact]:
    steps_dir = output_root / "ui" / "steps"
    tests_dir = output_root / "ui" / "tests"
    steps_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)
    flow_slug = slug_case(session.flow_name)
    step_path = steps_dir / f"{flow_slug}_steps.py"
    test_path = tests_dir / f"test_{flow_slug}.py"
    page_imports = "\n".join(
        f"from ui.pages.{page.output_group}.{page.file_stem} import {page.class_name}"
        for page in session.pages
    )
    fixture_names = [snake_case(page.class_name) for page in session.pages]
    step_functions = []
    for page, fixture_name in zip(session.pages, fixture_names):
        step_text = business_step_text(page)
        step_functions.append(
            f"@when({json.dumps(step_text)})\n"
            f"def step_{page.business_step}({fixture_name}, test_data, log):\n"
            f"    log.info({json.dumps('Executing ' + step_text)})\n"
            f"    {fixture_name}.complete_{page.business_step}(test_data)\n"
        )
    final_assert_page = session.pages[-1] if session.pages else None
    assert_block = ""
    if final_assert_page and final_assert_page.snapshot.summary_values:
        first_label = next(iter(final_assert_page.snapshot.summary_values))
        assert_block = (
            f"@then({json.dumps('the policy should be successfully created')})\n"
            f"def step_policy_created({snake_case(final_assert_page.class_name)}, log):\n"
            f"    value = {snake_case(final_assert_page.class_name)}.read_summary({json.dumps(first_label)})\n"
            f"    assert value, {json.dumps('Expected summary value for ' + first_label)}\n"
            f"    log.info({json.dumps('Policy creation assertion passed')})\n"
        )
    else:
        assert_block = (
            "@then(\"the policy should be successfully created\")\n"
            "def step_policy_created(log):\n"
            "    log.info(\"Final business assertion placeholder reached.\")\n"
        )
    step_path.write_text(
        "from pytest_bdd import then, when\n\n"
        + page_imports
        + "\n\n"
        + "\n\n".join(step_functions)
        + "\n\n"
        + assert_block,
        encoding="utf-8",
    )
    test_path.write_text(
        "from pytest_bdd import scenario\n\n"
        f"@scenario('../features/{session.lob}/{flow_slug}.feature', {json.dumps(feature_scenario_name(session))})\n"
        f"def test_{flow_slug}():\n"
        "    pass\n",
        encoding="utf-8",
    )
    return [
        GeneratedArtifact("step_definitions", str(step_path)),
        GeneratedArtifact("test_entry_point", str(test_path)),
    ]


def generate_feature_file(output_root: Path, session: RecordingSession) -> GeneratedArtifact:
    feature_dir = output_root / "ui" / "features" / session.lob
    feature_dir.mkdir(parents=True, exist_ok=True)
    flow_slug = slug_case(session.flow_name)
    path = feature_dir / f"{flow_slug}.feature"
    steps = "\n".join(
        ("    When " if idx == 0 else "    And ") + business_step_text(page)
        for idx, page in enumerate(session.pages)
    )
    path.write_text(
        f"Feature: {session.flow_name}\n\n"
        "  Background:\n"
        "    Given The user is logged in with valid credentials\n\n"
        f"  Scenario Outline: {feature_scenario_name(session)}\n"
        f"    Given the data is loaded \"testdata/static/{data_file_name(session)}\", \"<TC_ID>\"\n"
        f"{steps}\n"
        "    Then the policy should be successfully created\n\n"
        "    Examples:\n"
        "      | TC_ID |\n"
        f"      | {session.tc_id} |\n",
        encoding="utf-8",
    )
    return GeneratedArtifact("feature_file", str(path))


def generate_test_data_file(output_root: Path, session: RecordingSession) -> GeneratedArtifact:
    finalize_data_collection(session)
    data_dir = output_root / "testdata" / "static"
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / data_file_name(session)
    payload = {"testCases": [session.collected_data]}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return GeneratedArtifact("test_data", str(path))


def generate_fixture_snippet(output_root: Path, session: RecordingSession) -> GeneratedArtifact:
    path = output_root / "ui" / "fixtures_generated.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    imports = "\n".join(
        f"from ui.pages.{page.output_group}.{page.file_stem} import {page.class_name}"
        for page in session.pages
    )
    fixtures = "\n\n".join(
        f"@pytest.fixture\ndef {snake_case(page.class_name)}(page):\n    return {page.class_name}(page)"
        for page in session.pages
    )
    path.write_text(
        "import pytest\n\n"
        + imports
        + "\n\n"
        + fixtures
        + "\n",
        encoding="utf-8",
    )
    return GeneratedArtifact("fixture_snippet", str(path))


def generate_readme(output_root: Path, session: RecordingSession, framework: FrameworkInspection) -> GeneratedArtifact:
    path = output_root / "README.md"
    generated_page_paths = "\n".join(
        f"- `ui/pages/{page.output_group}/{page.file_stem}.py`"
        for page in session.pages
    )
    path.write_text(
        f"# {session.flow_name}\n\n"
        "This folder was generated by the local `Framework-Guided Policy Flow Generator` MCP server.\n\n"
        "## What was generated\n\n"
        f"{generated_page_paths}\n"
        f"- `ui/steps/{slug_case(session.flow_name)}_steps.py`\n"
        f"- `ui/tests/test_{slug_case(session.flow_name)}.py`\n"
        f"- `ui/features/{session.lob}/{slug_case(session.flow_name)}.feature`\n"
        f"- `testdata/static/{data_file_name(session)}`\n"
        "- `ui/fixtures_generated.py`\n"
        "- `flow_manifest.json`\n\n"
        "## Integration notes\n\n"
        "- Review any `TODO` locator comments before moving files into the live framework.\n"
        "- Register new page fixtures from `ui/fixtures_generated.py` into the real `ui/fixtures.py`.\n"
        "- Register the generated step module in `conftest.py` `pytest_plugins`.\n"
        "- Keep generated page methods on top of `BasePage` wrappers such as `smart_click`, `smart_fill`, `answer_question`, and `spinner_wait`.\n\n"
        "## Example flow\n\n"
        "1. Start the MCP server.\n"
        "2. Call `start_policy_recording` with a target URL.\n"
        "3. Manually complete the policy flow in the opened browser.\n"
        "4. Call `capture_action` periodically, `mark_page_complete` for each screen, then `finalize_policy_flow`.\n",
        encoding="utf-8",
    )
    return GeneratedArtifact("generated_readme", str(path))


def locator_var_name(action: RecordedAction) -> str:
    base = snake_case(action.label or action.name or action.text or action.target_key or "element")
    suffix = {
        "fill": "input",
        "select_dropdown": "dropdown",
        "set_checkbox": "checkbox",
        "select_radio": "radio_group",
        "click": "button" if action.role in {"button", "link"} else "element",
    }.get(action.kind, "element")
    if base.endswith(suffix):
        return base
    return f"{base}_{suffix}"


def action_method_name(action: RecordedAction) -> str:
    base = snake_case(action.label or action.name or action.text or action.target_key or "element")
    if action.kind == "fill":
        return f"enter_{base}"
    if action.kind == "select_dropdown":
        return f"select_{base}"
    if action.kind == "set_checkbox":
        return f"set_{base}"
    if action.kind == "select_radio":
        return f"answer_{base}"
    return f"click_{base}"


def to_data_key(label: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", label)
    if not words:
        return ""
    return "".join(word[:1].upper() + word[1:] for word in words)


def snake_case(value: str) -> str:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    parts = re.findall(r"[A-Za-z0-9]+", normalized)
    return "_".join(part.lower() for part in parts) or "generated"


def slug_case(value: str) -> str:
    return snake_case(value)


def feature_scenario_name(session: RecordingSession) -> str:
    return f"Create and bind a {session.flow_name}"


def data_file_name(session: RecordingSession) -> str:
    return f"{''.join(part.capitalize() for part in slug_case(session.flow_name).split('_'))}Data.json"


def business_step_text(page: RecordedPage) -> str:
    label = page.snapshot.header or page.name
    return f"I complete {label.lower()}"
