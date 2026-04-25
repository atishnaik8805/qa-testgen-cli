# Phase 0 Research: QA Test Case Generation CLI

**Branch**: `001-qa-testgen-cli` | **Date**: 2026-04-24

## 1. JIRA REST API v3 — ADF Parsing

**Decision**: Write a recursive ADF-to-plaintext traversal in `core/adf_parser.py`. No third-party ADF library.

**Rationale**: The `atlassian-python-api` library adds a large transitive dependency chain for one parsing task. ADF structure is simple enough to traverse directly. The description and acceptance criteria fields return `{"version": 1, "type": "doc", "content": [...]}`. Text is extracted from leaf nodes of type `"text"` by walking the `"content"` arrays recursively. Block nodes (`paragraph`, `bulletList`, `listItem`, `heading`, `blockquote`, `codeBlock`, `orderedList`) are separated by newlines. Inline marks (`strong`, `em`, `code`) are ignored — plain text is sufficient for generation context.

**Alternatives considered**: `atlassian-python-api` (too heavy, ADF support incomplete for custom fields); `markdown-it-py` (wrong direction — ADF is JSON not Markdown).

**Auth**: `httpx.BasicAuth(jira_email, jira_api_token)` — Atlassian Cloud standard. Base URL: `https://<domain>.atlassian.net`. Endpoint: `GET /rest/api/3/issue/{issueIdOrKey}?fields=summary,description,customfield_acceptance_criteria,labels,components,subtasks,issuetype`.

**Custom field for AC**: Acceptance criteria is stored in `customfield_10016` (Atlassian default) but varies per JIRA project. Config wizard must collect the AC custom field ID if different from default, or the tool reads from `description` as fallback.

---

## 2. Voyage AI Python SDK — Embedding

**Decision**: Use `voyageai>=0.3` Python SDK. Model: `voyage-3-large` (fixed; not configurable). Output dimension: 1024.

**API pattern**:
```python
import voyageai
vo = voyageai.Client(api_key=VOYAGE_API_KEY)
# For ingestion (forms/components YAML content):
result = vo.embed(texts, model="voyage-3-large", input_type="document")
# For query (resolving a QA phrase):
result = vo.embed([phrase], model="voyage-3-large", input_type="query")
embeddings = result.embeddings  # list[list[float]], each of length 1024
```

**Rationale**: `voyage-3-large` is the highest-accuracy Voyage model for mixed technical/plain-language content — matches confidence thresholds calibrated in FR-014.

**Alternatives considered**: `voyage-3` (lower accuracy, spec explicitly upgrades to `voyage-3-large`); `text-embedding-3-large` from OpenAI (different vendor, no migration path specified).

---

## 3. Supabase Python SDK — pgvector RPC

**Decision**: Use `supabase>=2.0` Python SDK. DDL executed via `postgrest-py` raw SQL through Supabase management API using the `service_role` key.

**API patterns**:
```python
from supabase import create_client
client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Deterministic fetch by form_id:
result = client.table("forms").select("*").eq("form_id", form_id).execute()

# Semantic similarity search (pgvector RPC):
result = client.rpc("match_forms", {
    "query_embedding": query_vector,   # list[float] length 1024
    "match_threshold": 0.65,
    "match_count": 3
}).execute()

# Upsert (for forms add / components add):
client.table("forms").upsert({"form_id": ..., "content": ..., "embedding": ...}).execute()
```

**DDL via db init**: pgvector extension and table creation use Supabase's `client.postgrest` raw SQL path or the management REST API. The `service_role` key has the DDL privilege — anon key does not.

**Alternatives considered**: Pinecone (no SQL filtering alongside vector search; higher ops overhead); Weaviate (separate infra); local SQLite with sqlite-vss (not shared across team).

---

## 4. Anthropic SDK — Prompt Caching

**Decision**: Use `anthropic>=0.40` Python SDK. Enable `cache_control: {"type": "ephemeral"}` on the system prompt block and the shared KB context block.

**API pattern**:
```python
import anthropic
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

response = client.messages.create(
    model=config.AI_MODEL_NAME,
    max_tokens=4096,
    system=[
        {
            "type": "text",
            "text": ROLE_AND_RULES,
            "cache_control": {"type": "ephemeral"}   # cached — stable across calls
        },
        {
            "type": "text",
            "text": ui_vocabulary + form_doc + component_docs,
            "cache_control": {"type": "ephemeral"}   # cached — changes only when KB changes
        }
    ],
    messages=[
        {
            "role": "user",
            "content": story_specific_prompt   # NOT cached — unique per story
        }
    ]
)
```

**Rationale**: System prompt + vocabulary/form/component context is identical across calls for the same form. Caching slashes token cost and latency on repeat calls. Story title/description/AC changes every call — not cached (FR-029).

**Alternatives considered**: No caching (higher cost per call); caching everything including story content (defeats purpose — story changes each call).

---

## 5. Google Gemini SDK

**Decision**: Use `google-genai>=1.0` Python SDK (current; replaces deprecated `google-generativeai`).

**API pattern**:
```python
from google import genai
from google.genai import types

client = genai.Client(api_key=GEMINI_API_KEY)
response = client.models.generate_content(
    model=config.AI_MODEL_NAME,   # e.g. "gemini-2.5-flash"
    contents=[story_specific_prompt],
    config=types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=4096,
    )
)
text = response.text
```

**Rationale**: `google-genai` is the current Google GenAI Python SDK. The deprecated `google-generativeai` should not be used in new code.

**Alternatives considered**: `google-generativeai` (deprecated, spec explicitly names `google-genai`).

---

## 6. Gherkin Parsing — Edit Loop Validation

**Decision**: Use `gherkin-official>=29.0` PyPI package for Gherkin parse/validate in the editor loop.

**API pattern**:
```python
from gherkin.parser import Parser
from gherkin.token_scanner import TokenScanner
from gherkin.errors import ParserError

def validate_gherkin(text: str) -> list[str]:
    try:
        parser = Parser()
        parser.parse(TokenScanner(text))
        return []  # no errors
    except ParserError as e:
        return [str(e)]
```

**Rationale**: `gherkin-official` is the reference Gherkin parser extracted from Cucumber. It validates the full Gherkin grammar including `Feature`, `Scenario`, `Given/When/Then/And/But` structure.

**Alternatives considered**: Regex-based validation (fragile, misses structural errors); `pytest-bdd` (pulls in test framework dependency for a single use case).

---

## 7. $PAGER Display

**Decision**: Use `subprocess.run` with TTY detection. Write content to a temp file and pass as argument to `less` (not via stdin) to preserve proper TTY handling.

**Pattern**:
```python
import os, subprocess, tempfile, sys

def display_with_pager(content: str) -> None:
    if not sys.stdout.isatty():
        sys.stdout.write(content)
        return
    pager = os.environ.get("PAGER", "less")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        tmp_path = f.name
    try:
        subprocess.run([pager, tmp_path], check=False)
    finally:
        os.unlink(tmp_path)
```

**Rationale**: Passing file path rather than piping via stdin ensures `less` can handle large outputs correctly and supports interactive navigation. Fallback to `less` when `$PAGER` unset.

---

## 8. Zephyr Scale Cloud JSON Import Format

**Decision**: Use the Zephyr Scale Cloud REST API import format. Structure:

```json
{
  "version": 1,
  "testCases": [
    {
      "name": "TC-01 · Save with all mandatory fields filled",
      "status": "Draft",
      "precondition": "Invoice form is open and user is logged in",
      "objective": "Verify save succeeds when all required fields are filled",
      "testScript": {
        "type": "STEP_BY_STEP",
        "steps": [
          {
            "description": "Fill vendor_name with 'Acme Corp', amount with '1000', select date",
            "testData": "",
            "expectedResult": "Fields accept input"
          },
          {
            "description": "Click [data-testid=\"save-icon\"]",
            "testData": "",
            "expectedResult": "Record persisted, success toast appears"
          }
        ]
      },
      "labels": ["auto-generated", "qa-gen"],
      "customFields": {}
    }
  ]
}
```

**Rationale**: Zephyr Scale Cloud accepts this format for bulk test case import via its REST API. The `testScript.type: "STEP_BY_STEP"` maps Gherkin Given/When/Then into discrete steps.

**Alternatives considered**: Gherkin `.feature` file export (Zephyr Scale can import these too, but the JSON format is more structured and controllable).

---

## 9. YAML → Supabase Ingestion ID Mismatch Validation

**Decision**: CLI `<form_id>` arg and `form_id` field inside YAML must match exactly. Check before embedding or writing to Supabase. Abort with message identifying both values.

**Pattern**: `forms add invoice_form --file ./invoice_form.yaml` → parse YAML → check `yaml_data["form_id"] == cli_arg`. Same for `components add <component_id>`.

---

## 10. Config File Location and Permissions

**Decision**: `~/.qa-gen/.env` — home directory, not inside project. Create with `os.chmod(path, 0o600)` immediately after write. On every startup, check `oct(os.stat(path).st_mode)[-3:]` and warn to stderr if not `600`.

**Rationale**: FR-020 mandates mode 600, startup permission check, and warning if relaxed. No secrets inside project directory (avoids accidental git commit).

---

## All NEEDS CLARIFICATION Items — Resolved

| Item | Resolution |
|------|------------|
| ADF parsing approach | Custom recursive traversal in `adf_parser.py` |
| Voyage AI SDK call pattern | `voyageai.Client().embed(texts, model="voyage-3-large", input_type=...)` |
| Supabase pgvector RPC pattern | `client.rpc("match_forms", {...}).execute()` |
| Anthropic prompt caching syntax | `cache_control: {"type": "ephemeral"}` in system content blocks |
| Gemini SDK | `google-genai` — `genai.Client().models.generate_content()` |
| Gherkin validation | `gherkin-official` PyPI package |
| $PAGER invocation | `subprocess.run([pager, tmp_path])` with TTY detection |
| Zephyr Scale JSON format | `{"version": 1, "testCases": [...]}` with `testScript.type: STEP_BY_STEP` |
| YAML ID mismatch handling | CLI arg vs YAML field strict equality check before any write |
| Config file permissions | `os.chmod(path, 0o600)` on create; startup permission check |
