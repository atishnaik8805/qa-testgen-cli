from pathlib import Path

import yaml

from qa_gen.models.component import Component
from qa_gen.models.form import Form


def _load_vocabulary(kb_path: Path) -> str:
    path = kb_path / "ui_vocabulary.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _derive_required_scenarios(components: list[Component]) -> str:
    seen: set[str] = set()
    required = []
    for comp in components:
        for pattern in comp.required_test_patterns:
            key = f"{pattern}:{comp.id}"
            if key not in seen:
                seen.add(key)
                required.append(f"{pattern} for component '{comp.id}'")
    if not required:
        return ""
    return "## Required Scenarios (MUST generate one each)\n" + "\n".join(f"- {r}" for r in required)


def _derive_edge_case_hints(form: Form) -> str:
    hints = []
    for f in form.fields:
        if f.max_length:
            hints.append(f"{f.id}: test {f.max_length - 1}, {f.max_length}, {f.max_length + 1} chars")
        if f.type == "date":
            hints.append(f"{f.id}: test cross-month, cross-year, same-day, past date")
    if hints:
        return "## Derived Edge Case Hints\n" + "\n".join(f"- {h}" for h in hints)
    return ""


def assemble_context(form: Form, components: list[Component], kb_path: Path) -> str:
    vocabulary = _load_vocabulary(kb_path)
    edge_case_hints = _derive_edge_case_hints(form)

    form_yaml = yaml.dump(form.model_dump(exclude_none=True), allow_unicode=True, sort_keys=False)
    form_section = f"## Form Definition\n\n```yaml\n{form_yaml}```"

    component_sections = []
    for comp in components:
        comp_yaml = yaml.dump(comp.model_dump(exclude_none=True), allow_unicode=True, sort_keys=False)
        component_sections.append(f"### Component: {comp.id}\n\n```yaml\n{comp_yaml}```")

    required_scenarios = _derive_required_scenarios(components)

    parts = [vocabulary, form_section]
    if component_sections:
        parts.append("## Component Definitions\n\n" + "\n\n".join(component_sections))
    if edge_case_hints:
        parts.append(edge_case_hints)
    if required_scenarios:
        parts.append(required_scenarios)

    return "\n\n".join(parts)


def assemble_system_prompt(max_tests: int = 15) -> str:
    return (
        "You are an expert QA engineer specializing in UI test case generation.\n\n"
        "Your task is to generate comprehensive Gherkin-format test cases for the JIRA story provided.\n\n"
        "Rules:\n"
        f"- Generate at most {max_tests} test cases total\n"
        "- Minimum coverage: 2 happy path, 3 negative/validation, 2 edge case, 3 field-interaction\n"
        "- REQUIRED: generate every scenario listed in the 'Required Scenarios' section of the context\n"
        "- Each test case must be a valid Gherkin Scenario or Scenario Outline block\n"
        "- Use Given/When/Then/And keywords correctly\n"
        "- REQUIRED: use @tags on EVERY scenario — pick from: @smoke @happy_path @negative @validation @edge_case @field_interaction @blur @save_trigger\n"
        "- REQUIRED: use a Background block for any Given steps repeated across scenarios\n"
        "- REQUIRED: use Scenario Outline + Examples table when testing multiple values of the same field (e.g. all leave types)\n"
        "- For each component's interaction_steps: generate one scenario per non-happy-path interaction (Escape, click-outside, invalid input)\n"
        "- For text fields with max_length in Derived Edge Case Hints: generate N-1, N, N+1 boundary scenarios\n"
        "- For date fields: generate cross-month, cross-year, same-day scenarios\n"
        "- Ground test cases in the form definition and component interaction steps provided — use exact field IDs\n"
        "- Reference exact save trigger patterns from the form definition\n"
        "- Output ONLY the Gherkin Feature block — no prose, no markdown fences, no explanation\n\n"
        "Example of correct output (follow this structure exactly):\n\n"
        "Feature: Submit expense claim\n\n"
        "  Background:\n"
        "    Given the employee is logged in\n"
        "    And the expense_claim_form is displayed\n\n"
        "  @happy_path @smoke\n"
        "  Scenario: Submit with all required fields filled\n"
        "    Given the employee selects \"Travel\" in the expense_type field\n"
        "    And the employee enters \"2025-08-01\" in the expense_date field\n"
        "    And the employee enters \"150.00\" in the amount field\n"
        "    When the employee clicks the Submit button\n"
        "    Then the expense claim is created with status \"Pending Approval\"\n\n"
        "  @negative @validation\n"
        "  Scenario: Submit with amount field empty\n"
        "    Given the expense_type field is set to \"Travel\"\n"
        "    And the amount field is left empty\n"
        "    When the employee clicks the Submit button\n"
        "    Then the form is NOT submitted\n"
        "    And an inline error is shown: \"Amount is required\"\n\n"
        "  @field_interaction @blur\n"
        "  Scenario: Validation error shown on amount blur when empty\n"
        "    Given the employee focuses on the amount field\n"
        "    And does not enter a value\n"
        "    When the employee moves focus away from the amount field\n"
        "    Then an inline error is displayed: \"Amount is required\"\n\n"
        "  @edge_case\n"
        "  Scenario Outline: Submit for each expense type\n"
        "    Given the employee selects \"<expense_type>\" in the expense_type field\n"
        "    And the employee enters \"2025-08-01\" in the expense_date field\n"
        "    And the employee enters \"50.00\" in the amount field\n"
        "    When the employee clicks the Submit button\n"
        "    Then the expense claim is created with expense_type \"<expense_type>\"\n\n"
        "    Examples:\n"
        "      | expense_type |\n"
        "      | Travel       |\n"
        "      | Meals        |\n"
        "      | Accommodation|\n"
    )
