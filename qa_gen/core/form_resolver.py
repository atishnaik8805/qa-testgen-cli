import sys
from pathlib import Path

import yaml

from qa_gen.models.form import Form


def load_form(kb_path: Path, form_id: str) -> Form | None:
    path = kb_path / "forms" / f"{form_id}.yaml"
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return Form.model_validate(data)
    except Exception as e:
        print(f"error loading form '{form_id}': {e}", file=sys.stderr)
        return None


def flatten_inheritance(form: Form, kb_path: Path) -> Form:
    if not form.extends:
        return form
    parent = load_form(kb_path, form.extends)
    if not parent:
        print(
            f"warning: parent form '{form.extends}' not found in KB — inheritance skipped",
            file=sys.stderr,
        )
        return form
    parent = flatten_inheritance(parent, kb_path)
    merged_fields = {f.id: f for f in parent.fields}
    for f in form.fields:
        merged_fields[f.id] = f
    merged_data = parent.model_dump()
    merged_data.update({k: v for k, v in form.model_dump().items() if v is not None})
    merged_data["fields"] = list(merged_fields.values())
    return Form.model_validate(merged_data)


def resolve_form(
    story_data: dict,
    kb_path: Path,
    alias_resolver=None,
) -> tuple[Form, bool]:
    fields = story_data.get("fields", {})
    labels: list[str] = [lbl.get("name", "") for lbl in (fields.get("labels") or [])]

    forms_dir = kb_path / "forms"
    known = {f.stem for f in forms_dir.glob("*.yaml")} if forms_dir.exists() else set()

    # Step 1: exact label match against known form IDs
    matched = [l for l in labels if l and l in known]
    if matched:
        if len(matched) > 1:
            print(f"warning: multiple form labels found {matched}, using first", file=sys.stderr)
        form = load_form(kb_path, matched[0])
        if not form:
            print(f"Form '{matched[0]}' not in KB — add YAML to {forms_dir}/", file=sys.stderr)
            raise SystemExit(3)
        return flatten_inheritance(form, kb_path), True

    # Step 2: alias lookup on labels
    if alias_resolver:
        for label in labels:
            resolved_id, _ = alias_resolver.resolve(label.lower(), "form")
            if resolved_id and resolved_id in known:
                form = load_form(kb_path, resolved_id)
                if form:
                    return flatten_inheritance(form, kb_path), False

    # Step 3: prompt tester
    print("warning: could not auto-detect form from labels", file=sys.stderr)
    if not known:
        print(f"No forms in KB — add YAML files to {forms_dir}/", file=sys.stderr)
        raise SystemExit(3)

    print("Available forms:", file=sys.stderr)
    for f in sorted(known):
        print(f"  {f}", file=sys.stderr)

    chosen = input("Enter form_id to use: ").strip()
    form = load_form(kb_path, chosen)
    if not form:
        print(f"Form '{chosen}' not in KB", file=sys.stderr)
        raise SystemExit(3)
    return flatten_inheritance(form, kb_path), False

    # V2: resolve_form also accepted supabase_client + embedding_client for vector fallback
    # See kb/supabase_client.py match_forms() for the semantic search implementation
