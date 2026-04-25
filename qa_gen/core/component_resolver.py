import sys
from pathlib import Path

import yaml

from qa_gen.models.component import Component
from qa_gen.models.form import Form


def load_component(kb_path: Path, component_id: str) -> Component | None:
    path = kb_path / "components" / f"{component_id}.yaml"
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return Component.model_validate(data)
    except Exception as e:
        print(f"error loading component '{component_id}': {e}", file=sys.stderr)
        return None


def resolve_components(
    form: Form,
    kb_path: Path,
    alias_resolver=None,
) -> list[Component]:
    components: list[Component] = []
    seen: set[str] = set()

    for field in form.fields:
        if not field.component or field.component in seen:
            continue

        comp = load_component(kb_path, field.component)
        if comp:
            seen.add(field.component)
            components.append(comp)
            continue

        # Try alias resolution
        if alias_resolver:
            resolved_id, _ = alias_resolver.resolve(field.component, "component")
            if resolved_id and resolved_id not in seen:
                comp = load_component(kb_path, resolved_id)
                if comp:
                    seen.add(resolved_id)
                    components.append(comp)
                    continue

        print(
            f"component '{field.component}' on field '{field.id}' not found in KB — skipping",
            file=sys.stderr,
        )

    return components

    # V2: resolve_components also used supabase_client for DB lookups + vector fallback
    # See kb/supabase_client.py match_components() for the semantic search implementation
