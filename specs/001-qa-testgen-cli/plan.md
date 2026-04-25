# Implementation Plan: QA Test Case Generation CLI Tool

**Branch**: `001-qa-testgen-cli` | **Date**: 2026-04-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-qa-testgen-cli/spec.md`

## Summary

Build `qa-gen` — a Python CLI tool that fetches a JIRA story via REST API, resolves the target form and UI components from a Supabase knowledge base, assembles a grounded context (static vocabulary + form doc + component docs), and calls an AI provider (Anthropic Claude or Google Gemini) to generate Gherkin-format test cases — with optional JIRA write-back, export, and an interactive confirmation loop.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Typer, Rich, httpx, supabase-py, voyageai, anthropic, google-genai, pydantic, pyyaml, gherkin-official
**Storage**: Supabase (PostgreSQL + pgvector)
**Testing**: pytest
**Target Platform**: Linux / macOS / Windows (local CLI, user machines)
**Project Type**: cli
**Performance Goals**: test case generation < 60s per story (SC-001); alias lookup < 1ms; semantic search < 500ms
**Constraints**: max 15 test cases per story; 60s AI call timeout; 3 retries with exponential backoff (1s/2s/4s); `~/.qa-gen/.env` mode 600; Supabase embedding dimension 1024 (voyage-3-large)
**Scale/Scope**: per-user local install via pipx; shared Supabase backend per team; knowledge base grows to hundreds of forms/components over time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

> **Note**: `.specify/memory/constitution.md` is an unfilled template. Gates below are derived from hard requirements in the spec.

| Gate | Rule | Status |
|------|------|--------|
| **G-1 Anti-Hallucination** | Generation MUST NOT start without fully resolved KB context (form doc + component docs injected). No fallthrough to AI on missing form. | PASS — orchestrator blocks on missing form (FR-019) |
| **G-2 Credential Security** | All secrets live exclusively in `~/.qa-gen/.env` (mode 600). No credential written inside project directory. Startup checks file permissions. | PASS — FR-020 explicitly specifies this |
| **G-3 Write Safety** | No JIRA subtask creation without explicit confirmation (action prompt or `--no-confirm` flag). `--dry-run` always wins. | PASS — FR-011, FR-012 define the gate |
| **G-4 External Call Resilience** | All calls to JIRA, AI provider, Supabase, Voyage AI wrapped in retry logic (3 attempts, exponential backoff, 429 Retry-After awareness). | PASS — FR-023 mandates this |
| **G-5 Non-TTY Safety** | Non-TTY environment without `--dry-run` or `--no-confirm` MUST error immediately. | PASS — FR-010 explicitly specifies this |

All gates pass. Proceeding.

## Project Structure

### Documentation (this feature)

```text
specs/001-qa-testgen-cli/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── cli.md           # CLI command schema
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
qa_gen/                           # Python package installed as `qa-gen` CLI
├── __init__.py
├── cli/
│   ├── __init__.py
│   ├── main.py                   # Typer app entry point; registers sub-apps
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── tests.py              # qa-gen tests <STORY_ID>
│   │   ├── forms.py              # qa-gen forms list/add/show/validate
│   │   ├── components.py         # qa-gen components add/list/show
│   │   ├── aliases.py            # qa-gen aliases add/list/remove
│   │   ├── config.py             # qa-gen config [show]
│   │   └── db.py                 # qa-gen db init
│   └── display.py                # Rich output helpers (panels, spinners, tables, pager)
├── core/
│   ├── __init__.py
│   ├── orchestrator.py           # Main pipeline: fetch → resolve → assemble → generate
│   ├── jira_client.py            # JIRA REST API v3 via httpx (direct; not MCP)
│   ├── jira_writer.py            # Create subtasks; check for existing qa-gen subtasks
│   ├── form_resolver.py          # FR-002: label → text extraction → tester prompt
│   ├── component_resolver.py     # FR-004: retrieve components by form reference
│   ├── alias_resolver.py         # FR-014/FR-015/FR-016: three-layer resolution chain
│   ├── context_assembler.py      # FR-003/FR-005: assemble system prompt context blocks
│   ├── adf_parser.py             # Convert Atlassian Document Format (ADF) JSON → plaintext
│   ├── gherkin_parser.py         # Parse/validate Gherkin; used in edit loop (FR-010)
│   └── ai/
│       ├── __init__.py
│       ├── base.py               # Abstract AI provider interface
│       ├── claude_client.py      # Anthropic provider with prompt caching (FR-029)
│       └── gemini_client.py      # Google Gemini provider via google-genai SDK
├── kb/
│   ├── __init__.py
│   ├── supabase_client.py        # Supabase client init; form/component/alias CRUD + RPC
│   ├── embedding.py              # Voyage AI voyage-3-large embedding wrapper
│   └── migrations.py             # DDL strings for qa-gen db init (pgvector + tables)
├── models/
│   ├── __init__.py
│   ├── form.py                   # Form, Field Pydantic models + YAML schema validation
│   ├── component.py              # Component Pydantic model + YAML schema validation
│   ├── alias.py                  # Alias Pydantic model
│   └── test_case.py              # TestCase Pydantic model; Gherkin + Zephyr JSON serialization
├── config/
│   ├── __init__.py
│   └── settings.py               # Load ~/.qa-gen/.env; enforce mode 600 on startup
└── knowledge_base/
    └── ui_vocabulary.md          # Layer 1 static vocabulary (always injected — never in vector DB)

tests/
├── unit/
│   ├── test_form_resolver.py
│   ├── test_alias_resolver.py
│   ├── test_context_assembler.py
│   ├── test_adf_parser.py
│   ├── test_gherkin_parser.py
│   └── test_models.py
├── integration/
│   ├── test_supabase.py
│   └── test_jira_client.py
└── contract/
    └── test_cli_commands.py

pyproject.toml
README.md
```

**Structure Decision**: Single-project CLI package (`qa_gen/`). No web frontend or mobile targets in v1. Core pipeline logic in `core/`, data access in `kb/`, Pydantic validation in `models/`, CLI surface in `cli/`. This separation allows unit testing of `core/` without any CLI or Supabase dependency.

## Complexity Tracking

> No constitution violations requiring justification.
