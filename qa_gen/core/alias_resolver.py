from pathlib import Path

import yaml


class AliasResolver:
    def __init__(self, kb_path: Path) -> None:
        self._kb_path = kb_path
        self._aliases = self._load()

    def _load(self) -> dict:
        path = self._kb_path / "aliases.yaml"
        if not path.exists():
            return {"components": {}, "forms": {}}
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return {
            "components": data.get("components") or {},
            "forms": data.get("forms") or {},
        }

    def resolve(self, phrase: str, target_type: str | None = None) -> tuple[str | None, str | None]:
        """Return (target_id, target_type) or (None, None) if not found."""
        normalized = phrase.lower().strip()

        if target_type in (None, "component"):
            for comp_id, phrases in self._aliases.get("components", {}).items():
                if normalized in [p.lower() for p in (phrases or [])]:
                    return comp_id, "component"

        if target_type in (None, "form"):
            for form_id, phrases in self._aliases.get("forms", {}).items():
                if normalized in [p.lower() for p in (phrases or [])]:
                    return form_id, "form"

        return None, None

    # V2: semantic vector search via Supabase + Voyage AI embeddings
    # def resolve_with_embeddings(self, phrase, target_type, embedding_client, supabase_client):
    #     ...
