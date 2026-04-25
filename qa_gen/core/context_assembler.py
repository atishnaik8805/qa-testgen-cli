from pathlib import Path

import yaml

from qa_gen.models.component import Component
from qa_gen.models.form import Form


def _load_vocabulary(kb_path: Path) -> str:
    path = kb_path / "ui_vocabulary.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def assemble_context(form: Form, components: list[Component], kb_path: Path) -> str:
    vocabulary = _load_vocabulary(kb_path)

    form_yaml = yaml.dump(form.model_dump(exclude_none=True), allow_unicode=True, sort_keys=False)
    form_section = f"## Form Definition\n\n```yaml\n{form_yaml}```"

    component_sections = []
    for comp in components:
        comp_yaml = yaml.dump(comp.model_dump(exclude_none=True), allow_unicode=True, sort_keys=False)
        component_sections.append(f"### Component: {comp.id}\n\n```yaml\n{comp_yaml}```")

    parts = [vocabulary, form_section]
    if component_sections:
        parts.append("## Component Definitions\n\n" + "\n\n".join(component_sections))

    return "\n\n".join(parts)


def assemble_system_prompt() -> str:
    return (
        "You are an expert QA engineer specializing in UI test case generation.\n\n"
        "Your task is to generate comprehensive Gherkin-format test cases for the JIRA story provided.\n\n"
        "Rules:\n"
        "- Generate at most 15 test cases total\n"
        "- Cover positive, negative, and edge cases\n"
        "- Each test case must be a valid Gherkin Scenario block\n"
        "- Use Given/When/Then/And keywords correctly\n"
        "- Ground test cases in the form definition and component interaction steps provided\n"
        "- Reference exact save trigger patterns from the form definition\n"
        "- Include blur-does-not-save scenarios for SAVE_EXPLICIT forms\n"
        "- Include blur-triggers-save scenarios for fields with save_on_blur=true\n"
        "- Output ONLY the Gherkin Feature block — no prose, no markdown fences, no explanation\n\n"
        "Format:\n"
        "Feature: <story summary>\n\n"
        "  Scenario: <title>\n"
        "    Given <precondition>\n"
        "    When <action>\n"
        "    And <action>\n"
        "    Then <expected result>\n"
    )
