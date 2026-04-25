# Tasks: QA Test Case Generation CLI Tool

**Input**: Design documents from `/specs/001-qa-testgen-cli/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/cli.md ✓, quickstart.md ✓

**Organization**: Tasks grouped by user story for independent implementation and testing. No test tasks — none requested in spec.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[Story]**: User story this task belongs to (US1–US5)
- Exact file paths in every description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and package structure

- [X] T001 Create `pyproject.toml` with `[project]` name=`qa-gen`, `requires-python=">=3.11"`, dependencies: typer, rich, httpx, supabase, voyageai, anthropic, google-genai, pydantic, pyyaml, gherkin-official, psycopg2-binary; `[project.scripts]` entry `qa-gen = "qa_gen.cli.main:app"`; `[tool.ruff]` config; `[tool.pytest.ini_options]` pointing to `tests/`
- [X] T002 [P] Create all package `__init__.py` files: `qa_gen/__init__.py`, `qa_gen/cli/__init__.py`, `qa_gen/cli/commands/__init__.py`, `qa_gen/core/__init__.py`, `qa_gen/core/ai/__init__.py`, `qa_gen/kb/__init__.py`, `qa_gen/models/__init__.py`, `qa_gen/config/__init__.py`, `qa_gen/knowledge_base/.gitkeep` per plan.md structure
- [X] T003 [P] Create test package stubs: `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`, `tests/contract/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story begins

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Implement `qa_gen/config/settings.py`: `Settings` dataclass loading from `~/.qa-gen/.env` only (not project dir, not shell env) with typed fields `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_DB_URL` (optional str | None — only required for `db init`), `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL_NAME`, `VOYAGE_API_KEY`; `load_settings() -> Settings` raises `SystemExit(1)` with `"run qa-gen config first"` if file missing; on load, `os.stat(path).st_mode & 0o777` check — warn to stderr if not `0o600` per FR-020
- [X] T005 [P] Implement `qa_gen/kb/supabase_client.py`: `create_supabase_client(settings: Settings) -> supabase.Client`; CRUD functions: `get_form(client, form_id)`, `upsert_form(client, data)`, `list_forms(client)`, `get_component(client, component_id)`, `upsert_component(client, data)`, `list_components(client)`, `get_alias(client, phrase)`, `upsert_alias(client, data)`, `delete_alias(client, phrase)`, `list_aliases(client, target_id, target_type)`; RPC: `match_forms(client, query_embedding, threshold, count)`, `match_components(client, query_embedding, threshold, count)`; catch `APIError` for missing tables and raise `SystemExit(2)` with `"required tables are missing — run qa-gen db init"` per FR-026
- [X] T006 [P] Implement `qa_gen/kb/embedding.py`: `EmbeddingClient(api_key: str)` wrapping `voyageai.Client`; `embed_document(texts: list[str]) -> list[list[float]]` with `input_type="document"`; `embed_query(phrase: str) -> list[float]` with `input_type="query"`; model fixed to `"voyage-3-large"` (dimension 1024); retry wrapper: 3 attempts, 1s/2s/4s backoff, 429 reads `Retry-After` header (30s fallback) per research.md §2/FR-023
- [X] T007 [P] Create `qa_gen/models/form.py`: `Field` Pydantic model (id, label, type, required, save_on_blur=False, component=None, save_behavior=None, save_trigger=None); `Form` Pydantic model (form_id, display_name, module, save_behavior, save_trigger, validation_timing, fields: list[Field], extends=None, notes=None) with `form_id` snake_case `field_validator` per data-model.md
- [X] T008 [P] Create `qa_gen/models/component.py`: `Component` Pydantic model (id, label, description, interaction_steps: list[str], save_behavior_notes=None, forms: list[str]=[]) per data-model.md
- [X] T009 [P] Create `qa_gen/models/alias.py`: `Alias` Pydantic model (phrase: str, target_id: str, target_type: Literal["form", "component"]) per data-model.md
- [X] T010 [P] Create `qa_gen/models/test_case.py`: `TestCase` Pydantic model (title, type: Literal["positive","negative","edge"], preconditions: list[str], steps: list[str], expected_result: str, story_id: str); `to_gherkin_scenario() -> str` — single `Scenario:` block with Given/When/And/Then, no Scenario Outline; `to_zephyr_step() -> dict` — Zephyr Scale Cloud STEP_BY_STEP format `{"description": "→".join(steps), "testData": "", "expectedResult": expected_result}` per data-model.md/research.md §8
- [X] T011 Implement `qa_gen/kb/migrations.py`: DDL string constants for `CREATE EXTENSION IF NOT EXISTS vector`, `CREATE TABLE IF NOT EXISTS forms` (schema from data-model.md including `embedding VECTOR(1024)`), `CREATE TABLE IF NOT EXISTS components` (including `embedding VECTOR(1024)`), `CREATE TABLE IF NOT EXISTS aliases`, IVFFlat indexes, `match_forms` and `match_components` RPC functions; `run_migrations(db_url: str)` opens a `psycopg2.connect(db_url)` connection with `autocommit=True` and executes each DDL statement sequentially — `db_url` is `settings.SUPABASE_DB_URL` (direct PostgreSQL connection string from Supabase dashboard → Settings → Database → Connection string URI mode); on `psycopg2.OperationalError` raise `SystemExit(2)` with connection error details per data-model.md
- [X] T012 [P] Implement `qa_gen/cli/display.py`: `show_with_pager(content: str)` — if `sys.stdout.isatty()` write to temp file and `subprocess.run([$PAGER or "less", tmp_path])`; else `sys.stdout.write(content)` per research.md §7; `action_prompt() -> str` returns "push"/"export"/"edit"/"discard"; `export_format_prompt() -> str` returns "md"/"json"; `confirm(message: str) -> bool`; `show_table(headers, rows)` Rich Table; `show_panel(title, content)` Rich Panel; `spinner(label: str)` Rich Live/Spinner context manager
- [X] T013 Create `qa_gen/cli/main.py`: top-level `app = typer.Typer()`; register sub-apps as stubs now — `tests_app`, `forms_app`, `components_app`, `aliases_app`, `config_app`, `db_app`; each sub-app added via `app.add_typer(..., name="...")`

**Checkpoint**: Foundation ready — all models, Supabase/embedding clients, settings, migrations DDL, display helpers, and CLI skeleton in place

---

## Phase 3: User Story 1 — Generate Test Cases for a JIRA Story (Priority: P1) 🎯 MVP

**Goal**: `qa-gen tests <STORY_ID>` fetches JIRA story, resolves form via label, assembles KB context, calls AI, displays Gherkin via pager, handles push/export/edit/discard actions.

**Independent Test**: `qa-gen tests PROJ-1042 --dry-run` against story with known `form_id` label produces Gherkin test cases without any JIRA write-back.

- [X] T014 [P] [US1] Implement `qa_gen/core/adf_parser.py`: `parse_adf(adf_json: dict) -> str` recursive traversal — extract text from leaf nodes `type=="text"`, join block nodes (`paragraph`, `bulletList`, `listItem`, `heading`, `blockquote`, `codeBlock`, `orderedList`) with `"\n"`, ignore inline marks (`strong`, `em`, `code`); return empty string for non-dict or null input per research.md §1
- [X] T015 [P] [US1] Implement `qa_gen/core/jira_client.py`: `JiraClient(base_url, email, api_token)` with `fetch_story(story_id: str) -> dict` via `httpx.BasicAuth`; `GET /rest/api/3/issue/{story_id}?fields=summary,description,customfield_10016,labels,components,subtasks,issuetype`; parse `description` and `customfield_10016` ADF fields via `adf_parser.parse_adf()`; retry: 3 attempts, 1s/2s/4s, 429 reads `Retry-After` header (30s fallback); `SystemExit(2)` with `"Story {story_id} not found in JIRA"` on 404 per FR-001/FR-023
- [X] T016 [P] [US1] Create `qa_gen/knowledge_base/ui_vocabulary.md`: static Layer 1 vocabulary — save behavior enums (`SAVE_EXPLICIT`, `SAVE_ON_BLUR`, `SAVE_ON_SUBMIT`, `SAVE_AUTO`), save trigger patterns (`"click → [data-testid=\"save-icon\"]"`), validation timing enums (`VALIDATE_ON_SAVE`, `VALIDATE_ON_BLUR`), blur event definition, button states (enabled/disabled/loading), toast notification patterns, error state descriptors, field interaction steps; this file is always injected into every generation request and must never be stored in Supabase per FR-005
- [X] T017 [P] [US1] Implement `qa_gen/core/ai/base.py`: `AIProvider` abstract base class with `generate(system_prompt: str, context: str, story_prompt: str, timeout: int = 60) -> str` abstractmethod
- [X] T018 [P] [US1] Implement `qa_gen/core/ai/claude_client.py`: `ClaudeProvider(AIProvider)` using `anthropic.Anthropic(api_key=...)`; `generate()` sends two cached system blocks (`cache_control: {"type": "ephemeral"}` on role/rules text block and context block) + uncached story `user` message; enforces 60s timeout; retry 3 attempts, 1s/2s/4s, 429 handling per research.md §4/FR-029/FR-023
- [X] T019 [P] [US1] Implement `qa_gen/core/ai/gemini_client.py`: `GeminiProvider(AIProvider)` using `genai.Client(api_key=...)`; `generate()` calls `client.models.generate_content(model=..., contents=[story_prompt], config=types.GenerateContentConfig(system_instruction=system_prompt+"\n\n"+context, max_output_tokens=4096))`; enforce 60s timeout; retry 3 attempts, 1s/2s/4s, 429 handling per research.md §5/FR-023
- [X] T020 [P] [US1] Implement `qa_gen/core/form_resolver.py`: `resolve_form(story_data: dict, supabase_client, settings) -> tuple[Form, bool]` — (1) extract labels list, filter `form_id` labels; use first (warn to stderr for others); (2) fetch from Supabase by `form_id`; (3) if no label, attempt text extraction from story text → set low-confidence flag (warn to stderr per FR-018); (4) still unresolved → prompt tester to pick from `list_forms()` output; (5) `SystemExit(3)` with `"Form {form_id} not in KB — add it first"` if resolved ID has no KB entry per FR-002/FR-003/FR-019; flatten inheritance via recursive parent fetch from Supabase
- [X] T021 [P] [US1] Implement `qa_gen/core/component_resolver.py`: `resolve_components(form: Form, supabase_client) -> list[Component]` — query Supabase `components` table for rows where `forms` array contains `form.form_id`; return list of `Component` Pydantic models per FR-004
- [X] T022 [P] [US1] Implement `qa_gen/core/context_assembler.py`: `assemble_context(form: Form, components: list[Component]) -> str` — read `qa_gen/knowledge_base/ui_vocabulary.md` via `importlib.resources`; concatenate vocabulary markdown + rendered form YAML + each component YAML into single context string; `assemble_system_prompt() -> str` returns role/rules text for AI system block per FR-003/FR-005
- [X] T023 [P] [US1] Implement `qa_gen/core/gherkin_parser.py`: `validate_gherkin(text: str) -> list[str]` using `gherkin.parser.Parser` + `TokenScanner` — return empty list on success, error strings on failure per research.md §6; `parse_gherkin_to_test_cases(text: str, story_id: str) -> list[TestCase]` extract `Scenario` blocks and map to `TestCase` objects; `SystemExit(4)` if AI output fails parse after retry
- [X] T024 [P] [US1] Implement `qa_gen/core/jira_writer.py`: `count_existing_qa_subtasks(story_id: str, jira_client: JiraClient) -> int` — fetch story subtasks, count those with `qa-gen` label; `create_subtasks(story_id, test_cases: list[TestCase], jira_client, no_confirm: bool) -> bool` — warn `"X existing qa-gen subtasks found on this story"` and `confirm()` unless `no_confirm`; `POST /rest/api/3/issue` per subtask with `auto-generated`+`qa-gen` labels; on write failure save to `test-cases-{story_id}.md` and print path to stderr per FR-011/FR-021; retry per FR-023
- [X] T025 [US1] Implement `qa_gen/core/orchestrator.py`: `run(story_id, dry_run, export_formats, form_override, no_confirm, verbose, settings) -> list[TestCase]` — (1) check non-TTY: if not `sys.stdin.isatty()` and not `dry_run` and not `no_confirm` → `SystemExit(1)` stderr `"interactive prompt unavailable in non-TTY — use --dry-run or --no-confirm"`; (2) load settings + init clients; (3) `JiraClient.fetch_story()`; (4) `--form` override: KB check first, `SystemExit(3)` if missing; else `form_resolver.resolve_form()`; (5) `component_resolver.resolve_components()`; (6) `context_assembler.assemble_context()`; (7) select `ClaudeProvider` or `GeminiProvider` from `settings.AI_PROVIDER`; (8) call `provider.generate()` — on malformed output retry once with stricter format instruction; (9) `gherkin_parser.parse_gherkin_to_test_cases()` — truncate to 15, warn to stderr if truncated per FR-025; (10) blur-save validation (FR-008/FR-009): if form's `save_behavior` is not a blur type, check that at least one `TestCase.steps` contains the form's `save_trigger` string in a negation context — warn to stderr `"FR-008: no blur-does-not-save scenario detected; review AI output"` if absent; for each `Field` with `save_on_blur=True`, check that at least one `TestCase` references that field's label in a blur-triggers-save context — warn to stderr `"FR-009: no blur-triggers-save scenario for field '{field.id}'"` if absent; warnings do not block or truncate generation; return list per FR-008/FR-009/FR-010/FR-019/FR-025
- [X] T026 [US1] Implement `qa_gen/cli/commands/tests.py`: `tests_app = typer.Typer()`; `generate(story_id: str, dry_run: bool, export: list[str], form: str, no_confirm: bool, verbose: bool)` command — conflict rules: `--dry-run`+`--no-confirm` → warn stderr `"--no-confirm ignored: --dry-run is active"`, `--dry-run` wins; call `orchestrator.run()`; if `export` flags set → skip action prompt, write `test-cases-{STORY_ID}.md` and/or Zephyr Scale JSON; else `display.show_with_pager()` → `action_prompt()` loop: push → `jira_writer.create_subtasks()`, export → `export_format_prompt()` → write file, edit → `tempfile` + `$EDITOR` + `gherkin_parser.validate_gherkin()` loop until valid or Ctrl-C, discard → exit silently per contracts/cli.md/FR-010/FR-012/FR-013/FR-022
- [X] T027 [US1] Replace stub in `qa_gen/cli/main.py`: import `tests_app` from `qa_gen.cli.commands.tests` and wire `app.add_typer(tests_app, name="tests")`

**Checkpoint**: `qa-gen tests PROJ-1042 --dry-run` against story with known `form_id` label produces Gherkin test cases without write-back

---

## Phase 4: User Story 2 — Vocabulary Resolution During Generation (Priority: P2)

**Goal**: Unknown component/form phrases escalate through alias → semantic search → confirmation prompt → free-text fallback, with auto-alias save on confirmation.

**Independent Test**: Trigger generation with story containing component phrase not in alias table — tool shows top-3 semantic candidates with descriptions, waits for selection, auto-saves phrase as alias; next run resolves silently.

- [X] T028 [US2] Implement `qa_gen/core/alias_resolver.py`: `AliasResolver(supabase_client, embedding_client)`; `resolve(phrase: str, target_type: str) -> str | None` — (1) `get_alias(phrase.lower())` → return `target_id` on hit; (2) `embedding_client.embed_query(phrase)` → `match_forms/match_components` RPC (RPC used is determined by `target_type` arg): score ≥ 0.85 → auto-resolve, log phrase for alias promotion via `upsert_alias({phrase: phrase.lower(), target_id: auto_id, target_type: target_type})`; score 0.65–0.84 → `display.show_table()` top-3 candidates with descriptions, tester picks → `upsert_alias({phrase: phrase.lower(), target_id: chosen_id, target_type: target_type})` → return `chosen_id`; (3) score < 0.65 → free-text prompt from `list_forms()/list_components()` known IDs; return `None` if tester aborts per FR-014/FR-015/FR-016
- [X] T029 [US2] Update `qa_gen/core/form_resolver.py`: add `alias_resolver: AliasResolver | None = None` parameter to `resolve_form()`; before text-extraction fallback, call `alias_resolver.resolve(unresolved_phrase, "form")` if resolver provided
- [X] T030 [US2] Update `qa_gen/core/component_resolver.py`: add `alias_resolver: AliasResolver | None = None` parameter to `resolve_components()`; for each `field.component` reference within the resolved `Form`'s field list where `get_component(client, field.component)` returns None (non-canonical ID or human phrase), call `alias_resolver.resolve(field.component, "component")` to attempt alias/semantic resolution; if resolved, use the resolved `component_id` to fetch the component definition; if unresolved, warn to stderr `"component '{field.component}' on field '{field.id}' could not be resolved — skipping"` and continue
- [X] T031 [US2] Update `qa_gen/core/orchestrator.py` and `qa_gen/cli/commands/tests.py`: instantiate `AliasResolver(supabase_client, embedding_client)` in orchestrator; pass to `form_resolver.resolve_form()` and `component_resolver.resolve_components()` calls

**Checkpoint**: `qa-gen tests` with story containing unknown component phrase shows top-3 semantic matches, saves alias on selection, resolves silently on next run

---

## Phase 5: User Story 3 — Manage Form & Component Knowledge Base (Priority: P2)

**Goal**: KB admins add, validate, list, and inspect form and component definitions via CLI.

**Independent Test**: `qa-gen forms add invoice_form --file ./invoice_form.yaml` → `qa-gen forms show invoice_form` prints inheritance-flattened definition. `qa-gen components add date_picker_v2 --file ./date_picker_v2.yaml` → `qa-gen components show date_picker_v2` prints full definition.

- [X] T032 [P] [US3] Implement `qa_gen/cli/commands/forms.py`: `forms_app = typer.Typer()`; `list_forms()` → Rich table with `form_id/display_name/save_behavior/module`; `add_form(form_id: str, file: Path)` → parse + validate YAML against `Form` schema, check `yaml["form_id"] == form_id` (abort with both values if mismatch per research.md §9), verify `extends` parent exists in Supabase (abort with `SystemExit(3)` if missing), `embedding_client.embed_document([yaml_text])`, `supabase_client.upsert_form()`; `show_form(form_id)` → fetch + recursive parent merge (child overrides parent fields) + print as human-readable YAML; `validate_form(form_id: str, file: Path)` → schema validation only, report offending key + remediation hint, no Supabase write per FR-017/contracts/cli.md
- [X] T033 [P] [US3] Implement `qa_gen/cli/commands/components.py`: `components_app = typer.Typer()`; `list_components()` → Rich table with `component_id/label/forms`; `add_component(component_id: str, file: Path)` → parse + validate YAML against `Component` schema, check `yaml["id"] == component_id` (abort on mismatch per research.md §9), `embedding_client.embed_document([yaml_text])`, `supabase_client.upsert_component()`; `show_component(component_id)` → fetch + print all fields and `interaction_steps` per FR-028/contracts/cli.md
- [X] T034 [US3] Replace stubs in `qa_gen/cli/main.py`: import `forms_app` from `qa_gen.cli.commands.forms` and `components_app` from `qa_gen.cli.commands.components`; wire `app.add_typer(forms_app, name="forms")` and `app.add_typer(components_app, name="components")`

**Checkpoint**: Add form → list shows it → show resolves inheritance correctly; add component → list shows it → show prints full definition

---

## Phase 6: User Story 4 — Manage QA Vocabulary Aliases (Priority: P3)

**Goal**: QA testers add/list/remove plain-language phrase→ID mappings without developer involvement; all aliases stored in shared Supabase table.

**Independent Test**: `qa-gen aliases add "the calendar thing" --maps-to date_picker_v2` → `qa-gen aliases list --component date_picker_v2` shows it → test generation with "the calendar thing" resolves silently without confirmation prompt.

- [X] T035 [US4] Implement `qa_gen/cli/commands/aliases.py`: `aliases_app = typer.Typer()`; `add_alias(phrase: str, maps_to: str, force: bool = False)` → fetch existing alias for `phrase.lower()`: if exists with different `target_id` and not `--force` → `SystemExit(1)` showing current mapping; else resolve `target_type`: call `get_form(client, maps_to)` → if row found set `target_type="form"`; else call `get_component(client, maps_to)` → if row found set `target_type="component"`; else `SystemExit(1)` with `"no form or component found with id: {maps_to}"`; then `upsert_alias({phrase: phrase.lower(), target_id: maps_to, target_type: target_type})`; `list_aliases(component: str = None, form: str = None)` → Rich table filtered by `target_id`/`target_type`; `remove_alias(phrase: str)` → `delete_alias(phrase.lower())`, `SystemExit(1)` with `"alias not found"` if missing per FR-016/contracts/cli.md
- [X] T036 [US4] Replace stub in `qa_gen/cli/main.py`: import `aliases_app` from `qa_gen.cli.commands.aliases`; wire `app.add_typer(aliases_app, name="aliases")`

**Checkpoint**: Add alias → listed → resolves silently in test generation; `--force` overwrites; error shown for duplicate without `--force`

---

## Phase 7: User Story 5 — Configure the Tool (Priority: P4)

**Goal**: First-time setup wizard creates `~/.qa-gen/.env` mode 600; `db init` creates Supabase tables idempotently.

**Independent Test**: `qa-gen config` on fresh install → complete wizard → `qa-gen config show` displays redacted config → `qa-gen db init` creates tables and confirms; re-run `db init` is safe.

- [X] T037 [US5] Implement `qa_gen/cli/commands/config.py`: `config_app = typer.Typer()`; `setup()` → Typer prompts for 10 fields in contracts/cli.md order (JIRA URL, JIRA email, JIRA API token with link note, Supabase URL, Supabase service_role key with inline note `"Use your project's service_role key — required for db init DDL and all runtime operations"`, Supabase DB URL with inline note `"Direct PostgreSQL connection string — required for 'db init'; find it in Supabase dashboard → Settings → Database → Connection string (URI mode)"`, AI provider `anthropic`/`gemini`, AI API key, AI model name, Voyage AI key); if `~/.qa-gen/.env` exists pre-fill each prompt's default from parsed file (Enter accepts); write `~/.qa-gen/.env` then `os.chmod(path, 0o600)`; `show()` → load `~/.qa-gen/.env` + print all keys with values — redact fields matching `_KEY`, `_TOKEN`, `_SECRET`, and `SUPABASE_DB_URL` (contains password) with `***` per FR-020/contracts/cli.md
- [X] T038 [US5] Implement `qa_gen/cli/commands/db.py`: `db_app = typer.Typer()`; `init()` → load settings; if `settings.SUPABASE_DB_URL` is None → `SystemExit(1)` with `"SUPABASE_DB_URL not set — run 'qa-gen config' and supply the direct PostgreSQL connection string"`; call `migrations.run_migrations(settings.SUPABASE_DB_URL)` which executes: pgvector extension → forms/components/aliases tables → IVFFlat indexes → `match_forms`/`match_components` RPCs; print confirmation per DDL step or specific error; idempotent (`IF NOT EXISTS` throughout) per FR-026/contracts/cli.md
- [X] T039 [US5] Replace stubs in `qa_gen/cli/main.py`: import `config_app` from `qa_gen.cli.commands.config` and `db_app` from `qa_gen.cli.commands.db`; wire `app.add_typer(config_app, name="config")` and `app.add_typer(db_app, name="db")`

**Checkpoint**: `qa-gen config` → `qa-gen config show` (redacted) → `qa-gen db init` (confirms tables created); re-run `db init` safe

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Verify cross-cutting behaviors and full end-to-end workflow

- [X] T040 [P] Verify `--verbose` flag wiring in all commands: `qa_gen/cli/commands/tests.py`, `forms.py`, `components.py`, `aliases.py`, `config.py`, `db.py` each must accept `verbose: bool` and pass it through to clients; when `True`, append structured debug output (request/response summaries, retry attempts, resolution steps) to `~/.qa-gen/debug.log` in all external client calls per FR-024
- [X] T041 [P] Audit exit codes in `qa_gen/cli/commands/tests.py`, `forms.py`, `components.py`, `aliases.py`, `config.py`, `db.py`: exit 0 success, 1 user error (invalid arg/missing config/non-TTY), 2 external service error (JIRA 404/Supabase failure), 3 KB error (form not found/missing parent), 4 AI error (timeout/malformed after retry); verify all `typer.Exit(code)` calls are in place per contracts/cli.md
- [X] T042 [P] Verify stderr routing across all commands: errors and warnings use `typer.echo(..., err=True)` or `Console(stderr=True)`; normal command output goes to stdout only; check all `SystemExit`, retry exhaustion, and warning messages per FR-024
- [X] T043 Run quickstart.md scenarios end-to-end: install via pipx → `qa-gen config` wizard → `qa-gen db init` → `qa-gen forms add` → `qa-gen forms show` → `qa-gen components add` → `qa-gen components show` → `qa-gen tests PROJ-xxx --dry-run` → `qa-gen tests PROJ-xxx --export md` → `qa-gen aliases add` → verify alias resolves in generation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — **BLOCKS all user stories**
- **Phase 3 (US1)**: Depends on Phase 2 — MVP deliverable
- **Phase 4 (US2)**: Depends on Phase 3 — extends form_resolver, component_resolver, orchestrator
- **Phase 5 (US3)**: Depends on Phase 2 — independent of US1/US2; parallel with Phase 3/4
- **Phase 6 (US4)**: Depends on Phase 2 — independent of US1–US3; parallel with Phase 3–5
- **Phase 7 (US5)**: Depends on Phase 2 (needs migrations.py) — independent; parallel with Phase 3–6
- **Phase 8 (Polish)**: Depends on all prior phases

### User Story Dependencies

- **US1 (P1)**: After Phase 2 — no inter-story deps; MVP path
- **US2 (P2)**: After US1 — modifies US1 components (form_resolver, component_resolver, orchestrator)
- **US3 (P2)**: After Phase 2 — independent (different CLI subgroup; no US1 code touched)
- **US4 (P3)**: After Phase 2 — independent (aliases CRUD only)
- **US5 (P4)**: After Phase 2 — independent; provides config wizard + db init

### Within Phase 3 (US1)

- T014–T024: all parallel (separate files, no cross-deps)
- T025 (orchestrator): after T014–T024 complete
- T026 (CLI command): after T025
- T027 (wire into main): after T026

### Parallel Opportunities

- T002, T003 (Setup): parallel after T001
- T005–T010, T012 (Foundational): all parallel after T004
- T014–T024 (US1 components): all parallel with each other
- T032, T033 (US3): parallel with each other; also parallel with US1 tasks
- T040, T041, T042 (Polish): parallel with each other

---

## Parallel Example: User Story 1

```bash
# All US1 component tasks run simultaneously (separate files):
T014: qa_gen/core/adf_parser.py
T015: qa_gen/core/jira_client.py
T016: qa_gen/knowledge_base/ui_vocabulary.md
T017: qa_gen/core/ai/base.py
T018: qa_gen/core/ai/claude_client.py
T019: qa_gen/core/ai/gemini_client.py
T020: qa_gen/core/form_resolver.py
T021: qa_gen/core/component_resolver.py
T022: qa_gen/core/context_assembler.py
T023: qa_gen/core/gherkin_parser.py
T024: qa_gen/core/jira_writer.py

# Then sequentially:
T025: qa_gen/core/orchestrator.py  (integrates all above)
T026: qa_gen/cli/commands/tests.py (CLI layer on top of orchestrator)
T027: qa_gen/cli/main.py           (wire in)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks everything)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: `qa-gen tests PROJ-1042 --dry-run` produces Gherkin
5. Demo / gather feedback before continuing

### Incremental Delivery

1. Phase 1+2 → Foundation ready
2. Phase 3 (US1) → Core feature: generate + display + push/export/edit/discard
3. Phase 4 (US2) → Quality gate: full alias + semantic resolution chain
4. Phase 5 (US3) → KB management: forms + components admin
5. Phase 6 (US4) → Alias management: QA team self-service vocabulary
6. Phase 7 (US5) → Config wizard + db init (onboarding flow)
7. Phase 8 → Polish + full quickstart validation

### Parallel Team Strategy (3 developers after Phase 2)

- **Dev A**: US1 (Phase 3) → US2 (Phase 4) — core generation pipeline
- **Dev B**: US3 (Phase 5) + US4 (Phase 6) — KB and alias management CLI
- **Dev C**: US5 (Phase 7) — config wizard + db init

---

## Notes

- [P] = different files, no blocking dependencies — safe to parallelize
- [US#] = traceability to user story
- No test tasks generated — not requested in spec
- Each story independently testable at its checkpoint
- Commit after each task or logical group; stop at checkpoints to validate
- `--verbose` and exit codes should be wired in during each command's implementation (Phase 3–7), then audited in Phase 8
