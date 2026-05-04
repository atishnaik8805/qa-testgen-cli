# Data Model: Local Semantic Search

## Entities

### SearchIndex (persisted as `.qa-gen/search_index.json`)

The per-project index file. Written atomically (temp file → rename). Deleted and rebuilt if corrupt or if `model` field differs from current model name.

```json
{
  "model": "all-MiniLM-L6-v2",
  "entries": {
    "forms/patient_registration_form": {
      "embedding": [0.023, -0.145, ...],
      "mtime": 1714012345.123,
      "sha256": "e3b0c44298fc1c14..."
    },
    "components/date_picker_v2": {
      "embedding": [0.087, 0.312, ...],
      "mtime": 1714012400.000,
      "sha256": "2cf24dba5fb0a30e..."
    }
  }
}
```

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `model` | `str` | Embedding model name (e.g., `"all-MiniLM-L6-v2"`). Full rebuild triggered if this differs from current model at load time |
| `entries` | `dict[str, IndexEntry]` | Map of namespaced entry key → IndexEntry. Key format: `"forms/{id}"` or `"components/{id}"` |

**IndexEntry fields**:

| Field | Type | Description |
|-------|------|-------------|
| `embedding` | `list[float]` | 384-dimensional embedding vector |
| `mtime` | `float` | `os.path.getmtime()` of source YAML at index time (used as pre-check) |
| `sha256` | `str` | SHA-256 hex digest of source YAML content (used to confirm change) |

**Key constraints**:
- `forms/{id}` entries come from `knowledge_base/forms/*.yaml`; `{id}` = filename without `.yaml`
- `components/{id}` entries come from `knowledge_base/components/*.yaml`; `{id}` = filename without `.yaml`
- Entries are pruned if their source file no longer exists (detected on every run via full dir scan)
- Entries are re-embedded only when both mtime AND sha256 differ from stored values
- If `model` field differs from current `MODEL_NAME`, entire index is discarded and rebuilt

---

### KBEntry (runtime only, not persisted)

Represents one YAML file from the KB, loaded during index update.

| Field | Type | Description |
|-------|------|-------------|
| `entry_id` | `str` | Filename without `.yaml` extension |
| `entry_type` | `Literal["form", "component"]` | Whether from `forms/` or `components/` |
| `text` | `str` | `name + " " + description` (or `name` alone if `description` absent) |
| `path` | `Path` | Absolute path to source YAML |

---

### MatchResult (runtime only, not persisted)

Returned by `SemanticSearchEngine.search_form()` and `search_component()`.

| Field | Type | Description |
|-------|------|-------------|
| `entry_id` | `str` | The matched KB entry ID (filename without `.yaml`) |
| `score` | `float` | Cosine similarity score in [0.0, 1.0] |

Returned only when `score >= threshold`. Returns `None` when no match above threshold.

---

## State Transitions

### Index Lifecycle

```
[No index file]
      │
      ▼ first run (update_index called)
[Building] ── model download fails ──► exit non-zero, print error
      │
      │ success
      ▼
[Index written atomically to .qa-gen/search_index.json]
[.gitignore updated to include entry]
      │
      ▼ subsequent runs
[Load existing index]
      ├─ model name mismatch ──► [Full rebuild] ──► [Index overwritten atomically]
      ├─ corrupt/unreadable   ──► [Silent delete] ──► [Full rebuild]
      └─ OK
           │
           ▼ full dir scan
      [Diff current files vs index keys]
           ├─ deleted files  ──► prune entry from index
           ├─ new files      ──► embed + add entry
           └─ changed files  ──► re-embed + update entry (mtime changed AND sha256 differs)
           │
           ▼
      [Atomic write if any changes; skip write if nothing changed]
```

---

## Validation Rules

- `model` field must be a non-empty string; if absent on load, treat as corrupt → full rebuild
- `entries` values must each have `embedding` (non-empty list of floats), `mtime` (float), and `sha256` (non-empty string); any missing field → treat whole index as corrupt → silent delete + full rebuild
- Entry key must match `^(forms|components)/[a-z][a-z0-9_]*$` (soft constraint; enforced by YAML filename conventions, not runtime validation)
- Threshold `QA_GEN_SIMILARITY_THRESHOLD` must parse as float in (0.0, 1.0]; if invalid, fall back to default 0.75 and print warning via Rich to stderr
