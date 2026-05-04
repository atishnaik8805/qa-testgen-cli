from pathlib import Path

from qa_gen.cli.display import err_console


def find_project_root(start: Path | None = None) -> Path:
    """Walk up from start (default: cwd) until knowledge_base/ or .qa-gen/ found."""
    current = start or Path.cwd()
    for directory in [current, *current.parents]:
        if (directory / "knowledge_base").exists() or (directory / ".qa-gen").exists():
            return directory
    err_console.print(
        f"Error: project root not found. Searched from '{current}' upward.\n"
        "Expected a directory containing 'knowledge_base/' or '.qa-gen/'."
    )
    raise SystemExit(1)
