from pathlib import Path

import typer
import yaml

from qa_gen.cli import display
from qa_gen.config.settings import load_settings
from qa_gen.models.component import Component

components_app = typer.Typer(help="Manage component knowledge base entries")


def _kb_path() -> Path:
    return load_settings().KB_PATH


@components_app.command("list")
def list_components() -> None:
    kb_path = _kb_path()
    comps_dir = kb_path / "components"
    if not comps_dir.exists():
        typer.echo(f"Components directory not found: {comps_dir}", err=True)
        typer.echo(f"Create {comps_dir}/ and add YAML files.")
        return
    rows = []
    for yaml_file in sorted(comps_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            comp = Component.model_validate(data)
            rows.append([comp.id, comp.label, ", ".join(comp.forms or [])])
        except Exception as e:
            rows.append([yaml_file.stem, f"(error: {e})", ""])
    if not rows:
        typer.echo("No components in KB.")
        return
    display.show_table(["component_id", "label", "forms"], rows)


@components_app.command("show")
def show_component(component_id: str = typer.Argument(...)) -> None:
    kb_path = _kb_path()
    path = kb_path / "components" / f"{component_id}.yaml"
    if not path.exists():
        typer.echo(f"Component '{component_id}' not found in {kb_path}/components/", err=True)
        raise typer.Exit(3)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        comp = Component.model_validate(data)
    except Exception as e:
        typer.echo(f"error reading component: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(yaml.dump(comp.model_dump(exclude_none=True), allow_unicode=True, sort_keys=False))


# V2: components add — validates, embeds via Voyage AI, upserts to Supabase
# Restore when upgrading to v2 (also restore _clients() helper and imports):
#
# from typing import Annotated
# from qa_gen.kb import supabase_client as sb
# from qa_gen.kb.embedding import EmbeddingClient
#
# def _clients():
#     settings = load_settings()
#     client = sb.create_supabase_client(settings)
#     embedding = EmbeddingClient(settings.VOYAGE_API_KEY)
#     return settings, client, embedding
#
# @components_app.command("add")
# def add_component(
#     component_id: str = typer.Argument(...),
#     file: Annotated[Path, typer.Option("--file", exists=True, readable=True)] = ...,
# ) -> None:
#     settings, client, embedding = _clients()
#     raw = file.read_text(encoding="utf-8")
#     try:
#         data = yaml.safe_load(raw)
#     except yaml.YAMLError as e:
#         typer.echo(f"YAML parse error: {e}", err=True)
#         raise typer.Exit(1)
#     yaml_id = data.get("id", "")
#     if yaml_id != component_id:
#         typer.echo(f"ID mismatch: CLI arg '{component_id}' != YAML id '{yaml_id}'", err=True)
#         raise typer.Exit(1)
#     try:
#         comp = Component.model_validate(data)
#     except Exception as e:
#         typer.echo(f"Schema validation error: {e}", err=True)
#         raise typer.Exit(1)
#     with display.spinner(f"Embedding {component_id}..."):
#         embeddings = embedding.embed_document([raw])
#     record = {
#         "component_id": comp.id,
#         "label": comp.label,
#         "description": comp.description,
#         "interaction_steps": comp.interaction_steps,
#         "save_behavior_notes": comp.save_behavior_notes,
#         "forms": comp.forms,
#         "content": raw,
#         "embedding": embeddings[0],
#     }
#     sb.upsert_component(client, record)
#     typer.echo(f"Component '{component_id}' added to KB.")
