# qa-gen Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-26

## Active Technologies
- Python 3.11+ + `sentence-transformers>=2.7,<3` (new, optional), `numpy` (transitive via sentence-transformers), `pyyaml`, `pydantic`, `rich`, `typer` (002-local-semantic-search)
- Local JSON file `.qa-gen/search_index.json` per project root; atomic write (temp file → rename on success) (002-local-semantic-search)

- Python 3.11+ + Typer, Rich, httpx, supabase-py, voyageai, anthropic, google-genai, pydantic, pyyaml, gherkin-official (001-qa-testgen-cli)

## Project Structure

```text
qa_gen/
  kb/
    semantic_search.py   — SemanticSearchEngine: local cosine search over KB forms/components
  core/
    project_root.py      — find_project_root(): walk CWD up to locate project root
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes
- 002-local-semantic-search: Added Python 3.11+ + `sentence-transformers>=2.7,<3` (new, optional), `numpy` (transitive via sentence-transformers), `pyyaml`, `pydantic`, `rich`, `typer`

- 001-qa-testgen-cli: Added Python 3.11+ + Typer, Rich, httpx, supabase-py, voyageai, anthropic, google-genai, pydantic, pyyaml, gherkin-official

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
