# Tasks: Local Semantic Search for KB Resolution

**Input**: Design documents from `/specs/002-local-semantic-search/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/semantic_search_engine.md, quickstart.md

**Tests**: Not requested in spec — test tasks omitted. See contracts/ for expected behaviour.

**Organization**: Grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Different file, no logical dependency on in-progress sibling tasks — can run in parallel
- **[Story]**: Which user story this implements (US1–US4 from spec.md)

---

## Phase 1: Setup

**Purpose**: Add optional dependency; create empty module skeletons so imports resolve.

- [X] T001 Add `sentence-transformers>=2.7,<3` under `dependencies` in pyproject.toml (optional install note in comment)
- [X] T002 [P] Create `qa_gen/kb/semantic_search.py` with `SemanticSearchEngine` class skeleton — `__init__`, `available` property, `update_index`, `search_form`, `search_component` all stub `...` bodies
- [X] T003 [P] Create `qa_gen/core/project_root.py` with `find_project_root(start: Path | None = None) -> Path` stub `...` body

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core engine infrastructure — MUST be complete before any user story can be implemented.

**⚠️ CRITICAL**: All user story phases depend on this phase being complete.

- [X] T004 [P] Implement `find_project_root()` in `qa_gen/core/project_root.py` — walk `Path.cwd()` upward until a dir containing `knowledge_base/` or `.qa-gen/` is found; `raise SystemExit(1)` with descriptive message via Rich to stderr if none found
- [X] T005 Implement `_load_index(index_path: Path) -> dict` in `qa_gen/kb/semantic_search.py` — read JSON; return `{"model": "", "entries": {}}` on missing file; silently delete + return empty dict on `json.JSONDecodeError` or missing required fields
- [X] T006 Implement `_save_index(index_path: Path, data: dict) -> None` in `qa_gen/kb/semantic_search.py` — create `index_path.parent` dir if absent; write to `index_path.parent / (index_path.name + ".tmp")`, then `Path.rename()` to `index_path` on success (atomic write)
- [X] T007 Implement `_compute_sha256(path: Path) -> str` and `_file_changed(path: Path, stored_mtime: float, stored_sha256: str) -> bool` helpers in `qa_gen/kb/semantic_search.py` — mtime pre-check first (fast path), SHA-256 read only when mtime differs
- [X] T008 Implement `SemanticSearchEngine.__init__(kb_path, index_path, threshold)` in `qa_gen/kb/semantic_search.py` — first line: `self._first_run = not index_path.exists()` (before any I/O — I3/I4 fix); then `try: from sentence_transformers import SentenceTransformer` → `ImportError` sets `self._available = False`; success loads model, sets `self._available = True`; then `self._index = _load_index(index_path)` (loaded once here — I1 fix); store `self._kb_path`, `self._index_path`, `self._threshold`, `self._model`
- [X] T009 Implement `update_index()` core loop in `qa_gen/kb/semantic_search.py` — if not available return immediately; use `self._index` (loaded by `__init__`, no second `_load_index()` call — I1 fix); if `self._index["model"] != MODEL_NAME` discard entries (`self._index = {"model": MODEL_NAME, "entries": {}}`); full-scan `self._kb_path/forms/*.yaml` and `self._kb_path/components/*.yaml`; prune index entries whose source file no longer exists; for each file call `_file_changed()` → re-embed if changed, reuse stored embedding otherwise; set `dirty` flag; if dirty call `_save_index()` and keep `self._index` in sync
- [X] T010 Implement `_cosine_search(query: str, entry_type: str, top_n: int = 3) -> list[tuple[str, float]]` in `qa_gen/kb/semantic_search.py` — wrap `self._model.encode(query)` in `try/except Exception as e`: on exception print warning via `err_console` to stderr, set `self._available = False`, return `[]` (C1 fix — covers FR-009 inference failures: CUDA OOM, corrupted model, etc.); on success compute `dot(q, v) / (norm(q) * norm(v))` for each entry in `self._index["entries"]` matching `entry_type`, return top-N `(entry_id, score)` sorted descending

**Checkpoint**: `SemanticSearchEngine` is instantiable; `update_index()` runs; `_cosine_search()` returns scores. No user-visible output yet.

---

## Phase 3: User Story 1 — Form Label Resolution (Priority: P1) 🎯 MVP

**Goal**: Unresolved JIRA form labels match KB forms via cosine similarity; tester sees confirmation; CI fails with alias hint when no match found.

**Independent Test**: Run `qa-gen tests PROJ-XXXX` where JIRA label has no exact match and no alias but semantically matches a KB form — system resolves and generates without prompting.

### Implementation

- [X] T011 [US1] Implement `search_form(label: str) -> tuple[str, float] | None` in `qa_gen/kb/semantic_search.py` — call `_cosine_search(label, "form")`; return top result only if `score >= self._threshold`; return `None` otherwise (U3 fix: `self._threshold` not `self.threshold`)
- [X] T012 [US1] Add FR-015 debug output to `search_form()` in `qa_gen/kb/semantic_search.py` — when `os.environ.get("QA_GEN_DEBUG") == "1"` print top-3 candidates to stderr via `err_console` in format `  [debug] candidates: '{e1}' ({s1:.2f}), '{e2}' ({s2:.2f}), '{e3}' ({s3:.2f})`
- [X] T013 [US1] Modify `resolve_form()` in `qa_gen/core/form_resolver.py` — add `from qa_gen.cli.display import err_console` import (U5 fix); add `semantic_engine=None` param; after alias-miss (Step 2), add Step 3: for each unmatched label call `semantic_engine.search_form(label)` if engine provided; on hit print FR-005 confirmation `Resolved '{label}' → '{form_id}' (score: {score:.2f})` via `err_console` (stderr — I2 fix: consistent with existing resolver output pattern) and load+return the form
- [X] T014 [US1] Add FR-011 non-TTY exit to `resolve_form()` in `qa_gen/core/form_resolver.py` — after all three steps miss and `not sys.stdin.isatty()`: print unresolved label to stderr, print alias hint to stderr, `raise SystemExit(1)`; only fall through to interactive prompt when TTY is present
- [X] T015 [US1] Wire `SemanticSearchEngine` into `orchestrator.run()` in `qa_gen/core/orchestrator.py` — `from qa_gen.kb.semantic_search import SemanticSearchEngine`; `from qa_gen.core.project_root import find_project_root`; derive `index_path = find_project_root() / ".qa-gen" / "search_index.json"`; read `threshold = float(os.environ.get("QA_GEN_SIMILARITY_THRESHOLD", "0.75"))`; instantiate engine; call `engine.update_index()` before form resolution; pass `semantic_engine=engine` to `form_resolver.resolve_form()`

**Checkpoint**: `qa-gen tests` with unresolved form label now resolves semantically and prints `Resolved '...' → '...' (score: ...)`.

---

## Phase 4: User Story 2 — Component Resolution (Priority: P2)

**Goal**: Informal component references in form fields match KB components via cosine similarity.

**Independent Test**: Reference a component by informal name (e.g., "date selector") in a JIRA story — generated test output includes that component's behavior context without a manual alias.

### Implementation

- [X] T016 [US2] Implement `search_component(reference: str) -> tuple[str, float] | None` in `qa_gen/kb/semantic_search.py` — call `_cosine_search(reference, "component")`; return top result only if `score >= self._threshold`; return `None` otherwise (U3 fix: `self._threshold` not `self.threshold`)
- [X] T017 [US2] Add FR-015 debug output to `search_component()` in `qa_gen/kb/semantic_search.py` — same `QA_GEN_DEBUG=1` stderr format as search_form debug (top-3 candidates + scores)
- [X] T018 [US2] Modify `resolve_components()` in `qa_gen/core/component_resolver.py` — add `from qa_gen.cli.display import err_console` import; add `semantic_engine=None` param; after alias miss (existing `print warning` path), before skip-warning: call `semantic_engine.search_component(field.component)` if engine provided; on hit print FR-005 confirmation `Resolved '{field.component}' → '{comp_id}' (score: {score:.2f})` via `err_console` (stderr — U4 fix: matches T013 channel and format) and load+add component; only print skip-warning when semantic also misses
- [X] T019 [US2] Pass `semantic_engine=engine` to `comp_res.resolve_components()` in `qa_gen/core/orchestrator.py`

**Checkpoint**: Informal component references now resolve semantically with confirmation output.

---

## Phase 5: User Story 3 — Automatic Index Maintenance (Priority: P3)

**Goal**: New or modified KB YAML files are reflected on the next `qa-gen tests` run with no manual step; first-run experience shows progress; index writes are atomic.

**Independent Test**: Add a new form YAML to `knowledge_base/forms/`, run `qa-gen tests` with a matching label — system resolves without any intermediate command.

**Note**: Core incremental-update logic (scan, prune, re-embed, atomic write) is delivered by T009 in Phase 2. This phase adds the user-facing experience (messages, spinners, gitignore).

### Implementation

- [X] T020 [US3] Add FR-012 first-run message + spinner to `update_index()` in `qa_gen/kb/semantic_search.py` — at start of `update_index()`, when `self._first_run` is True wrap the entire rebuild in a Rich `spinner` showing `"Downloading embedding model, first run only…"` (I3 fix: first-run detection stays in `__init__` via `self._first_run`; spinner lives in `update_index()` where the actual rebuild work runs)
- [X] T021 [US3] Add FR-004 model-change message + spinner to `update_index()` in `qa_gen/kb/semantic_search.py` — when `self._index["model"] != MODEL_NAME` print `"Embedding model changed, rebuilding index…"` and show spinner for the duration of the rebuild (I7 fix: `self._index` not bare `index`)
- [X] T022 [US3] Implement FR-013 first-run `.gitignore` management in `update_index()` in `qa_gen/kb/semantic_search.py` — when `self._first_run` is True: derive project root as `self._index_path.parent.parent`; read `project_root / ".gitignore"` (create if absent); append `.qa-gen/search_index.json` if not already present; write back (U1 fix: project_root = index_path.parent.parent; I3 fix: use self._first_run flag)
- [X] T023 [US3] Implement FR-014 model download failure exit in `SemanticSearchEngine.__init__()` in `qa_gen/kb/semantic_search.py` — use two separate except clauses after the `ImportError` guard: first `except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, urllib.error.URLError, TimeoutError) as e` → print `"Model download failed: {e}. Re-run when connected."` to stderr via `err_console`, `raise SystemExit(1)`; second `except Exception as e` → routes to T024 (I6 fix: exception-type routing; works correctly even when HuggingFace cache is cleared on non-first-run; `requests` is a transitive dep of sentence-transformers, always available)

**Checkpoint**: First-run shows download spinner; model changes show rebuild message; `.gitignore` updated automatically; interrupted downloads exit cleanly.

---

## Phase 6: User Story 4 — Graceful Fallback (Priority: P4)

**Goal**: Missing or broken `sentence-transformers` install produces v1 behavior with no new errors.

**Independent Test**: Run `qa-gen tests` with `sentence-transformers` not installed — behavior identical to v1 (exact match → alias → interactive prompt), no import errors raised.

### Implementation

- [X] T024 [US4] Add model load failure handling to `SemanticSearchEngine.__init__()` in `qa_gen/kb/semantic_search.py` — in the `except Exception as e` clause (second except, after T023's network-error clause): print warning `"Semantic search unavailable: {e}"` via `err_console`, set `self._available = False`, do not raise — generation continues via interactive prompt; covers corrupted cache, missing model files, incompatible versions, and any non-network load failure (I6 fix: no self._first_run needed; exception type alone determines routing)

**Checkpoint**: All four user stories functional. `qa-gen tests` works with or without `sentence-transformers`.

---

## Final Phase: Polish & Cross-Cutting Concerns

- [X] T025 [P] Add `sentence-transformers>=2.7,<3` to `environment.yml` under `pip:` block as optional dep comment
- [X] T026 [P] Run `ruff check qa_gen/kb/semantic_search.py qa_gen/core/project_root.py qa_gen/core/form_resolver.py qa_gen/core/component_resolver.py qa_gen/core/orchestrator.py` and fix any lint errors (line length, import order, unused imports)
- [X] T027 Update `CLAUDE.md` project structure section to list `qa_gen/kb/semantic_search.py` and `qa_gen/core/project_root.py` as new modules

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (T002, T003 skeletons must exist) — **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Phase 2 complete
- **US2 (Phase 4)**: Depends on Phase 2 complete; independent of US1
- **US3 (Phase 5)**: Depends on Phase 2 complete; independent of US1/US2 (but practically delivered after US1 since update_index wiring is in T015)
- **US4 (Phase 6)**: Depends on Phase 2 complete (specifically T008 __init__ skeleton)
- **Polish (Final)**: Depends on all story phases complete

### User Story Dependencies

- **US1 (P1)**: After Phase 2 — no dependency on US2/US3/US4
- **US2 (P2)**: After Phase 2 — no dependency on US1, US3, US4
- **US3 (P3)**: After Phase 2 — logically builds on US1's orchestrator wiring (T015); practially run after US1
- **US4 (P4)**: After Phase 2 (T008) — a single task modifying __init__, runnable any time after Phase 2

### Within Each Phase

- T002, T003: parallel (different files)
- T004: parallel with T005–T010 (different file: project_root.py vs semantic_search.py)
- T005 → T006 → T007 → T008 → T009 → T010: sequential (same file, logical dependency)
- T011 → T012 → T013 → T014 → T015: sequential (T011 must exist before callers are written)
- T016 → T017 → T018 → T019: sequential (T016 must exist before component_resolver caller)
- T021 depends on T009 (adds message+spinner to update_index model-mismatch path written in T009)
- T023 and T024 are sequential except clauses on the same try block: T023 writes the first clause (network errors → exit), T024 adds the second clause (all other exceptions → fallback)
- T025, T026: parallel (different files)

---

## Parallel Examples

### Phase 2 parallel opportunities
```
Parallel group A:
  Task: "Implement find_project_root() in qa_gen/core/project_root.py"  (T004)

Parallel group B (sequential within group):
  T005 → T006 → T007 → T008 → T009 → T010  (all qa_gen/kb/semantic_search.py + orchestrator.py)
```

### Phase 3 + Phase 4 (after Phase 2 complete)
```
Stream A — Form resolution (US1):
  T011 → T012 → T013 → T014 → T015

Stream B — Component resolution (US2):
  T016 → T017 → T018 → T019

Stream C — US4 single task:
  T024
```

### Polish
```
Parallel:
  T025  (environment.yml)
  T026  (ruff lint check)
  T027  (CLAUDE.md update)  — after T026 fixes applied
```

---

## Implementation Strategy

### MVP (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T010) — **CRITICAL, blocks everything**
3. Complete Phase 3: US1 (T011–T015)
4. **STOP and VALIDATE**: Run `qa-gen tests` with a label that has no exact match and no alias — confirm semantic resolution fires
5. Ship MVP — testers immediately benefit from form label resolution

### Incremental Delivery

1. Setup + Foundational → engine works, no user-visible effect
2. US1 (T011–T015) → form resolution semantic fallback active (MVP!)
3. US2 (T016–T019) → component resolution semantic fallback active
4. US3 (T020–T023) → first-run spinners, .gitignore, model-change rebuild message
5. US4 (T024) → hard model load failure degrades gracefully
6. Polish (T025–T027) → lint, env, docs clean

### Total Tasks

| Phase | Tasks | Count |
|-------|-------|-------|
| Setup | T001–T003 | 3 |
| Foundational | T004–T010 | 7 |
| US1 (P1) | T011–T015 | 5 |
| US2 (P2) | T016–T019 | 4 |
| US3 (P3) | T020–T023 | 4 |
| US4 (P4) | T024 | 1 |
| Polish | T025–T027 | 3 |
| **Total** | | **27** |

---

## Notes

- `[P]` tasks have no file conflicts with their siblings — safe to parallelize
- Each user story phase delivers a testable increment before the next begins
- `sentence-transformers` import only in `SemanticSearchEngine.__init__()` — no module-level import, so missing package never crashes other modules
- All stderr output via Rich `err_console = Console(stderr=True)` — consistent with existing display.py pattern
- Alias lookup always runs before semantic search (FR-010) — this is already enforced by the resolution step order in form_resolver.py and component_resolver.py
- Atomic write via temp-file rename ensures interrupted writes leave the previous index intact (FR-004)
