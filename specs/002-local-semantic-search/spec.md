# Feature Specification: Local Semantic Search for KB Resolution

**Feature Branch**: `002-local-semantic-search`  
**Created**: 2026-04-26  
**Status**: Draft  
**Input**: User description: "Add local YAML cosine semantic search fallback for form and component resolution"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Resolve Form from Natural Language Label (Priority: P1)

A QA tester runs `qa-gen tests PROJ-1042`. The JIRA story has a label such as "New Patient Intake Form" — a natural description that doesn't match any exact KB entry ID or saved alias. Today this drops the tester into an interactive prompt listing all forms. With this feature, the system automatically finds the correct form by meaning and proceeds with generation without any manual input.

**Why this priority**: This is the core value. Every unrecognized label currently interrupts the tester. Fixing this makes the tool usable across vocabulary differences without constant alias maintenance.

**Independent Test**: Can be fully tested by running `qa-gen tests` with a JIRA story whose label has no exact ID match and no alias — system should resolve and generate without prompting.

**Acceptance Scenarios**:

1. **Given** a KB with a form "Patient Registration Form" and no alias for "New Patient Intake", **When** the tester runs `qa-gen tests PROJ-1042` and the JIRA label is "New Patient Intake", **Then** the system resolves to "Patient Registration Form" and continues generation without prompting
2. **Given** the same setup, **When** the system resolves via semantic search, **Then** the CLI output shows a line in the format `Resolved 'New Patient Intake' → 'Patient Registration Form' (score: 0.XX)`
3. **Given** a label that has no close match in the KB (e.g., "Billing Invoice" when no billing form exists), **When** the system searches, **Then** the system falls through to the interactive prompt as before

---

### User Story 2 - Component Resolution from Partial or Informal Reference (Priority: P2)

A QA tester's JIRA story references a UI component using informal language (e.g., "date selector" instead of the KB entry "date_picker"). Today the component is skipped with a warning. With this feature, the system matches it by meaning and includes it in the generated test context.

**Why this priority**: Missing components degrade test quality. Forms often reference multiple components; skipping any reduces accuracy of the generated Gherkin.

**Independent Test**: Can be tested by referencing a component by an informal name in a JIRA story — generated test output should include that component's behavior context.

**Acceptance Scenarios**:

1. **Given** a component "Date Picker" in the KB and no alias for "date selector", **When** the system resolves component references and encounters "date selector", **Then** it matches to "date_picker" and includes its context in generation
2. **Given** a component reference with no meaningful match in the KB, **When** the system searches, **Then** it skips the component with a warning as in v1

---

### User Story 3 - Automatic Index Maintenance (Priority: P3)

When a new form or component YAML is added to the KB, the tester does not need to run any indexing command. The next time `qa-gen tests` is run, the system detects the new file and includes it in search — only processing files that have changed.

**Why this priority**: Removes operational overhead. Any required manual step after adding a KB entry creates friction and errors.

**Independent Test**: Can be tested by adding a new form YAML, then immediately running `qa-gen tests` with a label matching that form — system should resolve it without any intermediate command.

**Acceptance Scenarios**:

1. **Given** a new form YAML added to the KB, **When** the tester runs `qa-gen tests` next, **Then** the system indexes the new entry and makes it available for search
2. **Given** a KB where no YAML files have changed, **When** `qa-gen tests` runs, **Then** no calls to the external search service are made for indexing — only if a query needs semantic resolution
3. **Given** one form YAML updated and 19 others unchanged, **When** the system runs, **Then** only the updated form is re-indexed

---

### User Story 4 - Graceful Fallback if sentence-transformers Unavailable (Priority: P4)

A tester who does not have `sentence-transformers` installed runs `qa-gen tests`. The tool behaves exactly as v1 — exact match, alias lookup, then interactive prompt. No error is raised; no functionality is broken.

**Why this priority**: New users should not hit a broken setup. The feature must be opt-in through configuration, not required.

**Independent Test**: Can be tested by running `qa-gen tests` with the API key unset — behavior must be identical to the current v1 flow.

**Acceptance Scenarios**:

1. **Given** `sentence-transformers` is not installed, **When** the tester runs `qa-gen tests`, **Then** the system skips semantic search silently and proceeds with exact match → alias → interactive prompt
2. **Given** `sentence-transformers` is installed but the model fails to load, **When** the query is made, **Then** the system prints a warning via Rich to stderr and falls back to the interactive prompt — generation is not blocked

---

### Edge Cases

- What happens when the KB has zero YAML files? — Nothing to index; all labels fall through to prompt.
- What happens when no project root can be found (no `knowledge_base/` or `.qa-gen/` in any parent directory)? — Exit with a non-zero code and a descriptive error message.
- What happens when `.qa-gen/search_index.json` is corrupt or unreadable? — System deletes it and rebuilds the full index silently; no warning shown to tester.
- What happens in CI (no TTY) when no match above threshold is found? — Exit non-zero, print unresolved label, print alias hint; no interactive prompt.
- What happens when two forms have very similar descriptions and both score above the threshold? — Highest scoring match wins; tester sees the resolved name and can correct with an alias.
- What happens when the tester adds an alias that conflicts with a semantic match? — Alias takes priority (alias lookup runs before semantic search).
- What happens when a YAML file is deleted from the KB? — Full directory scan on every run diffs current files against index keys; entry is pruned immediately and no longer appears as a candidate.
- What happens when two `qa-gen tests` processes write the index simultaneously (e.g., parallel CI jobs)? — Last write wins; no file locking is used; if concurrent writes produce a corrupt index, the system detects and rebuilds silently on next run per the existing corruption edge case.
- What happens when a full index rebuild is interrupted mid-way (process killed, model crash)? — Index is written to a temp file and atomically renamed to `.qa-gen/search_index.json` only on full success; an interrupted rebuild leaves the previous index intact, and the next run retries the full rebuild.
- What happens when the `sentence-transformers` model fails to load (after it is already cached)? — System prints the error via Rich to stderr, skips semantic search for this run, falls through to interactive prompt.
- What happens when the first-run model download fails (network error/timeout)? — System exits non-zero and prints `"Model download failed: {error}. Re-run when connected."` via Rich to stderr; no fallback to interactive prompt.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST attempt semantic matching of unresolved form labels against all known KB forms before presenting the tester with an interactive selection prompt
- **FR-002**: System MUST attempt semantic matching of unresolved component references against all known KB components before skipping with a warning
- **FR-003**: System MUST build a local search index by scanning `knowledge_base/forms/` and `knowledge_base/components/` automatically on the first run and on any subsequent run where KB files have changed — no manual command required
- **FR-004**: On every run, system MUST perform a full scan of `knowledge_base/forms/` and `knowledge_base/components/` to detect additions, modifications, and deletions. Index entries for files no longer present are pruned immediately. Only entries whose file mtime has changed **and** whose SHA-256 hash differs from the stored value are re-embedded; all others are reused unchanged. If the index `model` field differs from the current model name, the entire index is discarded and rebuilt — system MUST print `"Embedding model changed, rebuilding index…"` and show a CLI spinner until rebuild completes. All index writes (incremental updates and full rebuilds) MUST use an atomic write pattern: write to a temporary file in the same directory, then rename to `.qa-gen/search_index.json` on success; an interrupted write leaves the previous index intact
- **FR-005**: System MUST display a visible confirmation in the CLI output whenever a form or component is resolved via semantic search, in the format: `Resolved '{label}' → '{matched entry}' (score: {score:.2f})`
- **FR-006**: System MUST accept a semantic match only when its confidence score meets or exceeds a configurable minimum threshold; matches below threshold are discarded
- **FR-007**: System MUST allow the minimum confidence threshold to be adjusted via the `QA_GEN_SIMILARITY_THRESHOLD` environment variable without modifying any code
- **FR-008**: System MUST operate without any errors or degraded behavior when `sentence-transformers` is not installed, reverting fully to v1 resolution behavior
- **FR-009**: System MUST handle `sentence-transformers` model load or inference failures without blocking test generation — system prints a warning via Rich to stderr and falls through to interactive prompt
- **FR-010**: System MUST give alias-based matches priority over semantic matches; if an alias exists, the semantic search step is skipped for that label
- **FR-011**: When running in a non-interactive environment (no TTY) and no match above threshold is found, system MUST exit with a non-zero code, print the unresolved label name, and print a hint to add an alias — no interactive prompt is shown
- **FR-012**: On first run, when the `all-MiniLM-L6-v2` model is not yet cached, system MUST print a one-time message ("Downloading embedding model, first run only…") and show a CLI spinner until the download completes
- **FR-013**: On first run (when `.qa-gen/search_index.json` does not yet exist), system MUST automatically append `.qa-gen/search_index.json` to the project root's `.gitignore` file; if `.gitignore` does not exist, system MUST create it with that entry
- **FR-014**: If the first-run model download fails (network error, timeout, or any exception), system MUST exit non-zero and print via Rich to stderr: `"Model download failed: {error}. Re-run when connected."` — no fallback to interactive prompt in this scenario
- **FR-015**: When `QA_GEN_DEBUG=1` is set, system MUST print the top-3 semantic candidates and their scores to stderr via Rich after each semantic search query, in the format: `  [debug] candidates: '{entry1}' ({score1:.2f}), '{entry2}' ({score2:.2f}), '{entry3}' ({score3:.2f})` — this output appears before the FR-005 resolution confirmation line

### Key Entities

- **KB Entry**: A form or component definition in the knowledge base. The **filename (without `.yaml` extension) is the entry ID**. The YAML file contains a `name` field (required) and an optional `description` field. The `name` and `description` values combined are used as the embedding source for semantic matching; if `description` is absent, `name` alone is used with no warning emitted.
- **Search Index**: A local, per-project file (`.qa-gen/search_index.json`) containing a top-level `model` field (the embedding model name, e.g. `"all-MiniLM-L6-v2"`) and a mapping of each KB entry ID (filename without `.yaml`) to its precomputed embedding vector (derived from `name` + `description`), stored mtime, and SHA-256 content hash. Persists across runs; an entry is re-indexed when its mtime has changed **and** its SHA-256 hash differs from the stored value. If the stored `model` field differs from the current model name, the entire index is discarded and rebuilt.
- **Label**: Natural language text extracted from a JIRA story (story title, description, or label field) used to find a matching KB entry.
- **Match Result**: The outcome of a semantic search — a KB entry ID paired with a confidence score. Only returned if confidence meets the configured threshold.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Labels that semantically describe an existing KB form resolve correctly without a manual alias in 90% of test cases across a KB of 20 or more forms
- **SC-002**: No interactive prompt is shown to the tester for any label whose meaning closely matches a KB entry above the configured confidence threshold
- **SC-007**: The full semantic search step (sentence-transformers local inference + cosine similarity) completes within 2 seconds; a CLI spinner is shown if the call is in progress. This is a soft SLA target — no hard timeout or abort is applied; inference runs to completion regardless of duration
- **SC-003**: After a KB of 20 forms is fully indexed, subsequent `qa-gen tests` runs with no YAML file changes add zero index-update delay — only query-time calls occur
- **SC-004**: Absence of `sentence-transformers` produces behavior identical to v1 with no new errors or warnings beyond a single silent skip notice
- **SC-005**: Testers can confirm what form or component was resolved semantically from CLI output (format: `Resolved '{label}' → '{entry}' (score: {score:.2f})`) before reviewing the generated test cases, giving them signal to add an alias when the score is low
- **SC-006**: A KB update (add or modify one YAML) is reflected in search results on the very next `qa-gen tests` run with no manual steps

## Assumptions

- KB YAML files for forms are stored at `knowledge_base/forms/` and for components at `knowledge_base/components/` — both relative to the project root; no YAML format changes are required by this feature
- Embedding is performed locally via `sentence-transformers>=2.7,<3` (`all-MiniLM-L6-v2`); no API key or internet connection required at query time. The model (~80 MB) is downloaded once on first use and cached by the library
- Default confidence threshold (0.75) is appropriate for a KB of 10–50 entries; teams with very similar form names may need to tune it upward
- Each user maintains their own local search index stored at `.qa-gen/search_index.json` within the project root; the tool automatically appends `.qa-gen/search_index.json` to the project's `.gitignore` on first run (creates `.gitignore` if absent). Index sharing across a team is a v2 concern and is out of scope here
- Project root is determined by walking up from CWD until a directory containing `knowledge_base/` or `.qa-gen/` is found; if neither is found, the command exits with an error
- Internet connectivity is only required on the first run to download the `all-MiniLM-L6-v2` model; all subsequent indexing and query operations run fully offline
- Forms or components with near-identical descriptions may occasionally produce ambiguous matches — the tester confirmation message (FR-005) is the mitigation
- This feature does not add any new CLI commands; all behavior is automatic within the existing `qa-gen tests` flow

## Clarifications

### Session 2026-04-26

- Q: What text is used to generate the embedding per KB entry? → A: Name + description fields
- Q: Where is the local search index stored? → A: Per-project at `.qa-gen/search_index.json`
- Q: How is a changed KB file detected for re-indexing? → A: mtime as quick pre-check; SHA-256 content hash to confirm change
- Q: Max acceptable query-time latency for semantic search step? → A: ≤2 seconds; show CLI spinner if in progress
- Q: What format for the local search index file? → A: JSON (`.qa-gen/search_index.json`)
- Q: Which embedding model/provider for semantic search? → A: `sentence-transformers` (`all-MiniLM-L6-v2`) — local, offline, free
- Q: KB entry missing description field — embed name only or skip? → A: Embed name only, no warning
- Q: Corrupt/unreadable search_index.json at startup — rebuild or skip? → A: Delete and rebuild silently
- Q: CI/non-TTY mode with no match above threshold — prompt, skip, or fail? → A: Exit non-zero + print unresolved label + print alias hint
- Q: First-run model download UX — silent, message+spinner, or progress bar? → A: One-time message + spinner
- Q: What is the env var name for the configurable confidence threshold? → A: `QA_GEN_SIMILARITY_THRESHOLD`
- Q: Canonical term for the search feature — "semantic" or "meaning-based"? → A: `semantic` (use "semantic search" / "resolved semantically" everywhere; "meaning-based" retired)
- Q: Should tool auto-add `.qa-gen/search_index.json` to `.gitignore` or leave it to tester? → A: Auto-add on first run; create `.gitignore` if absent (FR-013)
- Q: Version constraint for `sentence-transformers` dependency? → A: `>=2.7,<3`
- Q: User-facing message when full index rebuild triggered by model name change? → A: Print `"Embedding model changed, rebuilding index…"` + CLI spinner (same pattern as FR-012)
- Q: Where are KB YAML files located in the project directory? → A: `knowledge_base/forms/` for forms, `knowledge_base/components/` for components (both relative to project root)
- Q: What logging mechanism for warnings and errors (e.g., FR-009, model load failure)? → A: Rich `console.print` to stderr — consistent with existing CLI output; no Python `logging` module
- Q: First-run model download failure — exit or fallback silently? → A: Exit non-zero, print `"Model download failed: {error}. Re-run when connected."` via Rich to stderr (FR-014)
- Q: Should confidence score appear in semantic resolution confirmation message (FR-005)? → A: Yes — format `Resolved '{label}' → '{entry}' (score: {score:.2f})`
- Q: Exact YAML field names for KB entry ID, name, description? → A: Filename (sans `.yaml`) = ID; YAML keys are `name` (required) and `description` (optional)
- Q: Should index store model name to trigger full rebuild on model change? → A: Yes — store model name in index; full rebuild if model name differs
- Q: SC-007 2-second target — hard timeout (abort+fallback) or soft SLA? → A: Soft SLA target; inference runs to completion with spinner shown; no timeout or abort applied
- Q: Mechanism for testers to inspect candidate scores for threshold tuning? → A: `QA_GEN_DEBUG=1` env var prints top-3 candidates + scores to stderr via Rich before FR-005 confirmation line (FR-015)
- Q: How is project root determined when running from a subdirectory? → A: Walk up from CWD until `knowledge_base/` or `.qa-gen/` found; error if neither found
- Q: Deletion detection — full scan every run or lazy/explicit rebuild? → A: Full directory scan every run; prune index entries for missing files immediately
- Q: Concurrent index writes from parallel processes — locking or last-write-wins? → A: Last write wins; no file locking; corruption triggers silent rebuild per existing edge case handling
- Q: Index rebuild interrupted mid-way — partial commit, preserve old, or atomic write? → A: Atomic write (write to temp file, rename on success); interrupted rebuild leaves previous index intact; next run retries full rebuild
