# Running qa-gen with Local Semantic Search

## Prerequisites

Activate the project conda env:

```bash
conda activate qa-gen
```

Then `cd` into the project root (the folder containing `knowledge_base/`):

```bash
cd "C:\Users\91897\Desktop\AI\AI Projects\qa-gen"
```

Verify install:

```bash
qa-gen --help
```

---

## Step 1 — One-time config

qa-gen reads credentials from `~/.qa-gen/.env`. Run the config wizard once:

```bash
qa-gen config
```

This prompts for:

| Key | What it is |
|-----|-----------|
| `JIRA_BASE_URL` | e.g. `https://yourcompany.atlassian.net` |
| `JIRA_EMAIL` | your Atlassian account email |
| `JIRA_API_TOKEN` | from https://id.atlassian.com/manage-profile/security/api-tokens |
| `AI_PROVIDER` | `anthropic` or `gemini` |
| `AI_API_KEY` | API key for chosen provider |
| `AI_MODEL_NAME` | e.g. `claude-sonnet-4-6` or `gemini-2.0-flash` |

File is saved as `~/.qa-gen/.env` with permissions `0600`.

---

## Step 2 — (Optional) Install sentence-transformers

Without this, the CLI works exactly as before (exact match → alias → interactive prompt). No errors.

```bash
pip install "sentence-transformers>=2.7,<3"
```

~80 MB model downloads on first run and is cached by the library. No re-download after that.

---

## Step 3 — Add KB entries

Forms and components live under `knowledge_base/` in the project root.

**Form YAML** — `knowledge_base/forms/<form_id>.yaml`:

```yaml
name: Patient Registration Form
description: Collects new patient demographic and insurance details
fields:
  - id: first_name
    label: First Name
    type: text
  - id: dob
    label: Date of Birth
    type: date
    component: date_picker_v2
save_behavior: SAVE_ON_SUBMIT
```

**Component YAML** — `knowledge_base/components/<component_id>.yaml`:

```yaml
name: Date Picker v2
description: Calendar widget with keyboard navigation and range selection
```

The `name` + `description` fields are what the semantic engine embeds. Good descriptions = better matching.

List what's currently in the KB:

```bash
qa-gen forms list
qa-gen components list
```

---

## Step 4 — Generate test cases

```bash
qa-gen tests generate PROJ-1042
```

### Full example — first run with sentence-transformers installed

```
$ qa-gen tests generate PROJ-1042

⠋ Downloading embedding model, first run only…        ← one-time, ~5-30s
⠋ Fetching JIRA story...
⠋ Resolving form...
Resolved 'New Patient Intake' → 'patient_registration_form' (score: 0.87)
⠋ Resolving components...
Resolved 'date selector' → 'date_picker_v2' (score: 0.91)
⠋ Assembling context...
⠋ Generating test cases...

Feature: Patient Registration Form
  Scenario: Submit valid patient data
    Given I am on the Patient Registration Form
    When I fill in all required fields with valid data
    Then the form is submitted successfully
  ...

Action (push/export/edit/discard):
```

### Full example — subsequent runs (incremental, fast)

```
$ qa-gen tests generate PROJ-1043

⠋ Fetching JIRA story...
⠋ Resolving form...
Resolved 'Patient Sign Up' → 'patient_registration_form' (score: 0.83)
⠋ Resolving components...
⠋ Assembling context...
⠋ Generating test cases...
...
```

No model spinner — index is already built, only changed YAML files re-embedded.

### Dry run (preview only, no JIRA write)

```bash
qa-gen tests generate PROJ-1042 --dry-run
```

### Force a specific form (skip resolution entirely)

```bash
qa-gen tests generate PROJ-1042 --form patient_registration_form
```

### Skip confirmation prompt, auto-push to JIRA

```bash
qa-gen tests generate PROJ-1042 --no-confirm
```

### Write debug log to `~/.qa-gen/debug.log`

```bash
qa-gen tests generate PROJ-1042 --verbose
```

---

## Env vars

| Variable | Default | Effect |
|----------|---------|--------|
| `QA_GEN_SIMILARITY_THRESHOLD` | `0.75` | Min cosine score to accept a match. Raise to reduce false positives, lower to catch more. |
| `QA_GEN_DEBUG` | unset | Set to `1` to print top-3 candidates + scores to stderr before each resolution. |

### Raise threshold (stricter matching)

```bash
QA_GEN_SIMILARITY_THRESHOLD=0.85 qa-gen tests generate PROJ-1042
```

### Inspect why a label resolved (or didn't)

```bash
QA_GEN_DEBUG=1 qa-gen tests generate PROJ-1042
```

Output includes a debug line before each resolution:

```
  [debug] candidates: 'patient_registration_form' (0.87), 'patient_discharge_form' (0.61), 'lab_results_form' (0.44)
Resolved 'New Patient Intake' → 'patient_registration_form' (score: 0.87)
```

### Combine flags

```bash
QA_GEN_DEBUG=1 QA_GEN_SIMILARITY_THRESHOLD=0.80 qa-gen tests generate PROJ-1042 --dry-run
```

---

## CI / non-TTY

No interactive prompts in CI. If a label can't resolve, CLI exits non-zero:

```bash
# in a CI script
qa-gen tests generate PROJ-1042 --no-confirm
```

Failure output:

```
Unresolved label: 'New Patient Intake'
Hint: add an alias in knowledge_base/aliases.yaml → forms section
```

Fix options:
- Add alias: `qa-gen aliases add "new patient intake" --maps-to patient_registration_form`
- Improve KB YAML `name`/`description` so it matches semantically

---

## Managing aliases

```bash
# Add alias so "new patient intake" always maps to patient_registration_form
qa-gen aliases add "new patient intake" --maps-to patient_registration_form

# Overwrite existing alias
qa-gen aliases add "patient signup" --maps-to patient_registration_form --force

# List all aliases
qa-gen aliases list

# Remove alias
qa-gen aliases remove "new patient intake"
```

Alias lookup always runs before semantic search — an alias match skips the model entirely.

---

## Fallback conditions

| Condition | Behaviour |
|-----------|-----------|
| `sentence-transformers` not installed | v1 behavior: exact → alias → prompt |
| Model load fails (corrupted cache, wrong version) | Warning to stderr; falls through to prompt |
| Model download fails (no internet, first run) | Exit non-zero + `"Model download failed: … Re-run when connected."` |
| `.qa-gen/search_index.json` corrupt | Silently deleted; full rebuild this run |
| KB has zero YAML files | Nothing to index; all labels fall through to prompt |
| Project root not found (no `knowledge_base/` or `.qa-gen/` in CWD or parents) | Exit non-zero with descriptive error |

---

## File layout after first run

```
your-project/
  knowledge_base/
    forms/
      patient_registration_form.yaml
    components/
      date_picker_v2.yaml
    aliases.yaml
  .qa-gen/
    search_index.json        ← auto-generated, do not commit
  .gitignore                 ← .qa-gen/search_index.json appended automatically
```
