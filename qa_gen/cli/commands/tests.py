import json
import sys
import tempfile
from pathlib import Path
from typing import Annotated, Optional

import typer

from qa_gen.cli import display
from qa_gen.config.settings import load_settings
from qa_gen.models.test_case import TestCase

tests_app = typer.Typer(help="Generate test cases for a JIRA story")


def _validate_story_id(story_id: str) -> None:
    import re
    if not re.match(r"^[A-Z][A-Z0-9_]+-\d+$", story_id):
        typer.echo(
            f"invalid story ID format: {story_id!r} — expected format: PROJ-123",
            err=True,
        )
        raise typer.Exit(1)


def _gherkin_text(test_cases: list[TestCase], story_id: str) -> str:
    lines = [f"Feature: Test cases for {story_id}\n"]
    for tc in test_cases:
        lines.append(tc.to_gherkin_scenario())
        lines.append("")
    return "\n".join(lines)


def _write_md(test_cases: list[TestCase], story_id: str) -> Path:
    path = Path(f"test-cases-{story_id}.md")
    path.write_text(_gherkin_text(test_cases, story_id), encoding="utf-8")
    return path


def _write_json(test_cases: list[TestCase], story_id: str) -> Path:
    path = Path(f"test-cases-{story_id}.json")
    payload = {
        "version": 1,
        "testCases": [
            {
                "name": tc.title,
                "status": "Draft",
                "precondition": "; ".join(tc.preconditions),
                "objective": tc.title,
                "testScript": {
                    "type": "STEP_BY_STEP",
                    "steps": [tc.to_zephyr_step()],
                },
                "labels": ["auto-generated", "qa-gen"],
                "customFields": {},
            }
            for tc in test_cases
        ],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


@tests_app.command()
def generate(
    story_id: str = typer.Argument(..., help="JIRA story ID, e.g. PROJ-1042"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Display without writing to JIRA"),
    export: Annotated[Optional[list[str]], typer.Option("--export", help="md or json")] = None,
    form: Optional[str] = typer.Option(None, "--form", help="Override auto-detected form ID"),
    no_confirm: bool = typer.Option(False, "--no-confirm", help="Skip action prompt; auto-push"),
    verbose: bool = typer.Option(False, "--verbose", help="Write debug log to ~/.qa-gen/debug.log"),
) -> None:
    _validate_story_id(story_id)
    export = export or []

    # Conflict: --dry-run wins over --no-confirm
    if dry_run and no_confirm:
        typer.echo("--no-confirm ignored: --dry-run is active", err=True)
        no_confirm = False

    settings = load_settings()

    from qa_gen.core.orchestrator import run
    test_cases = run(
        story_id=story_id,
        dry_run=dry_run,
        export_formats=export,
        form_override=form,
        no_confirm=no_confirm,
        verbose=verbose,
        settings=settings,
    )

    gherkin = _gherkin_text(test_cases, story_id)

    # Export flags bypass action prompt
    if export:
        if "md" in export:
            path = _write_md(test_cases, story_id)
            typer.echo(f"Written: {path}")
        if "json" in export:
            path = _write_json(test_cases, story_id)
            typer.echo(f"Written: {path}")
        if dry_run:
            return
        if no_confirm:
            _push(story_id, test_cases, settings, no_confirm=True)
        return

    if dry_run:
        display.show_with_pager(gherkin)
        return

    display.show_with_pager(gherkin)

    while True:
        action = display.action_prompt()

        if action == "push":
            _push(story_id, test_cases, settings, no_confirm)
            break
        elif action == "export":
            fmt = display.export_format_prompt()
            if fmt == "md":
                path = _write_md(test_cases, story_id)
            else:
                path = _write_json(test_cases, story_id)
            typer.echo(f"Written: {path}")
        elif action == "edit":
            test_cases = _edit_loop(test_cases, story_id, gherkin)
            gherkin = _gherkin_text(test_cases, story_id)
        elif action == "discard":
            break


def _push(story_id: str, test_cases: list[TestCase], settings, no_confirm: bool) -> None:
    from qa_gen.core.jira_client import JiraClient
    from qa_gen.core.jira_writer import create_subtasks
    jira = JiraClient(settings.JIRA_BASE_URL, settings.JIRA_EMAIL, settings.JIRA_API_TOKEN)
    create_subtasks(story_id, test_cases, jira, no_confirm)


def _edit_loop(
    test_cases: list[TestCase],
    story_id: str,
    gherkin: str,
) -> list[TestCase]:
    import os
    from qa_gen.core import gherkin_parser

    editor = os.environ.get("EDITOR", "notepad" if sys.platform == "win32" else "vi")

    while True:
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".feature", delete=False, encoding="utf-8"
            ) as f:
                f.write(gherkin)
                tmp = f.name

            import subprocess
            subprocess.run([editor, tmp], check=False)

            edited = Path(tmp).read_text(encoding="utf-8")
            errors = gherkin_parser.validate_gherkin(edited)
            if errors:
                typer.echo(f"Gherkin validation errors: {errors}", err=True)
                if not display.confirm("Re-open editor to fix?"):
                    return test_cases
                gherkin = edited
                continue

            return gherkin_parser.parse_gherkin_to_test_cases(edited, story_id)
        except KeyboardInterrupt:
            return test_cases
        finally:
            try:
                os.unlink(tmp)
            except Exception:
                pass
