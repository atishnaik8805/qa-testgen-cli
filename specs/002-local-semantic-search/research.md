# Research: Local Semantic Search for KB Resolution

## Embedding Model

**Decision**: `sentence-transformers` (`all-MiniLM-L6-v2`)  
**Rationale**: Fully local/offline after first download; free; 384-dim embeddings; strong performance on short text similarity (form names, component labels); ~80 MB cached by the library; `>=2.7,<3` version range is stable and widely tested  
**Alternatives considered**:
- `voyageai` — already in the project but requires API key and internet; rejected (offline requirement)
- `openai` embeddings — requires API key; rejected (offline requirement)
- BM25/TF-IDF — keyword-based, no semantic understanding; rejected (cannot handle vocabulary mismatch like "date selector" → "date_picker")
- `fastembed` — smaller footprint but less mature; rejected (all-MiniLM-L6-v2 better known/tested)

## Cosine Similarity

**Decision**: `numpy` dot product + L2 norm  
**Rationale**: `numpy` arrives as a transitive dependency of `sentence-transformers` — no new dependency added; sufficient for linear scan of ≤50 vectors  
**Alternatives considered**:
- `scipy.spatial.distance.cosine` — extra dep; rejected
- `sklearn.metrics.pairwise` — extra dep; rejected
- Pure Python — acceptable at 50 entries but slower; rejected in favor of numpy which is already present

## Index Storage Format

**Decision**: JSON at `.qa-gen/search_index.json`; atomic write (write to `.qa-gen/search_index.json.tmp`, rename on success)  
**Rationale**: Human-readable; no additional deps; sufficient for ≤50 entries (each ~384 floats ≈ 6 KB per entry → ~300 KB total for 50 entries); atomic write prevents corrupt reads on interrupted writes  
**Alternatives considered**:
- SQLite — overkill for this scale; rejected
- `pickle` — unsafe (arbitrary code execution on load); rejected
- `msgpack` — extra dep; rejected
- `numpy` `.npy` — not human-readable, harder to debug; rejected

## Change Detection

**Decision**: Two-stage — mtime as pre-check (O(1), no file read), SHA-256 of file content as confirmation (read file only if mtime changed)  
**Rationale**: mtime is fast and avoids reading files that haven't changed; SHA-256 confirms actual content change and guards against spurious mtime updates (e.g., `git checkout` touching mtimes without changing content)  
**Alternatives considered**:
- Hash-only — reads every file every run; rejected (unnecessary I/O)
- mtime-only — false positives after git checkout; rejected

## Project Root Detection

**Decision**: Walk from `Path.cwd()` upward to filesystem root; return first directory containing `knowledge_base/` or `.qa-gen/`; exit non-zero with descriptive error if none found  
**Rationale**: Spec requirement; allows running `qa-gen tests` from any subdirectory within the project  
**Alternatives considered**:
- `settings.KB_PATH.parent` — depends on user naming their KB dir `knowledge_base`; fragile; rejected
- Env var — requires user configuration; rejected (should be zero-config)

## Graceful Fallback Pattern

**Decision**: Try `from sentence_transformers import SentenceTransformer` at `SemanticSearchEngine.__init__` time; set `self._available = False` on `ImportError`; all public methods return `None` immediately when not available  
**Rationale**: Zero impact on users who haven't installed the optional dep; no changes to v1 resolution flow when unavailable  
**Alternatives considered**:
- `importlib.util.find_spec` at module load time — works but delays the check; rejected in favor of try/except at init
- Extras in pyproject.toml (`qa-gen[semantic]`) — better UX for pip installs but adds packaging complexity; deferred to v3

## CI / Non-TTY Behavior

**Decision**: When `not sys.stdin.isatty()` and no alias or semantic match above threshold is found, exit non-zero; print unresolved label; print alias hint — no interactive prompt  
**Rationale**: Spec FR-011; CI jobs must fail loudly when a label cannot be resolved  
**Alternatives considered**:
- Skip and continue with no form — silently degrades test quality; rejected

## First-Run .gitignore Management

**Decision**: On first run (`.qa-gen/search_index.json` does not yet exist), append `.qa-gen/search_index.json` to project root `.gitignore`; create `.gitignore` if absent  
**Rationale**: FR-013; prevents testers from accidentally committing the index (~300 KB, binary-ish floats) to version control  
**Implementation**: Check if entry already present before appending (idempotent); write using UTF-8; append only, never overwrite existing file

## Debug Inspection

**Decision**: `QA_GEN_DEBUG=1` env var triggers top-3 candidate print (to stderr via Rich) after each semantic query, before the FR-005 resolution confirmation  
**Rationale**: FR-015; lets testers inspect why a label resolved (or didn't) without modifying code; consistent with existing `QA_GEN_DEBUG` usage in debug_log.py  
**Format**: `  [debug] candidates: '{entry1}' ({score1:.2f}), '{entry2}' ({score2:.2f}), '{entry3}' ({score3:.2f})`

## Resolved Clarifications (all from spec/clarifications section)

| Item | Resolution |
|------|-----------|
| Embedding source per entry | `name` + `description` (space-joined); `description` absent → `name` only, no warning |
| Index location | `.qa-gen/search_index.json` relative to project root |
| Change detection mechanism | mtime pre-check + SHA-256 confirmation |
| Latency target | ≤2s soft SLA; spinner shown; no abort |
| Index format | JSON |
| Embedding model | `sentence-transformers` `all-MiniLM-L6-v2` |
| Missing description | Embed name only, no warning |
| Corrupt index | Delete and rebuild silently |
| Non-TTY no-match | Exit non-zero + print label + print alias hint |
| First-run download UX | One-time message + spinner |
| Threshold env var | `QA_GEN_SIMILARITY_THRESHOLD` (default 0.75) |
| Alias priority | Alias lookup before semantic search; semantic skipped if alias resolves |
| Auto .gitignore | Yes — FR-013; create if absent |
| sentence-transformers version | `>=2.7,<3` |
| Model change rebuild message | `"Embedding model changed, rebuilding index…"` + spinner |
| KB YAML locations | `knowledge_base/forms/` and `knowledge_base/components/` |
| Warning mechanism | Rich `console.print` to stderr; no Python `logging` |
| Download failure | Exit non-zero + print `"Model download failed: {error}. Re-run when connected."` |
| Score in confirmation | Yes — `Resolved '{label}' → '{entry}' (score: {score:.2f})` |
| YAML ID field | Filename (sans `.yaml`) = ID; YAML keys: `name` (required), `description` (optional) |
| Index stores model name | Yes — full rebuild if model name differs |
| SC-007 timeout | Soft SLA; no timeout or abort |
| Debug inspection | `QA_GEN_DEBUG=1` → top-3 to stderr before FR-005 line |
| Project root | Walk CWD up until `knowledge_base/` or `.qa-gen/` found |
| Deletion detection | Full dir scan every run; prune missing entries immediately |
| Concurrent writes | Last-write-wins; no locking; corruption triggers silent rebuild |
| Interrupted rebuild | Atomic write (temp + rename); interrupted leaves previous index intact |
