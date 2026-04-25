# qa-gen: AI-Powered QA Test Case Generator

`qa-gen` is a CLI tool designed to bridge the gap between JIRA user stories and accurate UI test cases. By using a localized Knowledge Base (KB) of your application's UI behavior, it generates Gherkin-formatted test cases that reflect your actual product, eliminating the "hallucinations" common in generic AI generation.

> **Core Mandate:** The model must never "guess" UI behavior; it only generates test steps from resolved, injected facts.

---

## 🚀 What is qa-gen?

The biggest challenge in AI-generated testing is context. A "save" action on one form might be an explicit button click, while on another, it's an auto-save on blur. `qa-gen` solves this by injecting specific UI facts—selectors, save behaviors, and component interactions—directly into the AI's reasoning loop.

---

## 🛠️ Key Features (v1)

- **Form-Aware Generation:** Automatically detects which form a JIRA story relates to via labels or text analysis.
- **Three-Layer Context Strategy:**
    - **Layer 1 (Vocabulary):** Standardizes definitions like `SAVE_ON_BLUR` vs `SAVE_EXPLICIT`.
    - **Layer 2 (Forms):** Detailed maps of fields, requirements, and selectors for specific pages.
    - **Layer 3 (Components):** Shared interaction steps for complex widgets like Date Pickers or Search Dropdowns.

  > **Why this split?** Vocabulary defines *terms* — what `SAVE_EXPLICIT` means, what a blur event is, what button states exist. These are true everywhere, so they live in one file injected once per call. Components define *behavior* — how a specific date picker or editable dropdown actually works, including its own save semantics. If you put "what is a blur event" inside every component YAML, the AI sees the same definition repeated for every component loaded in a call. And when the definition changes, you update N files instead of one. Rule of thumb: if a definition belongs to a widget type → component YAML. If it belongs to the shared UI language → vocabulary.
- **JIRA Integration:** Direct integration with JIRA REST API v3 to fetch stories and push subtasks.
- **Zero Infra (v1):** Operates entirely with local YAML files and simple API keys—no database or vector infrastructure required for the POC.

---

## 📋 Tech Stack

- **CLI Framework:** [Typer](https://typer.tiangolo.com/) (FastAPI's sibling for CLIs)
- **Terminal UI:** [Rich](https://rich.readthedocs.io/) (Spinners, tables, and colored panels)
- **AI Models:** Anthropic Claude 3.5 Sonnet or Google Gemini 1.5/2.0
- **HTTP Client:** [httpx](https://www.python-httpx.org/)
- **Data Validation:** [Pydantic v2](https://docs.pydantic.dev/)

---

## 📥 Installation

### Prerequisites
- Python 3.11 or 3.12 (3.14+ is not recommended due to binary wheel compatibility)
- A JIRA Cloud account and API Token
- An API Key for Anthropic or Google Gemini

### For End Users (Recommended)
```bash
pipx install git+https://github.com/YOUR_ORG/qa-gen.git
```

### For Local Development (using Mamba/Conda)
```bash
# Clone the repository
git clone <repo-url>
cd qa-gen

# Create environment from environment.yml
mamba env create -f environment.yml
mamba activate qa-gen
```

---

## ⚙️ Setup & Configuration

### 1. Run the Config Wizard
```bash
qa-gen config
```
This creates `~/.qa-gen/.env` with permissions locked to **mode 600** (readable only by your user). It will prompt for:
- JIRA URL & Credentials
- AI Provider & API Key
- Knowledge Base Path (Defaults to `./knowledge_base`)

### 2. Prepare the Knowledge Base
The tool expects a specific directory structure:
```text
knowledge_base/
├── ui_vocabulary.md    # Global definitions (injected into every prompt)
├── aliases.yaml        # Maps "the calendar thing" -> date_picker_v2
├── forms/              # YAMLs for each form/screen
└── components/         # YAMLs for shared UI widgets
```

---

## 📖 JIRA Story Conventions

To enable auto-detection, your JIRA stories should follow these conventions:

1.  **Labels:** Include the `form_id` as a label (e.g., `invoice_form`).
2.  **Acceptance Criteria:** Use clear bullet points or "Given/When/Then" steps.
3.  **Components:** Use JIRA components to denote the application module.

If no label matches, `qa-gen` will attempt to guess the form via semantic analysis or prompt you to select one from the KB.

---

## ⌨️ Usage

### Generate Test Cases
```bash
# Interactive mode
qa-gen tests PROJ-1042

# Dry run (safe for testing)
qa-gen tests PROJ-1042 --dry-run

# Override form detection
qa-gen tests PROJ-1042 --form expense_form

# Export to files only
qa-gen tests PROJ-1042 --export md --export json --no-confirm
```

### Manage the KB
```bash
# List all forms
qa-gen forms list

# Validate a new YAML file before committing
qa-gen forms validate invoice_form --file ./my_new_form.yaml

# Map a new phrase to an ID
qa-gen aliases add "search box" --maps-to typeahead_select_v3
```

---

## 🛡️ Security & Privacy

- **Local First:** Your Knowledge Base stays in your local filesystem or git repo.
- **Secret Protection:** `qa-gen config show` redacts all API keys and tokens.
- **No Persistence:** `qa-gen` does not store your JIRA story data or generated test cases in any central database.
- **Safe Parsing:** Uses `yaml.safe_load()` to prevent remote code execution from malicious YAML files.

---

## 🆘 Troubleshooting

- **"run qa-gen config first"**: Your configuration file is missing. Run `qa-gen config`.
- **"ID mismatch"**: The `form_id` inside the YAML file must match the filename and the ID used in the CLI.
- **Permissions Warning**: If `~/.qa-gen/.env` is not mode 600, run `chmod 600 ~/.qa-gen/.env`.
- **AI Failure**: Use the `--verbose` flag and check `~/.qa-gen/debug.log` to see the raw API responses.

---

## 🔮 Roadmap to v2

- **Supabase Integration:** Team-shared Knowledge Base and aliases.
- **Semantic Search:** Voyage AI embeddings for fuzzy form/component matching.
- **Admin RBAC:** Permission tiers to gate KB modifications.

---

*Version: 1.0 (POC) | April 2026*
