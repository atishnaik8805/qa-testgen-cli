# Quickstart: Local Semantic Search

## Install the optional dependency

```bash
pip install "sentence-transformers>=2.7,<3"
```

Without this, `qa-gen tests` works exactly as v1 (exact match → alias → interactive prompt). No errors are raised.

## First run

```bash
qa-gen tests PROJ-1042
```

On first run with `sentence-transformers` installed:
1. Model downloads once (~80 MB, cached by the library): spinner shown
2. KB is indexed: `knowledge_base/forms/*.yaml` and `knowledge_base/components/*.yaml` are embedded
3. `.qa-gen/search_index.json` is written atomically
4. `.qa-gen/search_index.json` is appended to `.gitignore` (file created if absent)

## Subsequent runs

No model download. Index is updated incrementally — only files whose SHA-256 has changed are re-embedded. Unchanged files reuse stored embeddings.

## When a label resolves semantically

CLI output includes a confirmation line:
```
Resolved 'New Patient Intake' → 'patient_registration_form' (score: 0.87)
```

If the score is unexpectedly low, add an alias to `knowledge_base/aliases.yaml` to make it exact and skip semantic search next time.

## Tuning the threshold

Default: `0.75`. Raise it if you get false positives (wrong form matched). Lower it if close matches are missed.

```bash
QA_GEN_SIMILARITY_THRESHOLD=0.85 qa-gen tests PROJ-1042
```

## Inspecting candidates

```bash
QA_GEN_DEBUG=1 qa-gen tests PROJ-1042
```

Prints top-3 candidates and their scores to stderr before each resolution confirmation:
```
  [debug] candidates: 'patient_registration_form' (0.87), 'patient_discharge_form' (0.61), 'lab_results_form' (0.44)
```

## CI / non-TTY environments

If no match above threshold is found in CI (no TTY), the command exits non-zero with the unresolved label and an alias hint — no interactive prompt is shown. Add an alias to fix.

## Fallback conditions

| Condition | Behaviour |
|-----------|-----------|
| `sentence-transformers` not installed | v1 behavior (exact → alias → prompt) |
| Model fails to load after install | Warning to stderr; falls through to prompt |
| Model download fails (first run) | Exit non-zero; print error; re-run when connected |
| `.qa-gen/search_index.json` corrupt | Deleted silently; full rebuild on this run |
| KB has zero YAML files | Nothing to index; all labels fall through to prompt |
| Project root not found | Exit non-zero with descriptive error |

## Adding KB entries

Just add a YAML file to `knowledge_base/forms/` or `knowledge_base/components/`. The next `qa-gen tests` run detects the new file and indexes it automatically.
