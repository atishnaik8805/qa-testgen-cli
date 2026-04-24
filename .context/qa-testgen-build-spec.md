# QA Test Case Generation Tool — Build Specification

> A CLI tool that accepts a JIRA story ID, resolves form-specific UI behavior from a knowledge base, and generates structured Gherkin test cases using Claude — pushing results back to JIRA automatically.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Core Architecture](#2-core-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Knowledge Base Design](#4-knowledge-base-design)
   - 4.5 [QA Vocabulary Mismatch](#45-qa-vocabulary-mismatch--the-core-problem)
   - 4.6 [Vocabulary Resolution — Three-Layer Chain](#46-vocabulary-resolution--three-layer-chain)
5. [CLI Interface](#5-cli-interface)
6. [System Flow](#6-system-flow)
7. [Component Specifications](#7-component-specifications)
8. [JIRA Story Conventions](#8-jira-story-conventions)
9. [Prompt Engineering](#9-prompt-engineering)
10. [Error Handling](#10-error-handling)
11. [Phased Rollout Plan](#11-phased-rollout-plan)
12. [Directory Structure](#12-directory-structure)
13. [Environment & Configuration](#13-environment--configuration)

---

## 1. Problem Statement

The testing team writes test cases manually for each JIRA story. The same word — for example, "save" — means different things depending on which form is under test. One form saves via a save icon click (`SAVE_EXPLICIT`), another saves automatically on field blur (`SAVE_ON_BLUR`). Without knowing the form context, an AI model will hallucinate generic test steps that don't reflect the actual UI behavior.

**Goal:** Give the QA team a single CLI command that takes a JIRA story ID and returns accurate, form-aware, Gherkin-formatted test cases — with zero ambiguity about UI interactions.

**The model must never infer UI behavior. It must only generate test steps from resolved, injected facts.**

---

## 2. Core Architecture

```
QA Tester
    │
    │  qa-gen tests PROJ-1042
    ▼
CLI (Typer + Rich)
    │
    ├──► JIRA MCP ──────────────► Fetch story { title, AC, labels, components }
    │                                      │
    │                              Extract form_id from labels
    │                                      │
    ▼                                      ▼
Orchestration Layer (Python)
    │
    ├──► Knowledge Base
    │       ├── Static .md  (UI vocabulary — always injected)
    │       ├── Vector DB   (form registry — retrieved by form_id)
    │       └── Vector DB   (component library — retrieved by form reference)
    │
    ├──► Assemble context (static + retrieved docs)
    │
    └──► Claude API (claude-sonnet-4-20250514)
              │
              └──► Test cases [ ] — Gherkin format
                        │
              ┌─────────┴──────────┐
              ▼                    ▼
        JIRA subtasks        Markdown export
        (via MCP write)      (--export md flag)
```

### Three-Layer Context Strategy

| Layer | Content | Storage | Injection |
|---|---|---|---|
| Layer 1 | UI behavioral vocabulary, save type definitions | Static `.md` file | Always — every request |
| Layer 2 | Per-form save behavior, field list, selectors | YAML in Vector DB | Retrieved by `form_id` |
| Layer 3 | Shared UI components (date pickers, inputs) | YAML in Vector DB | Retrieved by component reference |

---

## 3. Tech Stack

| Concern | Tool | Notes |
|---|---|---|
| Story source | JIRA via MCP | Pull story, AC, labels, components |
| AI generation | Claude Sonnet 4 (`claude-sonnet-4-20250514`) | Test case generation |
| Orchestration | Python 3.11+ | LangChain optional — raw `httpx` sufficient |
| CLI framework | `Typer` | Typed commands, subcommands, flags |
| Terminal output | `Rich` | Colored panels, spinners, tables |
| Vector DB | Supabase (`pgvector` extension) | SQL + semantic search, low ops overhead |
| Embedding model | Voyage AI `voyage-3` | Embed YAML form documents |
| Knowledge base - static | Markdown `.md` file | UI vocabulary, save behavior taxonomy |
| Knowledge base - dynamic | YAML files per form | Stored and queried via Supabase |
| Test output | JIRA subtasks via MCP write | Or Xray / Zephyr for dedicated test mgmt |
| Package manager | `uv` or `pip` | Python dependency management |

### Why Supabase over Pinecone

Supabase pgvector allows SQL filtering alongside vector search. This means retrieval can be scoped with `WHERE form_id = 'invoice_form'` instead of relying purely on cosine similarity scores. For a form registry of hundreds of documents, this is more predictable and cheaper to operate.

### Why Static `.md` for Layer 1

The behavioral vocabulary (definitions of `SAVE_ON_BLUR`, `SAVE_EXPLICIT`, etc.) must **always** be present. If it lived in the vector DB, a missed retrieval would cause the model to hallucinate terminology. Static injection eliminates that class of failure entirely.

---

## 4. Knowledge Base Design

### 4.1 Layer 1 — UI Vocabulary (Static `.md`)

File: `knowledge_base/ui_vocabulary.md`

This file is injected into every system prompt without exception.

```markdown
## Save Behaviors

- `SAVE_EXPLICIT`: User must click a visible save control (button or icon).
  - Test step: click [data-testid="save-icon"] or equivalent selector
- `SAVE_ON_BLUR`: Field persists automatically when focus leaves the element.
  - Test step: tab out of field or click elsewhere — no explicit save action
- `SAVE_ON_SUBMIT`: Entire form saved via a submit/confirm action.
  - Test step: click submit button or press Enter in last field
- `SAVE_AUTO`: Timed or change-event driven. No user action required.
  - Test step: wait N seconds after change, verify persistence

## Field Interaction Patterns

- `FOCUS_BLUR`: click field → type → click away
- `DROPDOWN_SELECT`: open dropdown → select option → (may trigger blur-save)
- `DATE_PICKER`: click date field → calendar opens → select or type → blur
- `FILE_UPLOAD`: click upload area → system file picker → select file → field populated

## Validation Timing

- `VALIDATE_ON_SAVE`: Errors shown only when save is attempted
- `VALIDATE_ON_BLUR`: Errors shown when field loses focus
- `VALIDATE_INLINE`: Errors shown as user types
```

---

### 4.2 Layer 2 — Form Registry (YAML per form)

Directory: `knowledge_base/forms/`

Each form is one YAML file. Forms may extend a base form to avoid duplication.

**Example — `invoice_form.yaml`:**

```yaml
form_id: invoice_form
display_name: Invoice Entry Form
module: Billing
save_behavior: SAVE_EXPLICIT
save_trigger: click → [data-testid="save-icon"]
save_disabled_until: all required fields are filled
validation_timing: VALIDATE_ON_SAVE

fields:
  - id: vendor_name
    label: Vendor Name
    type: text
    required: true
    save_on_blur: false
  - id: amount
    label: Amount
    type: number
    required: true
    save_on_blur: false
  - id: invoice_date
    label: Invoice Date
    type: date
    required: true
    component: date_picker_v2
    save_on_blur: false
  - id: notes
    label: Notes
    type: textarea
    required: false
    save_on_blur: false

components_used:
  - date_picker_v2
  - currency_input_v1

notes: >
  Save icon remains visually disabled until all required fields pass validation.
  Blur does NOT trigger save on any field in this form.
```

**Example — `user_profile_form.yaml`:**

```yaml
form_id: user_profile_form
display_name: User Profile
module: Account Settings
save_behavior: SAVE_ON_BLUR
save_trigger: blur event on each individual field
validation_timing: VALIDATE_ON_BLUR

fields:
  - id: display_name
    label: Display Name
    type: text
    required: true
    save_on_blur: true
  - id: email
    label: Email
    type: email
    required: true
    save_on_blur: true
  - id: avatar
    label: Profile Picture
    type: file
    required: false
    save_behavior: SAVE_EXPLICIT
    save_trigger: click → [data-testid="upload-confirm"]

notes: >
  No explicit save button exists. Each field saves independently on blur.
  Exception: avatar upload requires explicit confirm click.
```

**Inheritance pattern for form variants:**

```yaml
form_id: expense_form
extends: invoice_form
display_name: Expense Entry Form
overrides:
  save_behavior: SAVE_ON_BLUR
  fields:
    - id: receipt_upload
      label: Receipt
      type: file
      save_behavior: SAVE_EXPLICIT
      save_trigger: click → [data-testid="upload-confirm"]
```

---

### 4.3 Layer 3 — Component Library (YAML per component)

Directory: `knowledge_base/components/`

Each component YAML is written in **two voices simultaneously** — the developer canonical name and the QA plain-language description. This is the key structural decision that bridges the vocabulary gap between teams (see Section 4.5 for full detail).

**Example — `date_picker_v2.yaml`:**

```yaml
component_id: date_picker_v2
display_name: Date Picker v2
used_in:
  - invoice_form
  - expense_form
  - leave_request_form

interaction_steps:
  - click the date field to open the calendar overlay
  - select a date by clicking it, or type a date in DD/MM/YYYY format
  - calendar closes automatically; field value is set
  - blur is triggered after calendar closes

save_note: >
  date_picker_v2 triggers a blur event on close.
  Whether this causes a save depends on the parent form's save_behavior.
  On SAVE_ON_BLUR forms, selecting a date will trigger a save.
  On SAVE_EXPLICIT forms, selecting a date does NOT save.
```

---

### 4.4 Embedding Strategy

- Each YAML file is embedded as a single document (do not chunk by field)
- Embed using Voyage AI `voyage-3`
- Store in Supabase with metadata columns: `form_id`, `component_id`, `module`, `save_behavior`
- Retrieval uses metadata filter first, then cosine similarity for fuzzy fallback

```python
# Deterministic retrieval (preferred)
result = supabase.table("forms").select("*").eq("form_id", form_id).execute()

# Fuzzy fallback if form_id not found
result = supabase.rpc("match_forms", {
    "query_embedding": embed(story_text),
    "match_threshold": 0.75,
    "match_count": 1
})
```

---

### 4.5 QA Vocabulary Mismatch — The Core Problem

QA team members describe UI components in plain, observational language. Developers name components using technical identifiers. These vocabularies rarely overlap, and a retrieval system that depends on term matching will fail every time a QA member writes "date picker" when the KB stores `date_picker_v2`.

**Examples of the gap:**

| QA says | KB stores |
|---|---|
| "date picker" | `date_picker_v2` |
| "common editable table" | `shared-editable-table-component` |
| "the dropdown that searches as you type" | `typeahead_select_v3` |
| "search dropdown" | `typeahead_select_v3` |
| "the upload thing" | `file_upload_widget_v2` |
| "invoicing screen" | `invoice_form` |

The solution is a **three-layer resolution chain** that handles this gap progressively, without ever requiring QA members to learn developer terminology.

---

### 4.6 Vocabulary Resolution — Three-Layer Chain

#### Resolution Priority

| Priority | Method | Fires when | Latency |
|---|---|---|---|
| 1 | Alias table lookup | Term matches a known QA phrase | ~0ms |
| 2 | Semantic vector search (score > 0.80) | No alias, high-confidence embedding match | ~200ms |
| 3 | Top-3 confirmation prompt (score 0.65–0.80) | Ambiguous semantic match | human input |
| 4 | Free-text fallback (score < 0.65) | No match found | human types name |
| — | Auto-learn | After any Layer 3 resolution | next occurrence → Layer 1 |

---

#### Resolution Layer 1 — Alias Table (deterministic, ~0ms)

File: `knowledge_base/aliases.yaml`

A plain dictionary mapping every known QA phrase to the canonical `component_id` or `form_id`. No vector search, no AI — a single dictionary lookup. This resolves the majority of queries in production once the table is seeded.

```yaml
# knowledge_base/aliases.yaml

components:
  date_picker_v2:
    - date picker
    - datepicker
    - calendar input
    - date field
    - date selector
    - the calendar thing
    - calendar popup
    - the field that opens a calendar

  typeahead_select_v3:
    - search dropdown
    - searchable dropdown
    - dropdown that filters
    - dropdown with search
    - type to search dropdown
    - autocomplete field
    - the dropdown that searches as you type
    - live search dropdown

  shared_editable_table:
    - common editable table
    - editable grid
    - inline edit table
    - the table where you can type in cells
    - editable rows
    - table that lets you edit inline

  file_upload_widget_v2:
    - file uploader
    - upload button
    - attachment picker
    - drag and drop upload
    - the upload thing

forms:
  invoice_form:
    - invoice form
    - invoicing screen
    - the invoice page
    - billing entry form

  user_profile_form:
    - profile page
    - user profile
    - account settings form
    - my profile
```

Resolution is a single lookup:

```python
def resolve_from_aliases(term: str) -> str | None:
    normalized = term.lower().strip()
    for entity_id, aliases in alias_table["components"].items():
        if normalized in [a.lower() for a in aliases]:
            return entity_id
    for entity_id, aliases in alias_table["forms"].items():
        if normalized in [a.lower() for a in aliases]:
            return entity_id
    return None
```

**Who maintains it?** The QA team — not developers. A dedicated CLI command lets any tester add their own phrases:

```bash
❯ qa-gen aliases add "the calendar widget" --maps-to date_picker_v2
  ✓ Alias added: "the calendar widget" → date_picker_v2

❯ qa-gen aliases list --component typeahead_select_v3
  typeahead_select_v3 — Search dropdown
  Known aliases (6):
    · search dropdown
    · searchable dropdown
    · dropdown with search
    · autocomplete field
    · live search dropdown
    · the dropdown that searches as you type
```

---

#### Resolution Layer 2 — Semantic Vector Search

When an alias lookup misses, the system falls through to vector search. For this to work across the QA vocabulary gap, every component YAML must be written in **two voices**:

```yaml
# knowledge_base/components/typeahead_select_v3.yaml

component_id: typeahead_select_v3

# Voice 1: developer — canonical identifier and tech context
canonical_name: typeahead_select_v3
tech_stack: React · react-select wrapper

# Voice 2: QA — how testers describe this component
qa_descriptions:
  - search dropdown
  - dropdown that filters as you type
  - dropdown with a search box
  - live filter dropdown
  - autocomplete select field
  - the dropdown that lets you type to narrow options

# Voice 3: functional — plain English, bridges both vocabularies
plain_description: >
  A dropdown field that filters its options in real time as the user types.
  Clicking the field opens a list of options with a text input at the top.
  Typing narrows the list. Selecting an option closes the dropdown and
  populates the field. Pressing Escape cancels without selecting.

display_name: Search dropdown (typeahead)
used_in:
  - expense_form
  - leave_request_form
  - vendor_search_form

behaviors:
  open: click the field to open the dropdown and show all options
  filter: type any characters to narrow the list in real time
  select: click an option to select it and close the dropdown
  cancel: press Escape or click outside to close without selecting
  clear: click the × icon to clear the current selection
```

The `qa_descriptions` and `plain_description` fields are what get embedded. When a QA member writes "the dropdown that searches as you type", the embedding of that phrase has high cosine similarity to `plain_description` — even though no exact terms match the `component_id`.

```python
def resolve_from_vector(term: str) -> tuple[str | list, float]:
    query_embedding = voyage.embed(term)

    result = supabase.rpc("match_components", {
        "query_embedding": query_embedding,
        "match_threshold": 0.65,
        "match_count": 3
    })

    if not result:
        return None, 0.0

    top_score = result[0]["similarity"]

    if top_score > 0.80:
        return result[0]["component_id"], top_score   # confident — use directly

    return result[:3], top_score                       # ambiguous — pass to Layer 3
```

---

#### Resolution Layer 3 — Fuzzy Confirmation Prompt

When semantic search returns a result below the confidence threshold, the system presents the top 3 matches in plain QA language and lets the tester choose. It never silently uses a low-confidence result.

```
  Could not confidently identify the component you described:
  "the dropdown that lets you filter by typing"

  Did you mean one of these?

    [1] Search dropdown (typeahead_select_v3)
        A dropdown that filters options as you type

    [2] Basic dropdown (select_field_v1)
        A standard select with no search — opens a list of options

    [3] Multi-select dropdown (multi_select_v2)
        Lets you pick multiple options, each shown as a tag

  Enter 1, 2, or 3 — or type the name yourself:
```

After the tester picks, the system automatically adds the original phrase as an alias so it resolves at Layer 1 on every future occurrence:

```python
def confirm_and_learn(chosen_id: str, original_phrase: str):
    alias_table["components"][chosen_id].append(original_phrase.lower().strip())
    save_alias_table()

    console.print(f"  ✓ Added '{original_phrase}' as alias for {chosen_id}")
    console.print(f"  You won't be asked again for this phrase.")
```

This feedback loop means the alias table grows organically from real QA usage. Within a few weeks, Layer 1 resolves the vast majority of queries without any developer involvement.

---

#### The Two-Voice YAML Principle

Every component and form YAML in the KB must be written to serve both audiences. The three-field pattern is the standard:

```yaml
# Field 1: canonical_name — for developers and system internals
canonical_name: shared-editable-table-component

# Field 2: qa_descriptions — explicit QA phrases for alias seeding and embedding
qa_descriptions:
  - common editable table
  - editable grid
  - inline editable rows
  - the table where you can type in cells
  - table that lets you edit inline
  - the grid with editable cells

# Field 3: plain_description — functional plain English, bridges both vocabularies
plain_description: >
  A table where individual cells can be clicked to enter edit mode.
  Changes are made directly in the cell. Rows may have save or cancel
  buttons, or may auto-save on blur depending on the parent form's
  save behavior.
```

The `plain_description` is the most important field for semantic retrieval — it is written to match the kind of language a QA member would use in a JIRA story, not the kind a developer would use in a PR description.

---

#### Full Resolution Flow

```python
def resolve_component(term: str) -> str:
    # Layer 1: alias table — deterministic, O(1)
    result = resolve_from_aliases(term)
    if result:
        return result

    # Layer 2: semantic vector search
    result, score = resolve_from_vector(term)

    if isinstance(result, str) and score > 0.80:
        # High confidence — auto-resolve and log for alias promotion
        log_for_alias_review(term, result, score)
        return result

    if isinstance(result, list) and score > 0.65:
        # Low confidence — ask tester to confirm
        chosen = prompt_confirmation(result, term)
        confirm_and_learn(chosen, term)
        return chosen

    # Layer 4: free-text fallback
    return prompt_free_text(term, known_ids=kb.list_all_ids())
```

---

## 5. CLI Interface

### 5.1 Commands

```bash
# Primary command — generate test cases for a story
qa-gen tests <STORY_ID>

# Flags
--dry-run          # Generate and display but do not push to JIRA
--export md        # Save output to test-cases-<STORY_ID>.md
--export json      # Save output to test-cases-<STORY_ID>.json
--form <form_id>   # Override auto-detected form identity
--no-confirm       # Skip the action prompt, auto-push to JIRA

# Form knowledge base management
qa-gen forms list                    # List all forms in KB with save behavior
qa-gen forms add <form_id>           # Add or update a form from YAML file
qa-gen forms show <form_id>          # Print resolved form doc (with inheritance)
qa-gen forms validate <form_id>      # Validate YAML schema

# Alias / vocabulary management (QA team self-service)
qa-gen aliases add "<phrase>" --maps-to <component_id>   # Add a new alias
qa-gen aliases list --component <component_id>            # List all aliases for a component
qa-gen aliases list --form <form_id>                      # List all aliases for a form
qa-gen aliases remove "<phrase>"                          # Remove a stale alias

# Configuration
qa-gen config                        # Interactive setup wizard
qa-gen config show                   # Print current config (redacted secrets)
```

### 5.2 Terminal Output Flow

```
❯ qa-gen tests PROJ-1042

  Connecting to JIRA via MCP...
  ✓ Story fetched: PROJ-1042 · [invoice_form] User can save partial entries
  Labels: invoice_form  save-behavior  regression

  ✓ Form identified: invoice_form
  ✓ Form doc loaded   save_behavior: SAVE_EXPLICIT · trigger: [data-testid="save-icon"]
  ✓ Components found  date_picker_v2 · currency_input_v1
  Generating test cases via Claude...

  ──────────────────────────────────────────────
  TC-01 · Save with all mandatory fields filled
  ──────────────────────────────────────────────
  Given  the invoice form is open and vendor_name, amount, date are filled
  When   the user clicks [data-testid="save-icon"]
  Then   the record is persisted and a success toast appears

  ──────────────────────────────────────────────
  TC-02 · Save with mandatory fields missing
  ──────────────────────────────────────────────
  Given  the invoice form is open with amount left blank
  When   the user clicks [data-testid="save-icon"]
  Then   the save icon is disabled, inline error shown on amount field

  ──────────────────────────────────────────────
  TC-03 · Save does NOT trigger on blur
  ──────────────────────────────────────────────
  Given  the user fills vendor_name and tabs to the next field
  When   focus leaves vendor_name
  Then   no save occurs — data only persists on explicit save-icon click

  ? What would you like to do?
    [1] Push all to JIRA as subtasks
    [2] Export to test-cases-PROJ-1042.md
    [3] Edit before saving
    [4] Discard
❯ 1

  ✓ 5 test cases pushed to JIRA as subtasks of PROJ-1042
```

### 5.3 CLI Implementation (Typer skeleton)

```python
import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(help="QA test case generator powered by Claude")
console = Console()

@app.command()
def tests(
    story_id: str = typer.Argument(..., help="JIRA story ID e.g. PROJ-1042"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    export: str = typer.Option(None, "--export", help="md or json"),
    form: str = typer.Option(None, "--form", help="Override form_id"),
    no_confirm: bool = typer.Option(False, "--no-confirm"),
):
    with console.status("Fetching story from JIRA..."):
        story = jira_mcp.get_issue(story_id)
    
    form_id = form or resolve_form_id(story)
    context = assemble_context(form_id, story)
    test_cases = generate_test_cases(context, story)
    
    display_test_cases(test_cases)
    
    if not dry_run:
        action = prompt_action() if not no_confirm else "push"
        handle_action(action, story_id, test_cases, export)

if __name__ == "__main__":
    app()
```

---

## 6. System Flow

### 6.1 High-Level Flow (per request)

```
1. Tester runs:  qa-gen tests PROJ-1042
2. CLI calls:    JIRA MCP → get_issue("PROJ-1042")
3. JIRA returns: { title, description, acceptance_criteria, labels, components }
4. CLI extracts: form_id from labels (e.g. "invoice_form")
5. Orchestrator queries:
     a. Supabase → form doc for invoice_form
     b. Supabase → component docs used by invoice_form
     c. Local filesystem → ui_vocabulary.md
6. Orchestrator assembles: system_prompt + user_prompt
7. Claude API returns: test_cases[] in Gherkin format
8. CLI displays test cases and prompts tester for action
9. On approval: JIRA MCP → create_subtasks(parent=PROJ-1042, test_cases)
```

### 6.2 Form Identity Resolution

```python
def resolve_form_id(story: dict) -> str:
    # Step 1: deterministic — check JIRA labels
    known_forms = kb.list_all_form_ids()
    for label in story["labels"]:
        if label in known_forms:
            return label
    
    # Step 2: fuzzy — extract from story text via Claude
    response = claude.complete(
        system="Extract the form name from the story. Reply with only the form_id.",
        user=f"Story: {story['title']}\n\n{story['description']}",
        valid_options=known_forms
    )
    if response in known_forms:
        return response
    
    # Step 3: ask tester
    return typer.prompt(
        f"Could not detect form. Available forms: {known_forms}\nEnter form_id"
    )
```

---

## 7. Component Specifications

### 7.1 JIRA MCP Integration

```python
# Fetching a story
story = jira_mcp.get_issue(story_id)
# Returns: summary, description, acceptance_criteria (custom field),
#          labels, components, issue_type, status

# Writing subtasks
for tc in test_cases:
    jira_mcp.create_issue({
        "project": project_key,
        "issuetype": "Subtask",
        "parent": story_id,
        "summary": tc["title"],
        "description": tc["gherkin"],
        "labels": ["auto-generated", "qa-gen"]
    })
```

### 7.2 Vector DB (Supabase pgvector)

```sql
-- Schema
create table forms (
  id uuid primary key default gen_random_uuid(),
  form_id text unique not null,
  display_name text,
  module text,
  save_behavior text,
  content text,           -- full YAML as text
  embedding vector(1024)  -- voyage-3 dimensionality
);

create table components (
  id uuid primary key default gen_random_uuid(),
  component_id text unique not null,
  used_in text[],
  content text,
  embedding vector(1024)
);

-- Similarity search function
create or replace function match_forms(
  query_embedding vector(1024),
  match_threshold float,
  match_count int
)
returns table(form_id text, content text, similarity float)
language sql stable as $$
  select form_id, content, 1 - (embedding <=> query_embedding) as similarity
  from forms
  where 1 - (embedding <=> query_embedding) > match_threshold
  order by similarity desc
  limit match_count;
$$;
```

### 7.3 Claude API Call

```python
import httpx

def generate_test_cases(context: dict, story: dict) -> list[dict]:
    system_prompt = f"""
You are a QA engineer generating structured test cases.

## UI Behavioral Vocabulary
{context['static_vocabulary']}

## Form Under Test
{context['form_doc']}

## Shared Components Used by This Form
{context['component_docs']}

## Rules
- Never assume or infer save behavior. Use only what is in "Form Under Test".
- Generate positive cases, negative cases, and edge cases.
- For each field marked save_on_blur: true, write a test verifying blur triggers save.
- For forms with SAVE_EXPLICIT: write a test verifying blur does NOT save.
- Output format: Gherkin (Given / When / Then).
- Reference exact selectors where provided (e.g. [data-testid="save-icon"]).
- Each test case must have: title, preconditions, steps, expected result.
"""

    user_prompt = f"""
Story: {story['title']}

Acceptance Criteria:
{story['acceptance_criteria']}

Description:
{story['description']}

Generate complete test cases for this story.
"""

    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": config.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}]
        }
    )
    return parse_test_cases(response.json()["content"][0]["text"])
```

---

## 8. JIRA Story Conventions

For the tool to work deterministically, QA and dev teams should follow these conventions when writing stories.

### 8.1 Required Fields

| Field | Convention | Example |
|---|---|---|
| **Labels** | Always include `form_id` as a label | `invoice_form` |
| **Labels** | Include test type tag | `regression`, `smoke`, `e2e` |
| **Acceptance Criteria** | Use Given/When/Then where possible | See below |
| **Components** | Map to module name | `Billing`, `Account Settings` |

### 8.2 Ideal Story Template

```
Title: [FormName] — <what the user can do>
Example: [Invoice Form] — User can save a partial entry

Labels: invoice_form, save-behavior, regression

Acceptance Criteria:
- Given the invoice form is open
- When the user fills vendor_name and amount and clicks the save icon
- Then the record is saved and a success toast is shown
- And the form remains open for further editing

Components: Billing
```

### 8.3 Form ID Naming Convention

Form IDs must be lowercase, snake_case, and match the YAML filename exactly.

```
invoice_form         → knowledge_base/forms/invoice_form.yaml
user_profile_form    → knowledge_base/forms/user_profile_form.yaml
expense_form         → knowledge_base/forms/expense_form.yaml
leave_request_form   → knowledge_base/forms/leave_request_form.yaml
```

---

## 9. Prompt Engineering

### 9.1 System Prompt Structure

```
[Section 1 — Role]
You are a QA engineer generating structured test cases.

[Section 2 — UI Vocabulary]
<contents of ui_vocabulary.md>

[Section 3 — Form Under Test]
<resolved form YAML, with inheritance flattened>

[Section 4 — Components Used]
<relevant component YAMLs>

[Section 5 — Rules]
- Never infer save behavior. Use only the form doc.
- Generate positive, negative, and edge cases.
- Output Gherkin: Given / When / Then.
- Reference selectors exactly as specified.
```

### 9.2 Key Prompt Rules

**Never leave save behavior ambiguous.** The prompt must always contain a `Form Under Test` section with `save_behavior` and `save_trigger` explicitly stated.

**Flatten inheritance before injection.** If `expense_form` extends `invoice_form`, resolve the full merged document before injecting. The model should never see raw inheritance — only the resolved output.

**Specify output format.** Ask for JSON-structured test cases so they can be parsed and formatted by Rich. Example output schema:

```json
[
  {
    "title": "Save with all mandatory fields filled",
    "type": "positive",
    "preconditions": ["Invoice form is open", "User is logged in"],
    "steps": [
      "Fill vendor_name with 'Acme Corp'",
      "Fill amount with '1000'",
      "Select date using date_picker_v2",
      "Click [data-testid='save-icon']"
    ],
    "expected_result": "Record is persisted, success toast appears, form remains open"
  }
]
```

### 9.3 Anti-Hallucination Guardrails

| Risk | Mitigation |
|---|---|
| Model invents a save button | Form doc explicitly states `save_trigger` selector |
| Model assumes blur saves | Form doc explicitly states `save_on_blur: false` per field |
| Model generates wrong component interaction | Component YAML injected with exact interaction steps |
| Form not in KB | System halts and alerts tester — never falls through to model |
| Ambiguous story | Low-confidence flag shown to tester before generation |

---

## 10. Error Handling

### 10.1 Failure Modes and Responses

| Failure | Detection | Response |
|---|---|---|
| JIRA story not found | MCP returns 404 | Print error: "Story PROJ-1042 not found in JIRA" |
| No acceptance criteria | `story.AC` is empty | Warn tester, extract implicit AC from description, flag as low confidence |
| Form ID not resolvable | Not in labels, NLP fails | Prompt tester: "Which form? (list all)" |
| Form not in knowledge base | DB returns no result | Block generation: "Add invoice_form to KB first — run: `qa-gen forms add invoice_form`" |
| Claude returns malformed JSON | Parse error | Retry once with stricter JSON prompt, then fall back to raw text display |
| JIRA write-back fails | MCP returns error | Save to local `.md` as fallback, show path to tester |

### 10.2 Confidence Flag

When story quality is low (missing AC, form detected via NLP not label), display a confidence warning before generating:

```
  ⚠ Low confidence — form detected via text analysis, not label
  Detected: invoice_form
  Confirm? [Y/n]
```

---

## 11. Phased Rollout Plan

### Phase 1 — Knowledge Base Seed (Week 1–2)

- Write `ui_vocabulary.md`
- Create YAML docs for top 10 most-tested forms
- Create YAML docs for all shared UI components
- Set up Supabase project, embed and ingest all YAMLs
- Manual test: verify retrieval returns correct form doc for each form_id

### Phase 2 — CLI + Generation (Week 3–4)

- Implement `qa-gen tests` command
- Wire JIRA MCP read
- Wire Claude API call with assembled context
- Implement Rich terminal output
- Dry-run mode only — no write-back yet
- QA team reviews generated output for 2 weeks

### Phase 3 — Write-back + Feedback Loop (Week 5–6)

- Implement JIRA MCP subtask creation
- Add `--export md` and `--export json` flags
- Capture rejected test cases to a feedback log
- Use feedback log to identify KB gaps

### Phase 4 — Automation Trigger (Week 7+)

- JIRA automation rule: story moves to "Ready for QA" → webhook fires pipeline
- Test cases created as draft subtasks automatically
- Human review gate: QA lead approves before subtasks become active
- KB maintenance process: monthly review of feedback log → update YAMLs

---

## 12. Directory Structure

```
qa-testgen/
├── README.md
├── pyproject.toml
├── .env.example
│
├── cli/
│   ├── __init__.py
│   ├── main.py              # Typer app entry point
│   ├── commands/
│   │   ├── tests.py         # qa-gen tests
│   │   ├── forms.py         # qa-gen forms
│   │   └── config.py        # qa-gen config
│   └── display.py           # Rich output helpers
│
├── core/
│   ├── jira_mcp.py          # JIRA MCP client
│   ├── orchestrator.py      # Main pipeline logic
│   ├── form_resolver.py     # Form identity resolution
│   ├── alias_resolver.py    # Alias table + vocabulary resolution chain
│   ├── context_assembler.py # Build system prompt context
│   ├── claude_client.py     # Anthropic API calls
│   └── jira_writer.py       # Write test cases back to JIRA
│
├── knowledge_base/
│   ├── ui_vocabulary.md     # Layer 1 — always injected
│   ├── aliases.yaml         # QA phrase → component_id / form_id map
│   ├── forms/
│   │   ├── invoice_form.yaml
│   │   ├── user_profile_form.yaml
│   │   ├── expense_form.yaml
│   │   └── ...
│   └── components/
│       ├── date_picker_v2.yaml
│       ├── currency_input_v1.yaml
│       ├── typeahead_select_v3.yaml
│       ├── shared_editable_table.yaml
│       └── ...
│
├── scripts/
│   ├── ingest_kb.py         # Embed and upload YAMLs to Supabase
│   └── validate_kb.py       # Validate all YAML files against schema
│
└── tests/
    ├── test_form_resolver.py
    ├── test_context_assembler.py
    └── test_claude_output_parser.py
```

---

## 13. Environment & Configuration

### 13.1 `.env` File

```bash
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# JIRA
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your@email.com
JIRA_API_TOKEN=...
JIRA_PROJECT_KEY=PROJ

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=...

# Voyage AI (embeddings)
VOYAGE_API_KEY=...

# App config
DEFAULT_EXPORT_DIR=./exports
LOG_LEVEL=INFO
CONFIDENCE_THRESHOLD=0.75
```

### 13.2 Installation

```bash
# Clone repo
git clone https://github.com/yourorg/qa-testgen
cd qa-testgen

# Install dependencies
pip install -e .

# Configure
qa-gen config

# Seed the knowledge base
python scripts/ingest_kb.py

# Run first test generation (dry run)
qa-gen tests PROJ-1042 --dry-run
```

### 13.3 Dependencies (`pyproject.toml`)

```toml
[project]
name = "qa-testgen"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "typer[all]>=0.12",
    "rich>=13.0",
    "httpx>=0.27",
    "supabase>=2.0",
    "voyageai>=0.2",
    "pyyaml>=6.0",
    "python-dotenv>=1.0",
    "pydantic>=2.0",
]
```

---

*This document was generated from a design session covering: RAG architecture decisions, contextual UI knowledge base design, QA vocabulary mismatch resolution (alias table + semantic embedding + confirmation loop), CLI tooling, JIRA MCP integration, and prompt engineering for hallucination suppression in test case generation.*
