# Implementation Plan: Local Semantic Search for KB Resolution

**Branch**: `002-local-semantic-search` | **Date**: 2026-04-26 | **Spec**: specs/002-local-semantic-search/spec.md
**Input**: Feature specification from `/specs/002-local-semantic-search/spec.md`

## Summary

Add a local semantic search fallback to KB form and component resolution. After exact match and alias lookup fail, the system uses `sentence-transformers` (`all-MiniLM-L6-v2`) to match natural language labels against a per-project JSON index of KB entry embeddings. The index is maintained automatically on every `qa-gen tests` run: entries are re-embedded only when their SHA-256 hash changes; a model name change triggers a full rebuild. The feature is optional — missing `sentence-transformers` silently reverts to v1 behavior (exact → alias → interactive prompt).

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: `sentence-transformers>=2.7,<3` (new, optional), `numpy` (transitive via sentence-transformers), `pyyaml`, `pydantic`, `rich`, `typer`  
**Storage**: Local JSON file `.qa-gen/search_index.json` per project root; atomic write (temp file → rename on success)  
**Testing**: pytest — unit (mocked sentence-transformers) + integration (real model if installed)  
**Target Platform**: macOS/Linux/Windows local developer machine  
**Project Type**: CLI  
**Performance Goals**: Semantic search (inference + cosine similarity) ≤2s soft SLA; spinner shown during long operations  
**Constraints**: Fully offline after first-run model download (~80 MB); no API key required; `sentence-transformers` is optional (graceful fallback to v1); no new CLI commands added  
**Scale/Scope**: KB of 10–50 entries; linear scan of embedded vectors (no ANN index needed at this scale)

## Constitution Check

Constitution file is an unfilled template — no formal gates defined. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/002-local-semantic-search/
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output (/speckit.plan)
├── data-model.md        # Phase 1 output (/speckit.plan)
├── quickstart.md        # Phase 1 output (/speckit.plan)
├── contracts/           # Phase 1 output (/speckit.plan)
└── tasks.md             # Phase 2 output (/speckit.tasks — not yet created)
```

### Source Code

```text
qa_gen/
├── kb/
│   └── semantic_search.py       # NEW: SemanticSearchEngine + index management
├── core/
│   ├── project_root.py          # NEW: find_project_root() — walks CWD upward
│   ├── form_resolver.py         # MODIFY: add semantic step (Step 3) before interactive prompt
│   ├── component_resolver.py    # MODIFY: add semantic step before skip-warning
│   └── orchestrator.py          # MODIFY: instantiate SemanticSearchEngine, update index, pass to resolvers
└── config/
    └── settings.py              # MODIFY: read QA_GEN_SIMILARITY_THRESHOLD env var

tests/
├── unit/
│   ├── test_semantic_search.py       # Index R/W, change detection, cosine similarity, fallback
│   ├── test_form_resolver_semantic.py
│   └── test_component_resolver_semantic.py
└── integration/
    └── test_semantic_flow.py         # Full resolution flow with real sentence-transformers
```

**Structure Decision**: Single-project layout. New module `qa_gen/kb/semantic_search.py` placed alongside existing `embedding.py` (V2 Voyage AI, untouched). New utility `qa_gen/core/project_root.py` alongside other core utilities.
