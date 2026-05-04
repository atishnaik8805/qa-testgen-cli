# Contract: SemanticSearchEngine

**Module**: `qa_gen.kb.semantic_search`  
**Type**: Python class (internal interface; no new CLI commands)

## Purpose

Provides local semantic search over KB form and component entries using `sentence-transformers`. Manages the per-project search index at `.qa-gen/search_index.json`. Degrades gracefully to a no-op when `sentence-transformers` is not installed.

---

## Class: `SemanticSearchEngine`

```python
class SemanticSearchEngine:
    MODEL_NAME: ClassVar[str] = "all-MiniLM-L6-v2"
    DEFAULT_THRESHOLD: ClassVar[float] = 0.75

    def __init__(
        self,
        kb_path: Path,
        index_path: Path,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None: ...

    @property
    def available(self) -> bool:
        """True if sentence-transformers is installed and model loaded successfully."""
        ...

    def update_index(self) -> None:
        """
        Scan KB, update index for changed entries, prune deleted entries.
        Writes atomically only if changes were made.
        Shows Rich spinner during model download (first run) or full rebuild.
        No-op if self.available is False.
        """
        ...

    def search_form(self, label: str) -> tuple[str, float] | None:
        """
        Return (form_id, score) if cosine similarity >= threshold, else None.
        Prints debug candidates to stderr if QA_GEN_DEBUG=1.
        No-op (returns None) if self.available is False.
        """
        ...

    def search_component(self, reference: str) -> tuple[str, float] | None:
        """
        Return (component_id, score) if cosine similarity >= threshold, else None.
        Prints debug candidates to stderr if QA_GEN_DEBUG=1.
        No-op (returns None) if self.available is False.
        """
        ...
```

---

## Behaviour Contracts

### Availability

- `available` returns `True` iff `sentence-transformers` is installed AND the model loaded without error
- If `ImportError` on `from sentence_transformers import SentenceTransformer` → `available = False`, no error raised
- If model load raises any other exception → `available = False`, warning printed to stderr via Rich

### update_index

| Scenario | Behaviour |
|----------|-----------|
| `available` is False | Returns immediately (no-op) |
| Index file absent | Full build; show "Downloading…" spinner if model not cached; auto-update `.gitignore` |
| Index file present, model name matches | Incremental: prune deleted entries; re-embed only entries where mtime changed AND sha256 differs |
| Index file present, model name differs | Discard + full rebuild; print `"Embedding model changed, rebuilding index…"` + spinner |
| Index file corrupt / unreadable | Delete silently + full rebuild |
| Model download fails (network error) | Exit non-zero; print `"Model download failed: {error}. Re-run when connected."` to stderr; no fallback |
| Rebuild interrupted (process killed mid-write) | Atomic write (temp + rename); previous index remains intact; next run retries full rebuild |

### search_form / search_component

| Scenario | Behaviour |
|----------|-----------|
| `available` is False | Returns `None` |
| Index empty (no entries of the requested type) | Returns `None` |
| All scores below threshold | Returns `None` |
| Score >= threshold | Returns `(best_match_id, score)` for highest-scoring entry |
| Two entries tied at threshold | Returns either (implementation detail; stable sort preferred) |
| `QA_GEN_DEBUG=1` | Prints top-3 candidates + scores to stderr before returning |

### Cosine Similarity

- Computed as: `dot(query_vec, entry_vec) / (norm(query_vec) * norm(entry_vec))`
- Score range: `[-1.0, 1.0]`; in practice `[0.0, 1.0]` for sentence embeddings
- Default threshold: `0.75`; overridden via `QA_GEN_SIMILARITY_THRESHOLD` env var

---

## Module-Level Function: `find_project_root`

```python
# qa_gen/core/project_root.py

def find_project_root(start: Path | None = None) -> Path:
    """
    Walk up from `start` (default: Path.cwd()) until a directory containing
    `knowledge_base/` or `.qa-gen/` is found.
    Raises SystemExit(1) with descriptive message if none found.
    """
    ...
```

---

## Integration Points

### orchestrator.py additions

```python
from qa_gen.kb.semantic_search import SemanticSearchEngine
from qa_gen.core.project_root import find_project_root

# Inside orchestrator.run():
project_root = find_project_root()
index_path = project_root / ".qa-gen" / "search_index.json"
threshold = float(os.environ.get("QA_GEN_SIMILARITY_THRESHOLD", "0.75"))
engine = SemanticSearchEngine(kb_path, index_path, threshold)
engine.update_index()  # no-op if not available; shows spinner if needed
```

### form_resolver.py — resolve_form signature change

```python
def resolve_form(
    story_data: dict,
    kb_path: Path,
    alias_resolver=None,
    semantic_engine=None,   # NEW: SemanticSearchEngine | None
) -> tuple[Form, bool]:
    ...
    # Step 3 (NEW): semantic search — before interactive prompt
    if semantic_engine:
        for label in labels:
            result = semantic_engine.search_form(label)
            if result:
                form_id, score = result
                err_console.print(f"Resolved '{label}' → '{form_id}' (score: {score:.2f})")
                form = load_form(kb_path, form_id)
                if form:
                    return flatten_inheritance(form, kb_path), False
    ...
```

### component_resolver.py — resolve_components signature change

```python
def resolve_components(
    form: Form,
    kb_path: Path,
    alias_resolver=None,
    semantic_engine=None,   # NEW: SemanticSearchEngine | None
) -> list[Component]:
    ...
    # After alias miss, before skip-warning:
    if semantic_engine:
        result = semantic_engine.search_component(field.component)
        if result:
            comp_id, score = result
            err_console.print(f"Resolved '{field.component}' → '{comp_id}' (score: {score:.2f})")
            comp = load_component(kb_path, comp_id)
            if comp and comp_id not in seen:
                seen.add(comp_id)
                components.append(comp)
                continue
    ...
```

---

## Output Format

### Resolution confirmation (FR-005)

Printed to stdout via Rich console when semantic match succeeds:
```
Resolved 'New Patient Intake' → 'patient_registration_form' (score: 0.87)
```

### Debug candidates (FR-015, when QA_GEN_DEBUG=1)

Printed to stderr via Rich before resolution confirmation:
```
  [debug] candidates: 'patient_registration_form' (0.87), 'patient_discharge_form' (0.61), 'lab_results_form' (0.44)
```

### Non-TTY no-match exit (FR-011)

Printed to stderr via Rich:
```
Unresolved label: 'New Patient Intake'
Hint: add an alias in knowledge_base/aliases.yaml → forms section
```
Then `raise SystemExit(1)`.
