from pathlib import Path
from typing import Annotated

import typer
import yaml

from qa_gen.cli import display
from qa_gen.config.settings import load_settings
from qa_gen.models.form import Form

forms_app = typer.Typer(help="Manage form knowledge base entries")


def _kb_path() -> Path:
    return load_settings().KB_PATH


@forms_app.command("list")
def list_forms() -> None:
    kb_path = _kb_path()
    forms_dir = kb_path / "forms"
    if not forms_dir.exists():
        typer.echo(f"Forms directory not found: {forms_dir}", err=True)
        typer.echo(f"Create {forms_dir}/ and add YAML files.")
        return
    rows = []
    for yaml_file in sorted(forms_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            form = Form.model_validate(data)
            rows.append([form.form_id, form.display_name or "", form.save_behavior, form.module or ""])
        except Exception as e:
            rows.append([yaml_file.stem, f"(error: {e})", "", ""])
    if not rows:
        typer.echo("No forms in KB.")
        return
    display.show_table(["form_id", "display_name", "save_behavior", "module"], rows)


@forms_app.command("show")
def show_form(form_id: str = typer.Argument(...)) -> None:
    from qa_gen.core.form_resolver import load_form, flatten_inheritance
    kb_path = _kb_path()
    form = load_form(kb_path, form_id)
    if not form:
        typer.echo(f"Form '{form_id}' not found in {kb_path}/forms/", err=True)
        raise typer.Exit(3)
    form = flatten_inheritance(form, kb_path)
    typer.echo(yaml.dump(form.model_dump(exclude_none=True), allow_unicode=True, sort_keys=False))


@forms_app.command("validate")
def validate_form(
    form_id: str = typer.Argument(...),
    file: Annotated[Path, typer.Option("--file", exists=True, readable=True)] = ...,
) -> None:
    raw = file.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        typer.echo(f"YAML parse error: {e}", err=True)
        raise typer.Exit(1)

    yaml_form_id = data.get("form_id", "")
    if yaml_form_id != form_id:
        typer.echo(
            f"ID mismatch: CLI arg '{form_id}' != YAML form_id '{yaml_form_id}'",
            err=True,
        )
        raise typer.Exit(1)

    try:
        Form.model_validate(data)
        typer.echo(f"✓ Form '{form_id}' is valid.")
    except Exception as e:
        for err in getattr(e, "errors", lambda: [{"loc": ("?",), "msg": str(e)}])():
            key = ".".join(str(k) for k in err.get("loc", ("?",)))
            msg = err.get("msg", str(err))
            hint = "Check the data type and allowed values for this field."
            typer.echo(f"  ✗ {key}: {msg} — {hint}", err=True)
        raise typer.Exit(1)


# V2: forms add — validates, embeds via Voyage AI, upserts to Supabase
# Restore when upgrading to v2 (also restore _clients() helper and imports):
#
# from qa_gen.kb import supabase_client as sb
# from qa_gen.kb.embedding import EmbeddingClient
#
# def _clients():
#     settings = load_settings()
#     client = sb.create_supabase_client(settings)
#     embedding = EmbeddingClient(settings.VOYAGE_API_KEY)
#     return settings, client, embedding
#
# @forms_app.command("add")
# def add_form(
#     form_id: str = typer.Argument(...),
#     file: Annotated[Path, typer.Option("--file", exists=True, readable=True)] = ...,
# ) -> None:
#     settings, client, embedding = _clients()
#     raw = file.read_text(encoding="utf-8")
#     try:
#         data = yaml.safe_load(raw)
#     except yaml.YAMLError as e:
#         typer.echo(f"YAML parse error: {e}", err=True)
#         raise typer.Exit(1)
#     yaml_form_id = data.get("form_id", "")
#     if yaml_form_id != form_id:
#         typer.echo(f"ID mismatch: CLI arg '{form_id}' != YAML form_id '{yaml_form_id}'", err=True)
#         raise typer.Exit(1)
#     try:
#         form = Form.model_validate(data)
#     except Exception as e:
#         typer.echo(f"Schema validation error: {e}", err=True)
#         raise typer.Exit(1)
#     if form.extends:
#         parent = sb.get_form(client, form.extends)
#         if not parent:
#             typer.echo(f"Parent form '{form.extends}' not found in KB — add it first", err=True)
#             raise typer.Exit(3)
#     with display.spinner(f"Embedding {form_id}..."):
#         embeddings = embedding.embed_document([raw])
#     record = {
#         "form_id": form.form_id,
#         "display_name": form.display_name,
#         "module": form.module,
#         "save_behavior": form.save_behavior,
#         "save_trigger": form.save_trigger,
#         "parent_form_id": form.extends,
#         "content": raw,
#         "embedding": embeddings[0],
#     }
#     sb.upsert_form(client, record)
#     typer.echo(f"Form '{form_id}' added to KB.")
