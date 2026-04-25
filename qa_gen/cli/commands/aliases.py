from pathlib import Path
from typing import Optional

import typer
import yaml

from qa_gen.cli import display
from qa_gen.config.settings import load_settings

aliases_app = typer.Typer(help="Manage QA vocabulary aliases")


def _kb_path() -> Path:
    return load_settings().KB_PATH


def _load_aliases(kb_path: Path) -> dict:
    path = kb_path / "aliases.yaml"
    if not path.exists():
        return {"components": {}, "forms": {}}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        "components": data.get("components") or {},
        "forms": data.get("forms") or {},
    }


def _save_aliases(kb_path: Path, aliases: dict) -> None:
    path = kb_path / "aliases.yaml"
    path.write_text(
        yaml.dump(aliases, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


def _find_phrase(aliases: dict, normalized: str) -> tuple[str | None, str | None]:
    """Return (target_id, group) where phrase already exists, or (None, None)."""
    for comp_id, phrases in aliases["components"].items():
        if normalized in [p.lower() for p in (phrases or [])]:
            return comp_id, "components"
    for form_id, phrases in aliases["forms"].items():
        if normalized in [p.lower() for p in (phrases or [])]:
            return form_id, "forms"
    return None, None


@aliases_app.command("add")
def add_alias(
    phrase: str = typer.Argument(..., help="Plain-language phrase"),
    maps_to: str = typer.Option(..., "--maps-to", help="form_id or component_id"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing alias"),
) -> None:
    kb_path = _kb_path()
    normalized = phrase.lower().strip()
    aliases = _load_aliases(kb_path)

    existing_id, _ = _find_phrase(aliases, normalized)
    if existing_id and existing_id != maps_to and not force:
        typer.echo(
            f"Alias '{normalized}' already maps to '{existing_id}'. Use --force to overwrite.",
            err=True,
        )
        raise typer.Exit(1)

    # Determine target_type from local files
    if (kb_path / "forms" / f"{maps_to}.yaml").exists():
        group = "forms"
        target_type = "form"
    elif (kb_path / "components" / f"{maps_to}.yaml").exists():
        group = "components"
        target_type = "component"
    else:
        typer.echo(f"no form or component found with id: {maps_to}", err=True)
        raise typer.Exit(1)

    # Remove old entry if overwriting a different target
    if existing_id and existing_id != maps_to:
        _remove_phrase(aliases, normalized)

    if maps_to not in aliases[group]:
        aliases[group][maps_to] = []
    if normalized not in [p.lower() for p in aliases[group][maps_to]]:
        aliases[group][maps_to].append(normalized)

    _save_aliases(kb_path, aliases)
    typer.echo(f"Alias '{normalized}' → '{maps_to}' ({target_type}) saved.")


def _remove_phrase(aliases: dict, normalized: str) -> bool:
    for group in ("components", "forms"):
        for target_id, phrases in aliases[group].items():
            if normalized in [p.lower() for p in (phrases or [])]:
                aliases[group][target_id] = [p for p in phrases if p.lower() != normalized]
                return True
    return False


@aliases_app.command("list")
def list_aliases(
    component: Optional[str] = typer.Option(None, "--component", help="Filter by component_id"),
    form: Optional[str] = typer.Option(None, "--form", help="Filter by form_id"),
) -> None:
    kb_path = _kb_path()
    aliases = _load_aliases(kb_path)
    rows = []

    if component:
        for phrase in (aliases["components"].get(component) or []):
            rows.append([phrase, component, "component"])
    elif form:
        for phrase in (aliases["forms"].get(form) or []):
            rows.append([phrase, form, "form"])
    else:
        for comp_id, phrases in aliases["components"].items():
            for phrase in (phrases or []):
                rows.append([phrase, comp_id, "component"])
        for form_id, phrases in aliases["forms"].items():
            for phrase in (phrases or []):
                rows.append([phrase, form_id, "form"])

    if not rows:
        typer.echo("No aliases found.")
        return
    display.show_table(["phrase", "target_id", "target_type"], rows)


@aliases_app.command("remove")
def remove_alias(phrase: str = typer.Argument(...)) -> None:
    kb_path = _kb_path()
    normalized = phrase.lower().strip()
    aliases = _load_aliases(kb_path)

    if not _remove_phrase(aliases, normalized):
        typer.echo(f"alias not found: '{normalized}'", err=True)
        raise typer.Exit(1)

    _save_aliases(kb_path, aliases)
    typer.echo(f"Alias '{normalized}' removed.")


# V2: aliases were stored in Supabase aliases table (shared across team, auto-learned from vector matches)
# See kb/supabase_client.py for upsert_alias, get_alias, list_aliases, delete_alias
