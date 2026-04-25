# Quickstart: qa-gen

**Branch**: `001-qa-testgen-cli` | **Date**: 2026-04-24  
**Version**: v1 (flat-file KB — no Supabase, no embeddings)

---

## Prerequisites

- Python 3.11+
- `pipx` installed
- Atlassian Cloud JIRA instance with API token access
- Anthropic or Google Gemini API key

> **v2 only:** Supabase project and Voyage AI API key are required in v2 for shared vector KB storage and semantic search.

---

## 1. Install

```bash
pipx install git+<repo-url>
```

Verify:

```bash
qa-gen --help
```

---

## 2. Configure

Run the interactive wizard. It will create `~/.qa-gen/.env` (mode 600).

```bash
qa-gen config
```

You will be prompted for:
1. JIRA URL (`https://yourcompany.atlassian.net`)
2. JIRA email and API token
3. AI provider (`anthropic` or `gemini`), API key, and model name
4. Knowledge base path (default: `./knowledge_base`)

Verify config:

```bash
qa-gen config show
```

> **v2 only:** Config wizard also collects Supabase URL, service_role key, Supabase DB URL, and Voyage AI API key in v2.

---

## 3. Set Up the Knowledge Base

The knowledge base is a local directory of YAML files committed alongside the codebase. Create the structure:

```bash
mkdir -p knowledge_base/forms
mkdir -p knowledge_base/components
```

Or point `KB_PATH` in `~/.qa-gen/.env` to an existing directory. Default is `./knowledge_base` relative to wherever you run `qa-gen`.

No database initialization required in v1.

> **v2 only:** `qa-gen db init` creates Supabase tables and enables pgvector. Required once per team after `qa-gen config` in v2.

---

## 4. Seed the Knowledge Base

### Add a form

Create your form YAML (see `data-model.md` for schema), then place it in the forms directory. The filename must match `form_id`:

```bash
cp invoice_form.yaml knowledge_base/forms/invoice_form.yaml
```

Verify:

```bash
qa-gen forms list
qa-gen forms show invoice_form
```

### Add a component

```bash
cp date_picker_v2.yaml knowledge_base/components/date_picker_v2.yaml
```

Verify:

```bash
qa-gen components list
qa-gen components show date_picker_v2
```

> **v2 only:** `qa-gen forms add <form_id> --file <path>` and `qa-gen components add <component_id> --file <path>` embed via Voyage AI and upsert to Supabase in v2 — shared instantly across the team.

---

## 5. Generate Test Cases

Make sure the JIRA story has a label matching a `form_id` in `knowledge_base/forms/` — that is how `qa-gen` auto-detects the form.

```bash
# Dry run — see output without writing to JIRA
qa-gen tests PROJ-1042 --dry-run

# Full run — generates, displays via $PAGER, then prompts for action
qa-gen tests PROJ-1042

# Export to Markdown immediately (skip action prompt)
qa-gen tests PROJ-1042 --export md

# Override auto-detected form
qa-gen tests PROJ-1042 --form invoice_form

# Automation pipeline (no prompt, push + export)
qa-gen tests PROJ-1042 --no-confirm --export json
```

Output file locations (current working directory):
- `test-cases-PROJ-1042.md`
- `test-cases-PROJ-1042.json` (Zephyr Scale Cloud import format)

---

## 6. Manage Vocabulary Aliases

Aliases map plain-language QA phrases to known form or component IDs. Stored in `knowledge_base/aliases.yaml` — commit this file to share with the team.

```bash
# Add alias so "the calendar thing" resolves to date_picker_v2
qa-gen aliases add "the calendar thing" --maps-to date_picker_v2

# List all aliases
qa-gen aliases list

# Remove a stale alias
qa-gen aliases remove "the calendar thing"
```

> **v2 only:** Aliases are stored in a shared Supabase table in v2 — visible to all team members instantly without a git commit or pull.

---

## 7. Debug Mode

Pass `--verbose` to any command. Debug output is appended to `~/.qa-gen/debug.log`.

```bash
qa-gen tests PROJ-1042 --dry-run --verbose
tail -f ~/.qa-gen/debug.log
```

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `"Story PROJ-1042 not found in JIRA"` | Wrong story ID or no JIRA access | Check story ID; verify JIRA credentials in `qa-gen config show` |
| `"Form invoice_form not in KB — add YAML to ..."` | Form YAML not in `knowledge_base/forms/` | Copy YAML to `knowledge_base/forms/invoice_form.yaml` |
| `"No forms in KB — add YAML files to ..."` | Knowledge base directory is empty | Add at least one form YAML to `knowledge_base/forms/` |
| `"warning: could not auto-detect form from labels"` | Story has no label matching a known `form_id` | Add correct label to JIRA story, or re-run with `--form <form_id>` |
| `"component '...' not found in KB — skipping"` | Component YAML missing | Copy component YAML to `knowledge_base/components/<id>.yaml` |
| `"interactive prompt unavailable in non-TTY"` | Running in CI without flags | Add `--dry-run` or `--no-confirm` |
| `"--no-confirm ignored: --dry-run is active"` | Both flags passed | Expected behavior — `--dry-run` wins |
| Config file permissions warning | `~/.qa-gen/.env` mode is not 600 | `chmod 600 ~/.qa-gen/.env` |
