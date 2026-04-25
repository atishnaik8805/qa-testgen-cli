# Feature Specification: QA Test Case Generation CLI Tool

**Feature Branch**: `001-qa-testgen-cli`  
**Created**: 2026-04-24  
**Status**: Draft  
**Version**: v1 (flat-file KB). Requirements marked **v2 only** are implemented in code but inactive — see `.context/v1-migration-log.md`.  
**Input**: User description: "use the .context/qa-testgen-build-spec.md to understand what we want to build."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate Test Cases for a JIRA Story (Priority: P1)

A QA tester runs a single command with a JIRA story ID. The tool fetches the story, identifies which form it relates to, pulls the relevant UI behavior rules from the knowledge base, and outputs complete Gherkin-formatted test cases. The tester reviews the output and chooses to push it back to JIRA as subtasks or export it.

**Why this priority**: This is the core value proposition. Everything else enables or extends this flow.

**Independent Test**: Run `qa-gen tests PROJ-1042 --dry-run` against a story with a known form label — produces Gherkin test cases without any write-back.

**Acceptance Scenarios**:

1. **Given** a JIRA story with a `form_id` label and acceptance criteria exists, **When** the tester runs `qa-gen tests <STORY_ID>`, **Then** the tool displays Gherkin test cases that accurately reflect the form's save behavior and field interactions — no generic or hallucinated steps.
2. **Given** the story has all required fields, **When** test cases are displayed, **Then** the tester is prompted to push to JIRA, export, edit, or discard.
3. **Given** the tester selects "Push to JIRA", **When** the action completes, **Then** all generated test cases appear as subtasks under the original story with the `auto-generated` and `qa-gen` labels.
4. **Given** the `--dry-run` flag is used, **When** generation completes, **Then** test cases are displayed but nothing is written to JIRA.
5. **Given** the `--export md` flag is used, **When** generation completes, **Then** the action prompt is skipped and a Markdown file `test-cases-<STORY_ID>.md` is saved locally immediately.
6. **Given** the `--no-confirm` flag is used, **When** generation completes, **Then** all test cases are pushed to JIRA as subtasks immediately without any action prompt.

---

### User Story 2 - Vocabulary Resolution During Generation (Priority: P2)

When the knowledge base cannot instantly match a component or form mentioned in a story, the tool escalates through a resolution chain — alias lookup, then (v2) semantic search, then a confirmation prompt — rather than silently guessing or failing.

**Why this priority**: This is the quality gate that prevents hallucinated test steps. A missed resolution either blocks generation safely or prompts the tester transparently.

**v1 Independent Test**: Trigger generation with a story containing a component phrase not in `aliases.yaml`. Confirm the tool prompts the tester to type the component ID from the known list.

> **v2 Independent Test**: Trigger generation with a story containing a component phrase not in the alias table. Confirm the tool presents top-3 candidate matches, waits for tester selection, then auto-saves the phrase as an alias for future use.

**Acceptance Scenarios**:

1. **Given** a phrase has a known alias, **When** the term appears in a story, **Then** it resolves instantly without any prompt. *(v1 + v2)*
2. *(v2 only)* **Given** no alias exists but a semantic match with score ≥ 0.85 is found, **When** the term appears, **Then** it resolves automatically and the phrase is flagged for alias promotion.
3. *(v2 only)* **Given** a semantic match with score 0.65–0.84, **When** the term appears, **Then** the tester is shown the top-3 candidates with plain-language descriptions and asked to pick one.
4. *(v2 only)* **Given** the tester confirms a match, **Then** the original phrase is saved as an alias so future occurrences resolve at the alias layer.
5. **Given** no match is found, **Then** the tester is prompted to type the component name manually from the known ID list. *(v1 + v2)*

---

### User Story 3 - Manage Form & Component Knowledge Base (Priority: P2)

A KB administrator adds, updates, or inspects form and component definitions in the knowledge base so that new forms and components become available for test generation.

**Why this priority**: Without form and component data, generation for new forms is impossible. This enables the tool to grow alongside the product.

**v1 Independent Test**: Copy a valid form YAML to `knowledge_base/forms/<form_id>.yaml`, then `qa-gen forms show <form_id>` — the resolved (inheritance-flattened) form definition prints correctly. Copy a component YAML to `knowledge_base/components/<component_id>.yaml`, then `qa-gen components show <component_id>` — the component definition prints correctly.

> **v2 Independent Test**: Run `qa-gen forms add <form_id> --file <path>` then `qa-gen forms show <form_id>`. Run `qa-gen components add <component_id> --file <path>` then `qa-gen components show <component_id>`.

**Acceptance Scenarios**:

1. *(v2 only)* **Given** a valid form YAML file exists at a path supplied via `--file <path>`, **When** the admin runs `qa-gen forms add <form_id> --file <path>`, **Then** the form is embedded and upserted to Supabase in a single step and available for future test generation. **v1**: Drop YAML into `knowledge_base/forms/<form_id>.yaml` — available immediately.
2. **Given** a form extends a parent form, **When** the admin runs `qa-gen forms show <form_id>`, **Then** the output shows the fully resolved form with all parent fields merged and overrides applied. *(v1 + v2)*
3. **Given** a YAML file has a schema error, **When** `qa-gen forms validate <form_id>` runs, **Then** specific validation errors are reported with field names and guidance. *(v1 + v2)*
4. **Given** the admin runs `qa-gen forms list`, **Then** all registered forms are shown with their save behavior type. *(v1 + v2)*
5. *(v2 only)* **Given** a valid component YAML file exists at a path supplied via `--file <path>`, **When** the admin runs `qa-gen components add <component_id> --file <path>`, **Then** the component is embedded and upserted to Supabase in a single step. **v1**: Drop YAML into `knowledge_base/components/<component_id>.yaml`.
6. **Given** the admin runs `qa-gen components show <component_id>`, **Then** the full component definition prints including all fields and interaction steps. *(v1 + v2)*
7. **Given** the admin runs `qa-gen components list`, **Then** all registered components are shown with their labels. *(v1 + v2)*

---

### User Story 4 - Manage QA Vocabulary Aliases (Priority: P3)

A QA tester adds their own plain-language phrases to map to known component or form IDs, so future mentions of those phrases resolve automatically without developer involvement.

**Why this priority**: Reduces friction for QA team members who don't know developer naming conventions. Improves retrieval accuracy over time through organic growth.

**Independent Test**: Add alias `"the calendar widget"` mapping to `date_picker_v2`, then run test generation against a story mentioning "the calendar widget" — it resolves without any confirmation prompt.

**Acceptance Scenarios**:

1. **Given** a QA tester runs `qa-gen aliases add "the calendar thing" --maps-to date_picker_v2`, **Then** the alias is saved and future mentions resolve to `date_picker_v2` without any confirmation prompt.
2. **Given** a tester runs `qa-gen aliases list --component date_picker_v2`, **Then** all known QA phrases for that component are listed.
3. **Given** a tester runs `qa-gen aliases remove "stale phrase"`, **Then** that phrase is deleted from the alias table.
4. **Given** a tester runs `qa-gen aliases add "phrase" --maps-to new_id` and "phrase" already maps to a different ID, **Then** the system displays an error showing the current mapping and exits without writing — re-run with `--force` to overwrite.

---

### User Story 5 - Configure the Tool (Priority: P4)

A first-time user runs `qa-gen config` to supply credentials and connection settings through an interactive wizard.

**Why this priority**: Prerequisite for all other features, but a one-time setup action with no recurring complexity.

**Independent Test**: Run `qa-gen config` on a fresh install, complete the wizard, then run `qa-gen config show` — all non-secret settings display correctly.

**Acceptance Scenarios**:

1. **Given** no config exists, **When** the user runs `qa-gen config`, **Then** an interactive wizard collects JIRA URL, JIRA username, JIRA API token, AI provider key, AI model name, and knowledge base path. *(v1: 7 fields)* *(v2 also collects: Supabase URL, service_role key, Supabase DB URL, Voyage AI key — 10 fields total)*
2. **Given** config exists, **When** the user runs `qa-gen config show`, **Then** current settings display with secrets redacted. *(v1 + v2)*
3. *(v2 only)* **Given** `qa-gen config` has been completed, **When** the user runs `qa-gen db init`, **Then** all required Supabase tables are created and the command confirms success. Re-running is safe and produces no data loss.
4. *(v2 only)* **Given** required Supabase tables do not exist, **When** the user runs any command that accesses the knowledge base or aliases, **Then** the tool errors immediately with a message instructing the user to run `qa-gen db init`.

---

### Edge Cases

- What happens when a JIRA story has no `form_id` label? → Tool attempts extraction from story text; if still unresolved, prompts tester to select from known forms.
- What happens when a story has no acceptance criteria? → Tool warns tester, extracts implicit AC from description, and flags output as low confidence before proceeding.
- What happens when the knowledge base has no entry for the detected form? → Generation is blocked; tester is told to add the form first.
- What happens when the AI returns malformed output? → Tool retries once with stricter format instructions; if still malformed, displays raw text.
- What happens when JIRA write-back fails? → Test cases are saved locally as a Markdown file and the tester is shown the file path.
- What happens when a form extends a parent that does not exist in the KB? → Validation error is raised with a clear message identifying the missing parent.
- What happens when the `--form <form_id>` override flag specifies a form not in the KB? → Error displayed immediately before generation is attempted; auto-detection is skipped entirely when `--form` is supplied.
- *(v2 only)* What happens when required Supabase tables do not exist? → Tool errors immediately with a message instructing the user to run `qa-gen db init`.

---

## Clarifications

> **Version note**: Several clarifications below reference Supabase, pgvector, Voyage AI, and `db init`. These are v2 decisions — preserved here for v2 implementation context. v1 uses flat YAML files with no DB or embeddings.

### Session 2026-04-24

- Q: Where should the alias table be stored — local YAML per machine or shared across the team? → A: Supabase shared table
- Q: What does the "Edit" action do in the post-generation action prompt? → A: Open in $EDITOR (temp file); re-parse after save/close
- Q: Does `forms add` auto-ingest to Supabase or require a separate ingest step? → A: Auto-ingest — save YAML + embed + upsert to Supabase in one command
- Q: Is rejected test case feedback logging in scope for v1? → A: Deferred to v2; discard action completes silently
- Q: Should `--no-confirm` flag be in scope for v1? → A: Yes — add as FR-022; required for Phase 4 unattended pipeline automation
- Q: Does JIRA integration use direct REST API or MCP protocol? → A: Direct JIRA REST API via httpx — no MCP server or protocol required
- Q: Where does `qa-gen config` persist credentials and settings? → A: `~/.qa-gen/.env` — home-dir file, machine-local, no git-commit risk
- Q: Aliases storage — Supabase only or local YAML fallback? → A: Supabase only — no local file; network connection required for all alias operations
- Q: Retry policy for external API failures (Claude, JIRA, Supabase, Voyage AI)? → A: 3 retries with exponential backoff (1s → 2s → 4s) for all external calls
- Q: How does `forms add` locate the YAML file to ingest? → A: `--file <path>` is always required — no default path; superseded by session clarification below
- Q: What JIRA authentication method should the config wizard collect? → A: Username + API Token (Atlassian Cloud standard)
- Q: What numeric thresholds split high-confidence vs low-confidence semantic matches? → A: ≥ 0.85 auto-resolve; 0.65–0.84 show top-3; < 0.65 no match
- Q: Which JIRA REST API version to use? → A: v3 (current Atlassian Cloud standard; ADF parsing required for story body fields)
- Q: What happens when `aliases add` is run with a phrase that already maps to a different target? → A: Error — display current mapping, require `--force` flag to overwrite
- Q: How should HTTP 429 rate limit responses be handled vs other transient errors? → A: On 429, read `Retry-After` header and wait that duration; fall back to 30s if header absent; max 3 retries
- Q: How is `qa-gen` distributed and installed on team member machines? → A: `pipx install git+<repo-url>` — direct from Git repo, no private registry required
- Q: What observability does `qa-gen` need for v1? → A: Errors/warnings to stderr always; `--verbose` flag writes debug log to `~/.qa-gen/debug.log`
- Q: What is the maximum number of test cases generated per story in v1? → A: 15
- Q: What structure should `--export json` output use? → A: Zephyr Scale JSON import format — team uses Zephyr Scale as test management tool
- Q: Should `~/.qa-gen/.env` be created with restricted file permissions? → A: Enforce mode 600 (owner read/write only) on create; warn tester if permissions are later relaxed
- Q: Which AI model should `qa-gen` use for test generation, and how is it configured? → A: Model-agnostic — AI model name configurable via `~/.qa-gen/.env`, set once through `qa-gen config` wizard; no per-command flag or CLI override
- Q: How should generated test cases be structured in Gherkin output? → A: One `Feature` block per story, multiple `Scenario` blocks inside — single file/output unit; no `Scenario Outline` or bare scenario list
- Q: Does `qa-gen` create Supabase tables automatically or via explicit command? → A: Explicit `qa-gen db init` command — tester runs once after `qa-gen config`; no auto-migration on startup
- Q: How does admin supply form YAML to `forms add` — default local path or explicit `--file`? → A: Always explicit `--file <path>` — no default path convention; no `knowledge_base/` directory assumption; Supabase is canonical store after ingest
- Q: Which Voyage AI embedding model should `qa-gen` use for semantic search? → A: `voyage-3-large` — highest accuracy for mixed technical/plain-language content; aligns with FR-014 confidence thresholds
- Q: What does the form YAML schema look like? → A: Minimal required fields: `form_id` (string), `save_behavior` (enum), `save_trigger` (enum), `fields[]` each with `id`/`label`/`type`/`required`; optional `extends` (string) for parent inheritance
- Q: How are Voyage AI embeddings stored and queried for semantic search? → A: pgvector extension in Supabase — embeddings stored as `vector` columns, cosine similarity via `<=>` operator; no separate vector DB required
- Q: Which AI providers does v1 support for test generation? → A: Anthropic (Claude) and Google Gemini — two explicit providers; model name stored in `~/.qa-gen/.env` selects the active model within the configured provider
- Q: What is the minimum Python version required? → A: Python 3.11+ — required for `match`/`case`, improved error messages, and stdlib features used in implementation
- Q: Which Zephyr Scale deployment target does `--export json` output target? → A: Zephyr Scale Cloud (Atlassian Marketplace app for Jira Cloud) — consistent with team's Atlassian Cloud JIRA instance
- Q: What is the component YAML schema for component ingestion? → A: Required: `id` (string), `label` (string), `description` (string), `interaction_steps` (string[]); optional: `save_behavior_notes` (string), `forms` (string[]). User-supplied YAML; this is the canonical default schema.
- Q: When tester selects "export" at the action prompt, how is format chosen? → A: Sub-prompt "Export as: [md / json]?" fires after "export" selected; primary prompt keeps 4 options (push / export / edit / discard) without format variants.
- Q: When a JIRA story has multiple `form_id` labels, how should the tool disambiguate? → A: Use first label (lowest-index in labels array) as target form; warn tester listing ignored form labels; tester may re-run with `--form` to target a specific form.
- Q: When `--export md` and `--export json` are both passed simultaneously, what happens? → A: Both files written additively — `test-cases-<STORY_ID>.md` and `test-cases-<STORY_ID>.json`; consistent with additive flag pattern in FR-022.
- Q: When `qa-gen config` is re-run on a machine with existing config, does wizard pre-fill or start fresh? → A: Pre-fill all existing values; tester edits only changed fields, accepts unchanged by pressing Enter.
- Q: How should generated test cases be displayed before the action prompt — dump stdout or pager? → A: Pipe through `$PAGER` (default `less`); fall back to plain stdout when not a TTY.
- Q: Should Anthropic (Claude) generation calls use prompt caching for shared context? → A: Yes — cache system prompt + vocabulary/form/component context block; story-specific content uncached; Gemini provider unaffected.
- Q: Is `--form <form_id>` override flag in scope for v1? → A: Yes — added as FR-027; overrides FR-002 auto-detection entirely; errors immediately if form_id not in KB.
- Q: Should duplicate push be prevented when story already has `qa-gen` subtasks? → A: Warn tester with count of existing qa-gen subtasks and require confirmation before proceeding; `--no-confirm` auto-proceeds.
- Q: Which Google SDK for Gemini provider integration? → A: `google-genai` — current Google GenAI Python SDK; replaces deprecated `google-generativeai`.
- Q: How are components ingested into the KB — dedicated CLI subgroup or embedded in form YAML? → A: `qa-gen components` subgroup mirroring `forms` — `components add <component_id> --file <path>`, `components list`, `components show <component_id>`; same Voyage AI embed + Supabase upsert pattern.
- Q: When `--export md` or `--export json` is passed as CLI flag, does the action prompt still appear? → A: No — action prompt skipped entirely; generate then export immediately to file (same behavior as `--dry-run` skipping JIRA write).
- Q: What happens when tester saves invalid Gherkin from `$EDITOR` during edit action? → A: Show parse error inline, re-open `$EDITOR` with same file — loop until valid Gherkin or tester aborts (Ctrl-C).
- Q: When `--export` and `--no-confirm` are combined, do both actions execute? → A: Yes — both execute additively: export file AND push to JIRA with no prompt; designed for CI/automation pipelines.
- Q: When `--dry-run` and `--no-confirm` are combined, which flag wins? → A: `--dry-run` wins — display only, no JIRA push; tool MUST warn tester that `--no-confirm` is ignored when `--dry-run` is active.
- Q: What happens to the action prompt when `qa-gen tests` runs in a non-TTY environment without `--dry-run` or `--no-confirm`? → A: Error immediately — "interactive prompt unavailable in non-TTY — use `--dry-run` or `--no-confirm`"
- Q: When `--export md`/`--export json` target file already exists, what happens? → A: Overwrite silently — no prompt, no error
- Q: When CLI `<form_id>`/`<component_id>` arg differs from `form_id`/`id` field inside the YAML, what happens? → A: Validation error — CLI arg and YAML field must match; abort with clear message identifying the mismatch
- Q: What is the timeout for the AI generation call? → A: 60 seconds
- Q: Which Supabase key type should the config wizard collect, and should it cover both `db init` DDL and runtime DML? → A: Single service_role key for all operations — wizard must document this requirement explicitly

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST fetch a JIRA story (title, description, acceptance criteria, labels, components) given a story ID using the JIRA REST API v3. Rich text fields (description, acceptance criteria) are returned in Atlassian Document Format (ADF) and MUST be converted to plaintext before use in generation context.
- **FR-002**: System MUST identify the target form from JIRA story labels; fall back to text extraction; fall back to tester prompt if still unresolved. When multiple `form_id` labels are present on a story, the system MUST use the first label (lowest-index in the labels array) as the target form and MUST warn the tester listing the other `form_id` labels that were ignored. The tester may use `--form <form_id>` (FR-027) to override and target a specific form.
- **FR-003**: System MUST retrieve the fully resolved form definition (with inheritance flattened) from the knowledge base before generation.
- **FR-004**: System MUST retrieve all shared component definitions referenced by the resolved form.
- **FR-005**: System MUST inject UI behavioral vocabulary alongside form and component context into every generation request — this vocabulary must never be omitted.
- **FR-006**: System MUST generate Gherkin-format test cases covering positive, negative, and edge cases for the story. Output MUST be structured as a single `Feature` block (title = JIRA story ID + title) containing multiple `Scenario` blocks — one per test case. `Scenario Outline` is not used.
- **FR-007**: Generated test cases MUST reference exact UI selectors specified in the form definition — no generic step language is permitted.
- **FR-008**: For forms with explicit save behavior, system MUST generate a test case verifying that field blur does NOT trigger a save.
- **FR-009**: For each field marked with blur-save enabled, system MUST generate a test case verifying blur triggers a save.
- **FR-010**: System MUST present generated test cases to the tester by piping output through `$PAGER` (defaulting to `less` if `$PAGER` is unset); when stdout is not a TTY (e.g. CI pipeline), output MUST be written to stdout directly without invoking a pager. After the tester exits the pager, the system MUST prompt for action (push / export / edit / discard) before writing anything to JIRA; the "edit" action MUST open test cases in `$EDITOR` as a temp file, re-parse the result after the editor closes, then return the tester to the action prompt with updated cases. When "export" is selected, a secondary prompt MUST ask "Export as: [md / json]?" before writing the file — the primary prompt itself does NOT list format variants. When `--export md` or `--export json` is passed as a CLI flag, the action prompt MUST be skipped entirely — the tool generates and immediately writes the export file without any interactive prompt. If re-parsing after editor close produces a Gherkin syntax error, the tool MUST display the error inline and re-open `$EDITOR` with the same temp file — this loop continues until the tester saves valid Gherkin or aborts with Ctrl-C. When stdout is not a TTY and neither `--dry-run` nor `--no-confirm` is passed, the tool MUST exit with a non-zero status and print to stderr: "interactive prompt unavailable in non-TTY — use --dry-run or --no-confirm".
- **FR-011**: System MUST create JIRA subtasks from approved test cases with `auto-generated` and `qa-gen` labels. Before creating subtasks, the system MUST check whether the parent story already has any subtasks carrying the `qa-gen` label; if found, the tester MUST be warned ("X existing qa-gen subtasks found on this story") and asked to confirm before proceeding. `--no-confirm` flag bypasses this warning and proceeds automatically.
- **FR-012**: System MUST support `--dry-run` mode that generates and displays output without writing to JIRA. `--dry-run` takes precedence over all write flags — if `--no-confirm` is also present, it MUST be silently ignored and the tool MUST warn: "`--no-confirm` ignored: `--dry-run` is active."
- **FR-013**: System MUST support `--export md` and `--export json` flags that save output to local files. The `--export json` output MUST conform to the **Zephyr Scale Cloud** JSON import format (Atlassian Marketplace app for Jira Cloud) so exported files can be imported directly into Zephyr Scale Cloud. When both `--export md` and `--export json` are passed simultaneously, both files MUST be written additively — `test-cases-<STORY_ID>.md` and `test-cases-<STORY_ID>.json` — consistent with the additive flag behavior in FR-022. If a target export file already exists at the output path, it MUST be overwritten silently — no prompt and no error.
- **FR-014**: *(v1: alias lookup + free-text fallback only)* *(v2: full chain)* System MUST resolve component and form references through a layered chain: alias lookup → semantic search → confirmation prompt → free-text fallback — in that priority order. **v1**: only alias lookup and free-text fallback are active. **v2**: semantic search uses Voyage AI (`voyage-3-large`) to embed the query phrase and executes a cosine similarity query against the `embedding` vector columns in Supabase via the pgvector `<=>` operator. Confidence thresholds (cosine similarity): score ≥ 0.85 = auto-resolve with no prompt; score 0.65–0.84 = show top-3 candidates for tester selection; score < 0.65 = no match, escalate to free-text fallback.
- **FR-015**: *(v2 only)* After a tester confirms a match at the confirmation layer, the system MUST automatically save the original phrase as an alias for future resolution.
- **FR-016**: System MUST allow any team member to add, list, and remove vocabulary aliases without developer assistance. **v1**: aliases stored in `knowledge_base/aliases.yaml` — shared via git. **v2**: aliases stored exclusively in the shared Supabase table — network connection required for all alias operations. When `aliases add` is run with a phrase that already maps to a different target, the system MUST display an error showing the current mapping and abort — the `--force` flag is required to overwrite an existing alias. *(v1 + v2)*
- **FR-017**: System MUST allow KB administrators to add, update, validate, list, and inspect form definitions via CLI commands. **v1**: `forms add` is not available — admins drop YAML files directly into `knowledge_base/forms/`. **v2**: `forms add` MUST embed the provided YAML via Voyage AI and upsert to Supabase in a single command. The form YAML MUST conform to the following minimal schema: required top-level keys are `form_id` (string), `save_behavior` (enum: e.g. `auto`, `manual`, `blur`), `save_trigger` (enum: e.g. `button`, `blur`, `change`), and `fields` (array); each field entry requires `id` (string), `label` (string), `type` (string), and `required` (boolean). The optional `extends` key (string) names a parent `form_id` for inheritance. `forms validate` MUST report errors with the offending key name and a remediation hint. *(v1 + v2)*
- **FR-018**: System MUST display a low-confidence warning before generating when the form was identified via text extraction rather than a label.
- **FR-019**: System MUST block test generation and alert the tester when a form has no KB entry — never fall through to generation with missing context.
- **FR-020**: System MUST provide an interactive configuration wizard for first-time setup and a redacted config display command. **v1**: The wizard MUST collect JIRA URL, JIRA username (email address), JIRA API token, AI provider (one of: `anthropic`, `gemini`), AI provider API key, AI model name, and knowledge base path (`KB_PATH`, default `./knowledge_base`) — 7 fields total. **v2**: The wizard also collects Supabase connection URL, Supabase service_role key (inline note: "Use your project's service_role key — required for db init DDL and all runtime operations"), Supabase DB URL (inline note: "Direct PostgreSQL connection string — required for 'db init'"; optional at wizard time), and Voyage AI API key — 10 fields total. All settings MUST be persisted to `~/.qa-gen/.env`; this file is machine-local and must never be written inside the project directory. The file MUST be created with mode 600 (owner read/write only). On every startup, the tool MUST check `~/.qa-gen/.env` permissions and warn the tester if the file is readable by group or others. When `qa-gen config` is re-run on a machine that already has `~/.qa-gen/.env`, the wizard MUST pre-fill each prompt with the existing value — the tester edits only the fields that need updating and accepts unchanged fields by pressing Enter.
- **FR-021**: When JIRA write-back fails, system MUST save generated test cases to a local file and report the file path to the tester.
- **FR-022**: System MUST support `--no-confirm` flag that skips the action prompt and auto-pushes all generated test cases to JIRA without human input — required for unattended pipeline automation. When combined with `--export md` or `--export json`, both actions execute additively: the export file is written AND subtasks are pushed to JIRA in the same run with no prompt.
- **FR-023**: All external API calls (JIRA REST, Claude API, Supabase, Voyage AI) MUST be retried up to 3 times on network or transient errors using exponential backoff (delays: 1s, 2s, 4s). HTTP 429 (rate limited) responses MUST be handled separately: read the `Retry-After` response header and wait that duration before retrying; if the header is absent, wait 30s. The 3-retry limit applies to 429s as well. After 3 failed attempts the operation MUST fail with a clear error message identifying the failing service and the error type (rate limited vs transient). AI generation calls (Claude, Gemini) MUST enforce a 60-second per-attempt timeout; a timeout counts as a transient error and triggers the retry policy.
- **FR-024**: All errors and warnings MUST be written to stderr. When `--verbose` is passed, the tool MUST write structured debug output (request/response summaries, resolution steps, retry attempts) to `~/.qa-gen/debug.log`, appending to any existing file.
- **FR-025**: Generation MUST produce a maximum of 15 test cases per story. If the AI model returns more than 15, the tool MUST truncate to the first 15 and warn the tester.
- **FR-026**: *(v2 only)* System MUST provide a `qa-gen db init` command that creates all required Supabase tables (forms, components, aliases, and any supporting tables). This command MUST also enable the `pgvector` extension (`CREATE EXTENSION IF NOT EXISTS vector`) and add `embedding vector(1024)` columns to the `forms` and `components` tables (dimension 1024 matches `voyage-3-large` output). This command is idempotent — safe to re-run; existing data is not modified. Testers MUST run this once after `qa-gen config` during initial setup. The tool MUST NOT auto-migrate on startup; if required tables are missing at runtime, the tool MUST error with a clear message instructing the tester to run `qa-gen db init`. DDL execution requires the Supabase service_role key stored in `~/.qa-gen/.env` — the anon key does not have sufficient privileges for `db init`.
- **FR-027**: System MUST support `--form <form_id>` flag on `qa-gen tests` that explicitly sets the target form, bypassing FR-002 auto-detection entirely. If the supplied `form_id` has no KB entry, the tool MUST error immediately before generation is attempted.
- **FR-029**: When the configured AI provider is Anthropic (Claude), generation requests MUST use prompt caching (`cache_control: {"type": "ephemeral"}`) on the system prompt block and the shared context block containing UI behavioral vocabulary, form definition, and component definitions. The story-specific content (title, description, acceptance criteria) is NOT cached — it changes per call. Caching applies only to the Anthropic provider; the Gemini provider does not use this mechanism.

- **FR-028**: System MUST provide a `qa-gen components` subcommand group for KB administrators to manage component definitions: `components list` (display all registered components with labels), `components show <component_id>` (display full component definition). *(v1 + v2)* **v1**: add components by dropping YAML files into `knowledge_base/components/`. **v2 only**: `components add <component_id> --file <path>` embeds via Voyage AI and upserts to Supabase in one step — `--file <path>` flag required; if CLI `<component_id>` does not match `id` field inside YAML, command MUST abort with a validation error. Component YAML MUST conform to the schema in Key Entities: required keys `id`, `label`, `description`, `interaction_steps`; optional keys `save_behavior_notes`, `forms`.

### Key Entities

- **Form**: Represents a single UI form. YAML schema — required keys: `form_id` (string, unique), `save_behavior` (enum), `save_trigger` (enum), `fields` (array of Field objects). Optional key: `extends` (string — parent `form_id`). Carries save behavior type, save trigger, validation timing, and a list of fields. May extend a parent form via `extends`.
- **Field**: A single input within a form — has an ID, label, type, required flag, and optionally its own save behavior if it overrides the parent form.
- **Component**: A reusable UI element (e.g., date picker, file uploader, search dropdown). YAML schema — required keys: `id` (string, unique), `label` (string), `description` (string), `interaction_steps` (array of strings). Optional keys: `save_behavior_notes` (string), `forms` (array of `form_id` strings referencing forms this component appears in). User supplies YAML; this is the default schema.
- **Alias**: A plain-language QA phrase mapped to a canonical form or component ID — maintained by the QA team and stored in a shared Supabase table so all team members benefit from any new alias immediately.
- **Test Case**: A generated Gherkin scenario — has a title, type (positive/negative/edge), preconditions, ordered steps, and expected result.
- **Story**: A JIRA issue supplying the generation input — has a title, description, acceptance criteria, labels, and component tags.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A QA tester can go from running `qa-gen tests <STORY_ID>` to reviewing complete test cases in under 60 seconds for any story with a known form.
- **SC-002**: 100% of generated test cases reference the form's actual save trigger — no generic save step language appears in output.
- **SC-003**: After aliases are seeded with initial QA phrases (`knowledge_base/aliases.yaml` in v1; Supabase aliases table in v2), 90% of form and component references in stories resolve at the alias layer without any prompt.
- **SC-004**: Zero test cases are generated when a referenced form is absent from the knowledge base — the system always blocks rather than guessing.
- **SC-005**: Any new vocabulary alias added by a tester resolves correctly on the next invocation without requiring a tool restart or developer action.
- **SC-006**: A KB administrator can add a new form and have it available for test generation in under 10 minutes.
- **SC-007**: When JIRA write-back fails, no test case data is lost — all generated output is recoverable from a local file.

---

## Assumptions

- QA team members have JIRA read access; at least one team member has JIRA write access for subtask creation.
- Form YAML definitions are authored and maintained by developers or KB administrators before test generation is needed for those forms.
- JIRA stories follow the convention of including the `form_id` as a label for deterministic form detection.
- The knowledge base will be seeded with the most frequently tested forms and all shared UI components before the tool is rolled out to the team. **v1**: seeding = copying YAML files to `knowledge_base/`. **v2**: seeding = running `qa-gen forms add` + `qa-gen components add` per file.
- Mobile and native app forms are out of scope for v1 — only web UI forms are covered.
- The tool runs locally on individual QA team machines; no centralized server deployment is required for v1.
- JIRA integration uses the Atlassian REST API directly via `httpx` — no MCP server or protocol is required. The `jira_mcp.py` module name in the build spec is a naming convention only.
- JIRA instance is Atlassian Cloud. Authentication uses username (email) + API token per Atlassian's recommended auth method — password-based auth is not supported.
- JIRA REST API v3 is used for all requests. Story description and acceptance criteria fields are returned in Atlassian Document Format (ADF) and must be parsed to plaintext before injection into generation context.
- Multi-page wizards are treated as separate forms unless explicitly linked via inheritance in the form YAML.
- Rejected test case feedback logging (capturing discarded output for KB improvement) is explicitly out of scope for v1 — deferred to v2.
- `qa-gen` is distributed via `pipx install git+<repo-url>` — no private PyPI registry is required. Team members install directly from the Git repository URL. Minimum Python version is **3.11**; installations on older Python versions are unsupported.
- The team uses Zephyr Scale Cloud (Atlassian Marketplace app for Jira Cloud) as the test management tool. `--export json` output MUST conform to the Zephyr Scale Cloud JSON import format.
- *(v2 only)* Voyage AI embedding model is `voyage-3-large`. This model is fixed — not configurable. The FR-014 confidence thresholds (≥0.85 auto-resolve, 0.65–0.84 top-3 prompt) are calibrated for this model.
- Anthropic provider uses the `anthropic` Python SDK. Gemini provider uses the `google-genai` Python SDK (current Google GenAI SDK; replaces deprecated `google-generativeai`).
- *(v2 only)* Supabase is a shared team resource — all team members share the same forms, components, and aliases tables. Requires one admin to run `qa-gen db init` and seed the KB before other team members can use the tool.
