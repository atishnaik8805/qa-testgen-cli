from __future__ import annotations

import hashlib
import json
import os
import urllib.error
from pathlib import Path
from typing import ClassVar

from qa_gen.cli.display import err_console

MODEL_NAME = "all-MiniLM-L6-v2"


def _load_index(index_path: Path) -> dict:
    if not index_path.exists():
        return {"model": "", "entries": {}}
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
        if not isinstance(data.get("model"), str) or not isinstance(data.get("entries"), dict):
            raise ValueError("missing required fields")
        for entry in data["entries"].values():
            if (
                not entry.get("embedding")
                or not isinstance(entry.get("mtime"), (int, float))
                or not entry.get("sha256")
            ):
                raise ValueError("invalid entry")
        return data
    except (json.JSONDecodeError, ValueError):
        try:
            index_path.unlink()
        except OSError:
            pass
        return {"model": "", "entries": {}}


def _save_index(index_path: Path, data: dict) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = index_path.parent / (index_path.name + ".tmp")
    tmp_path.write_text(json.dumps(data), encoding="utf-8")
    tmp_path.rename(index_path)


def _compute_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file_changed(path: Path, stored_mtime: float, stored_sha256: str) -> bool:
    current_mtime = path.stat().st_mtime
    if current_mtime == stored_mtime:
        return False
    return _compute_sha256(path) != stored_sha256


class SemanticSearchEngine:
    MODEL_NAME: ClassVar[str] = "all-MiniLM-L6-v2"
    DEFAULT_THRESHOLD: ClassVar[float] = 0.75

    def __init__(
        self,
        kb_path: Path,
        index_path: Path,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        self._first_run = not index_path.exists()
        self._kb_path = kb_path
        self._index_path = index_path
        self._threshold = threshold
        self._available = False
        self._model = None

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            self._index = _load_index(index_path)
            return

        import requests

        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(MODEL_NAME)
            self._available = True
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            urllib.error.URLError,
            TimeoutError,
        ) as e:
            err_console.print(f"Model download failed: {e}. Re-run when connected.")
            raise SystemExit(1)
        except Exception as e:
            err_console.print(f"Semantic search unavailable: {e}")
            self._model = None

        self._index = _load_index(index_path)

    @property
    def available(self) -> bool:
        return self._available

    def update_index(self) -> None:
        if not self._available:
            return

        import yaml
        from rich.live import Live
        from rich.spinner import Spinner

        model_changed = self._index["model"] != MODEL_NAME

        def _do_update() -> None:
            if model_changed:
                self._index = {"model": MODEL_NAME, "entries": {}}

            forms_dir = self._kb_path / "forms"
            comps_dir = self._kb_path / "components"
            current_files: dict[str, Path] = {}
            if forms_dir.exists():
                for p in forms_dir.glob("*.yaml"):
                    current_files[f"forms/{p.stem}"] = p
            if comps_dir.exists():
                for p in comps_dir.glob("*.yaml"):
                    current_files[f"components/{p.stem}"] = p

            dirty = False

            for key in [k for k in self._index["entries"] if k not in current_files]:
                del self._index["entries"][key]
                dirty = True

            for key, path in current_files.items():
                stored = self._index["entries"].get(key)
                if stored and not _file_changed(path, stored["mtime"], stored["sha256"]):
                    continue
                try:
                    data = yaml.safe_load(path.read_text(encoding="utf-8"))
                    name = data.get("name", path.stem)
                    desc = data.get("description", "")
                    text = f"{name} {desc}".strip() if desc else name
                except Exception:
                    text = path.stem
                embedding = self._model.encode(text).tolist()
                self._index["entries"][key] = {
                    "embedding": embedding,
                    "mtime": path.stat().st_mtime,
                    "sha256": _compute_sha256(path),
                }
                dirty = True

            if dirty:
                _save_index(self._index_path, self._index)

        if self._first_run:
            with Live(
                Spinner("dots", text="Downloading embedding model, first run only…"),
                refresh_per_second=10,
                console=err_console,
            ):
                _do_update()
        elif model_changed:
            err_console.print("Embedding model changed, rebuilding index…")
            with Live(
                Spinner("dots", text="Rebuilding index…"),
                refresh_per_second=10,
                console=err_console,
            ):
                _do_update()
        else:
            _do_update()

        if self._first_run:
            project_root = self._index_path.parent.parent
            gitignore_path = project_root / ".gitignore"
            entry = ".qa-gen/search_index.json"
            content = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
            if entry not in content:
                if content and not content.endswith("\n"):
                    content += "\n"
                content += f"{entry}\n"
                gitignore_path.write_text(content, encoding="utf-8")

    def _cosine_search(
        self, query: str, entry_type: str, top_n: int = 3
    ) -> list[tuple[str, float]]:
        import numpy as np

        try:
            q_vec = self._model.encode(query)
        except Exception as e:
            err_console.print(f"[warning] semantic encode failed: {e}")
            self._available = False
            return []

        prefix = f"{entry_type}s/"
        results: list[tuple[str, float]] = []
        for key, entry in self._index["entries"].items():
            if not key.startswith(prefix):
                continue
            e_vec = np.array(entry["embedding"])
            norm_product = float(np.linalg.norm(q_vec) * np.linalg.norm(e_vec))
            if norm_product == 0:
                continue
            score = float(np.dot(q_vec, e_vec) / norm_product)
            results.append((key[len(prefix) :], score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_n]

    def search_form(self, label: str) -> tuple[str, float] | None:
        if not self._available:
            return None
        candidates = self._cosine_search(label, "form")
        if os.environ.get("QA_GEN_DEBUG") == "1" and candidates:
            parts = ", ".join(f"'{e}' ({s:.2f})" for e, s in candidates)
            err_console.print(f"  [debug] candidates: {parts}")
        if candidates and candidates[0][1] >= self._threshold:
            return candidates[0]
        return None

    def search_component(self, reference: str) -> tuple[str, float] | None:
        if not self._available:
            return None
        candidates = self._cosine_search(reference, "component")
        if os.environ.get("QA_GEN_DEBUG") == "1" and candidates:
            parts = ", ".join(f"'{e}' ({s:.2f})" for e, s in candidates)
            err_console.print(f"  [debug] candidates: {parts}")
        if candidates and candidates[0][1] >= self._threshold:
            return candidates[0]
        return None
