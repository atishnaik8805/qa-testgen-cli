# Data Model: QA Test Case Generation CLI

**Branch**: `001-qa-testgen-cli` | **Date**: 2026-04-24  
**Version note**: Supabase schema section is v2 only. Pydantic models and YAML schemas apply to both v1 and v2.

---

## Supabase Schema

> **v2 only:** The SQL schema below is not used in v1. v1 stores all KB data as YAML files in `knowledge_base/forms/` and `knowledge_base/components/`. No database initialization required in v1.

### Extension

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

### Table: `forms`

```sql
CREATE TABLE IF NOT EXISTS forms (
    id           UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    form_id      TEXT    UNIQUE NOT NULL,          -- snake_case identifier, e.g. invoice_form
    display_name TEXT,
    module       TEXT,
    save_behavior TEXT NOT NULL,                   -- enum: auto, manual, blur (SAVE_EXPLICIT etc)
    save_trigger  TEXT NOT NULL,                   -- e.g. "click → [data-testid=\"save-icon\"]"
    parent_form_id TEXT REFERENCES forms(form_id), -- NULL if no inheritance (extends field)
    content      TEXT NOT NULL,                    -- full YAML text (canonical store)
    embedding    VECTOR(1024),                     -- voyage-3-large output
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);
```

**Indexes**:
```sql
CREATE INDEX IF NOT EXISTS forms_embedding_idx ON forms USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS forms_form_id_idx   ON forms (form_id);
```

**Similarity search RPC**:
```sql
CREATE OR REPLACE FUNCTION match_forms(
    query_embedding VECTOR(1024),
    match_threshold FLOAT,
    match_count     INT
)
RETURNS TABLE(form_id TEXT, display_name TEXT, save_behavior TEXT, content TEXT, similarity FLOAT)
LANGUAGE SQL STABLE AS $$
    SELECT
        form_id,
        display_name,
        save_behavior,
        content,
        1 - (embedding <=> query_embedding) AS similarity
    FROM forms
    WHERE 1 - (embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
$$;
```

---

### Table: `components`

```sql
CREATE TABLE IF NOT EXISTS components (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    component_id TEXT UNIQUE NOT NULL,             -- snake_case identifier, e.g. date_picker_v2
    label       TEXT NOT NULL,                     -- human display name
    description TEXT NOT NULL,                     -- plain English for semantic retrieval
    interaction_steps TEXT[] NOT NULL,             -- ordered interaction steps
    save_behavior_notes TEXT,
    forms        TEXT[],                           -- form_ids this component appears in
    content      TEXT NOT NULL,                    -- full YAML text
    embedding    VECTOR(1024),
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);
```

**Indexes**:
```sql
CREATE INDEX IF NOT EXISTS components_embedding_idx ON components USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS components_id_idx        ON components (component_id);
```

**Similarity search RPC**:
```sql
CREATE OR REPLACE FUNCTION match_components(
    query_embedding VECTOR(1024),
    match_threshold FLOAT,
    match_count     INT
)
RETURNS TABLE(component_id TEXT, label TEXT, description TEXT, similarity FLOAT)
LANGUAGE SQL STABLE AS $$
    SELECT
        component_id,
        label,
        description,
        1 - (embedding <=> query_embedding) AS similarity
    FROM components
    WHERE 1 - (embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
$$;
```

---

### Table: `aliases`

```sql
CREATE TABLE IF NOT EXISTS aliases (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phrase      TEXT NOT NULL,                     -- normalized lowercase phrase
    target_id   TEXT NOT NULL,                     -- form_id or component_id
    target_type TEXT NOT NULL CHECK (target_type IN ('form', 'component')),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

**Constraints**:
```sql
CREATE UNIQUE INDEX IF NOT EXISTS aliases_phrase_idx ON aliases (phrase);
```

> No foreign key to `forms` or `components` — alias resolution is a lookup only; orphaned aliases fail gracefully at vector search fallback.

---

## Pydantic Models (Python)

### Form

```python
from pydantic import BaseModel, field_validator
from typing import Optional

class Field(BaseModel):
    id: str
    label: str
    type: str
    required: bool
    save_on_blur: bool = False
    component: Optional[str] = None         # component_id if this field uses a component
    save_behavior: Optional[str] = None     # overrides form-level if set
    save_trigger: Optional[str] = None

class Form(BaseModel):
    form_id: str
    display_name: Optional[str] = None
    module: Optional[str] = None
    save_behavior: str                      # SAVE_EXPLICIT | SAVE_ON_BLUR | SAVE_ON_SUBMIT | SAVE_AUTO
    save_trigger: str
    validation_timing: Optional[str] = None
    fields: list[Field]
    extends: Optional[str] = None          # parent form_id
    notes: Optional[str] = None

    @field_validator("form_id")
    @classmethod
    def form_id_snake_case(cls, v: str) -> str:
        if v != v.lower().replace("-", "_"):
            raise ValueError(f"form_id must be snake_case, got: {v!r}")
        return v
```

### Component

```python
class Component(BaseModel):
    id: str
    label: str
    description: str
    interaction_steps: list[str]
    save_behavior_notes: Optional[str] = None
    forms: list[str] = []                  # form_ids this component appears in
```

### Alias

```python
from typing import Literal

class Alias(BaseModel):
    phrase: str
    target_id: str
    target_type: Literal["form", "component"]
```

### TestCase

```python
class TestCase(BaseModel):
    title: str
    type: Literal["positive", "negative", "edge"]
    preconditions: list[str]
    steps: list[str]
    expected_result: str
    story_id: str                           # parent JIRA story ID

    def to_gherkin_scenario(self) -> str:
        lines = [f"  Scenario: {self.title}"]
        for pre in self.preconditions:
            lines.append(f"    Given {pre}")
        for i, step in enumerate(self.steps):
            keyword = "When" if i == 0 else "And"
            lines.append(f"    {keyword} {step}")
        lines.append(f"    Then {self.expected_result}")
        return "\n".join(lines)

    def to_zephyr_step(self) -> dict:
        return {
            "description": " → ".join(self.steps),
            "testData": "",
            "expectedResult": self.expected_result
        }
```

---

## YAML Schemas (user-supplied files)

### Form YAML (minimal required schema per FR-017)

```yaml
form_id: invoice_form              # string, required — must match CLI arg
display_name: Invoice Entry Form   # string, optional
module: Billing                    # string, optional
save_behavior: SAVE_EXPLICIT       # enum: SAVE_EXPLICIT | SAVE_ON_BLUR | SAVE_ON_SUBMIT | SAVE_AUTO
save_trigger: "click → [data-testid=\"save-icon\"]"  # string, required
validation_timing: VALIDATE_ON_SAVE  # optional
extends: base_form                 # optional — parent form_id for inheritance

fields:                            # required array
  - id: vendor_name                # string, required
    label: Vendor Name             # string, required
    type: text                     # string, required
    required: true                 # boolean, required
    save_on_blur: false            # boolean, defaults to false
    component: null                # optional component_id
```

### Component YAML (minimal required schema per FR-028)

```yaml
id: date_picker_v2                 # string, required — must match CLI arg
label: Date Picker v2              # string, required
description: >                     # string, required — plain English for semantic retrieval
  A date input that opens a calendar overlay when clicked.
  The user selects a date or types in DD/MM/YYYY format.
  Blur is triggered after the calendar closes.
interaction_steps:                 # array of strings, required
  - click the date field to open the calendar overlay
  - select a date by clicking it, or type a date in DD/MM/YYYY format
  - calendar closes automatically; field value is set
  - blur is triggered after calendar closes
save_behavior_notes: >             # string, optional
  Triggers blur event on close. Whether this causes a save depends on parent form save_behavior.
forms:                             # array of form_ids, optional
  - invoice_form
  - expense_form
```

---

## State Transitions

### Vocabulary Resolution (FR-014)

**v1** — alias lookup only (no semantic search):

```
phrase entered
    │
    ▼
aliases.yaml lookup
    │
    ├─ found → resolved ✓
    │
    └─ miss → tester types ID from known list ✓
```

> **v2 only:** Full 3-layer chain with semantic search:
> ```
> phrase entered
>     │
>     ▼
> Supabase aliases table lookup (O(1))
>     │
>     ├─ found → resolved ✓
>     │
>     └─ miss
>         │
>         ▼
>     semantic search (voyage-3-large → pgvector cosine)
>         │
>         ├─ score ≥ 0.85 → auto-resolve → log for alias promotion ✓
>         │
>         ├─ score 0.65–0.84 → show top-3 → tester picks → save alias ✓
>         │
>         └─ score < 0.65 → free-text fallback → tester types from known ID list ✓
> ```

### Action Prompt (FR-010, FR-012, FR-013, FR-022)

```
test cases generated
    │
    ├─ --export flag set → write file immediately → done (no prompt)
    │
    ├─ --dry-run → display only → done
    │
    ├─ non-TTY + no flags → error to stderr → exit 1
    │
    └─ interactive TTY
        │
        ▼
    display via $PAGER (less fallback)
        │
        ▼
    action prompt: push / export / edit / discard
        │
        ├─ push → check existing qa-gen subtasks → confirm → create subtasks
        │
        ├─ export → sub-prompt "md / json?" → write file
        │
        ├─ edit → open $EDITOR with temp file → re-parse Gherkin
        │             │
        │             ├─ valid → return to action prompt with updated cases
        │             └─ invalid → show error → re-open $EDITOR (loop)
        │
        └─ discard → exit silently
```
