# CLI Contract: qa-gen

**Branch**: `001-qa-testgen-cli` | **Date**: 2026-04-24  
**Version**: v1 (flat-file KB). Sections marked **v2 only** are implemented but not active in v1 — see `v1-migration-log.md`.

All commands write errors and warnings to **stderr**. All normal output to **stdout**. Exit code 0 = success; non-zero = error.

---

## `qa-gen tests <STORY_ID>`

Generate test cases for a JIRA story.

```
qa-gen tests <STORY_ID> [OPTIONS]
```

| Arg / Flag | Type | Required | Default | Description |
|---|---|---|---|---|
| `STORY_ID` | string | yes | — | JIRA story ID, e.g. `PROJ-1042` |
| `--dry-run` | flag | no | false | Display test cases without writing to JIRA. Takes precedence over all write flags. |
| `--export` | `md\|json` | no | — | Skip action prompt; write file immediately. Both `--export md --export json` allowed simultaneously. |
| `--form <form_id>` | string | no | — | Override auto-detected form; error immediately if form_id not in KB. |
| `--no-confirm` | flag | no | false | Skip action prompt; auto-push all test cases to JIRA. |
| `--verbose` | flag | no | false | Write debug log to `~/.qa-gen/debug.log`. |

**Conflict rules**:
- `--dry-run` + `--no-confirm`: `--dry-run` wins; warn to stderr: `"--no-confirm ignored: --dry-run is active"`
- `--dry-run` + `--export`: export still writes file; JIRA write suppressed
- `--no-confirm` + `--export`: both execute additively (export file + push to JIRA)
- Non-TTY + no `--dry-run` + no `--no-confirm`: exit 1 with stderr: `"interactive prompt unavailable in non-TTY — use --dry-run or --no-confirm"`

**Output files**:
- `--export md` → `test-cases-<STORY_ID>.md` (current working directory)
- `--export json` → `test-cases-<STORY_ID>.json` (Zephyr Scale Cloud import format)
- Both flags → both files written additively; existing files silently overwritten

**Test case limit**: Max 15 per story. If AI returns more, truncate to first 15 and warn to stderr.

**JIRA write-back failure**: Auto-save to `test-cases-<STORY_ID>.md` and print path to stderr.

---

## `qa-gen forms`

Manage form knowledge base entries.

### `qa-gen forms list`

```
qa-gen forms list
```

Outputs a table of all registered forms with columns: `form_id`, `display_name`, `save_behavior`, `module`.

### `qa-gen forms add <form_id> --file <path>`

> **v2 only:** This command is not available in v1. In v1, add forms by copying YAML files directly to `knowledge_base/forms/<form_id>.yaml`.

```
qa-gen forms add <form_id> --file <path>
```

| Arg / Flag | Type | Required | Description |
|---|---|---|---|
| `form_id` | string | yes | Target form ID. Must match `form_id` field in YAML. |
| `--file <path>` | path | yes | Path to form YAML file. No default path. |

Steps:
1. Parse and validate YAML against Form schema
2. Check `yaml["form_id"] == cli_arg` — abort with validation error if mismatch
3. If `extends` set, verify parent exists in KB — abort if missing
4. Embed YAML content via Voyage AI *(v2 only)*
5. Upsert to Supabase `forms` table *(v2 only)*

### `qa-gen forms show <form_id>`

```
qa-gen forms show <form_id>
```

Prints the fully resolved form definition with inheritance flattened (all parent fields merged, child overrides applied). Output is human-readable YAML.

### `qa-gen forms validate <form_id> --file <path>`

```
qa-gen forms validate <form_id> --file <path>
```

Validates YAML schema only — no write to Supabase. Reports errors with offending key name and remediation hint.

---

## `qa-gen components`

Manage component knowledge base entries.

### `qa-gen components list`

```
qa-gen components list
```

Outputs a table: `component_id`, `label`, `forms` (comma-separated form_ids).

### `qa-gen components add <component_id> --file <path>`

> **v2 only:** This command is not available in v1. In v1, add components by copying YAML files directly to `knowledge_base/components/<component_id>.yaml`.

```
qa-gen components add <component_id> --file <path>
```

| Arg / Flag | Type | Required | Description |
|---|---|---|---|
| `component_id` | string | yes | Target component ID. Must match `id` field in YAML. |
| `--file <path>` | path | yes | Path to component YAML file. No default path. |

Steps:
1. Parse and validate YAML against Component schema
2. Check `yaml["id"] == cli_arg` — abort with validation error if mismatch
3. Embed YAML content via Voyage AI *(v2 only)*
4. Upsert to Supabase `components` table *(v2 only)*

### `qa-gen components show <component_id>`

```
qa-gen components show <component_id>
```

Prints full component definition including all fields and interaction steps.

---

## `qa-gen aliases`

Manage QA vocabulary aliases.

**v1**: Stored in `knowledge_base/aliases.yaml` — local file, shared via git.  
**v2**: Stored in Supabase `aliases` table — shared across team instantly, no git commit needed.

### `qa-gen aliases add "<phrase>" --maps-to <target_id>`

```
qa-gen aliases add "<phrase>" --maps-to <target_id>
```

| Arg / Flag | Type | Required | Description |
|---|---|---|---|
| `phrase` | string | yes | Plain-language QA phrase (quoted). Stored as lowercase. |
| `--maps-to <target_id>` | string | yes | `form_id` or `component_id` to map to. |
| `--force` | flag | no | Overwrite if phrase already exists with different target. |

Error if phrase already maps to a **different** target: display current mapping, exit non-zero. Re-run with `--force` to overwrite.

### `qa-gen aliases list`

```
qa-gen aliases list [--component <component_id>] [--form <form_id>]
```

| Flag | Type | Required | Description |
|---|---|---|---|
| `--component <id>` | string | no | Filter to aliases for a specific component. |
| `--form <id>` | string | no | Filter to aliases for a specific form. |

Without filters: lists all aliases.

### `qa-gen aliases remove "<phrase>"`

```
qa-gen aliases remove "<phrase>"
```

Removes alias. Errors if phrase not found.  
**v1**: Deletes from `knowledge_base/aliases.yaml`.  
**v2**: Deletes from Supabase `aliases` table.

---

## `qa-gen config`

Interactive setup wizard. Persists to `~/.qa-gen/.env` (mode 600).

```
qa-gen config
```

**v1** — Wizard collects (in order):
1. JIRA URL — `https://<domain>.atlassian.net`
2. JIRA username — email address
3. JIRA API Token — displayed note: "Create at https://id.atlassian.com/manage-profile/security/api-tokens"
4. AI provider — choices: `anthropic`, `gemini`
5. AI provider API key
6. AI model name — e.g. `claude-sonnet-4-20250514` or `gemini-2.5-flash`
7. Knowledge base path — default: `./knowledge_base`

> **v2 only:** Config wizard also collects: Supabase URL (field 4), Supabase service_role key (field 5, note: "Use your project's service_role key — required for db init DDL and all runtime operations"), Supabase DB URL (field 6, note: "Direct PostgreSQL connection string — required for 'db init'"; optional at wizard time), and Voyage AI API key (field 10). Total 10 fields in v2 vs 7 in v1.

**Re-run behavior**: Pre-fills prompts with existing values. Tester presses Enter to accept unchanged fields.

### `qa-gen config show`

```
qa-gen config show
```

Prints all settings from `~/.qa-gen/.env` with secrets redacted (replaced with `***`).

---

## `qa-gen db init`

> **v2 only:** This command is not available in v1. No database setup is required in v1 — the knowledge base is local YAML files.

Create Supabase tables and enable pgvector extension.

```
qa-gen db init
```

Operations (idempotent — safe to re-run):
1. `CREATE EXTENSION IF NOT EXISTS vector`
2. `CREATE TABLE IF NOT EXISTS forms (...)` with embedding column `VECTOR(1024)`
3. `CREATE TABLE IF NOT EXISTS components (...)` with embedding column `VECTOR(1024)`
4. `CREATE TABLE IF NOT EXISTS aliases (...)`
5. Create IVFFlat indexes for cosine similarity search
6. Create similarity search RPC functions (`match_forms`, `match_components`)

Requires `service_role` key. Confirms success or prints specific DDL error.

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | User error (invalid arg, missing flag, config not found) |
| `2` | External service error (JIRA 404, Supabase connection failure) |
| `3` | KB error (form not found, component not found, parent missing) |
| `4` | AI generation error (timeout, malformed output after retry) |

---

## Environment Variables (set by `qa-gen config`)

All variables read from `~/.qa-gen/.env`. The tool does **not** read from shell environment or project `.env` files.

**v1** — required variables:

```bash
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=you@company.com
JIRA_API_TOKEN=...
AI_PROVIDER=anthropic            # anthropic | gemini
AI_API_KEY=...
AI_MODEL_NAME=claude-sonnet-4-20250514
KB_PATH=./knowledge_base         # path to local YAML knowledge base
```

> **v2 only:** Also requires:
> ```bash
> SUPABASE_URL=https://xxx.supabase.co
> SUPABASE_SERVICE_KEY=...
> SUPABASE_DB_URL=postgresql://postgres.xxx:password@aws-0-region.pooler.supabase.com:6543/postgres
> VOYAGE_API_KEY=...
> ```
