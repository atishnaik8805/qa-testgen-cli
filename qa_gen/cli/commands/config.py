import os
import sys
from pathlib import Path

import typer

config_app = typer.Typer(help="Configure qa-gen")

_CONFIG_DIR = Path.home() / ".qa-gen"
_CONFIG_PATH = _CONFIG_DIR / ".env"

_REDACT_PATTERNS = ("_KEY", "_TOKEN", "_SECRET", "SUPABASE_DB_URL")

_FIELDS = [
    ("JIRA_BASE_URL", "JIRA URL (https://<domain>.atlassian.net)", None),
    ("JIRA_EMAIL", "JIRA email", None),
    (
        "JIRA_API_TOKEN",
        "JIRA API token (create at https://id.atlassian.com/manage-profile/security/api-tokens)",
        None,
    ),
    ("AI_PROVIDER", "AI provider (anthropic/gemini)", "anthropic"),
    ("AI_API_KEY", "AI provider API key", None),
    ("AI_MODEL_NAME", "AI model name (e.g. claude-sonnet-4-20250514)", None),
    ("KB_PATH", "Knowledge base path (directory containing forms/ and components/)", "./knowledge_base"),
    # V2:
    # ("SUPABASE_URL", "Supabase URL", None),
    # (
    #     "SUPABASE_SERVICE_KEY",
    #     "Supabase service_role key — required for db init DDL and all runtime operations",
    #     None,
    # ),
    # (
    #     "SUPABASE_DB_URL",
    #     (
    #         "Supabase DB URL (direct PostgreSQL connection string — required for 'db init'; "
    #         "find it in Supabase dashboard → Settings → Database → Connection string (URI mode)) "
    #         "[optional, press Enter to skip]"
    #     ),
    #     None,
    # ),
    # ("VOYAGE_API_KEY", "Voyage AI API key", None),
]


def _load_existing() -> dict[str, str]:
    if not _CONFIG_PATH.exists():
        return {}
    env: dict[str, str] = {}
    with open(_CONFIG_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


@config_app.command()
def setup() -> None:
    existing = _load_existing()
    collected: dict[str, str] = {}

    typer.echo("qa-gen configuration wizard")
    typer.echo("Press Enter to accept existing values shown in brackets.\n")

    for key, prompt_text, default in _FIELDS:
        current = existing.get(key, default or "")
        display_default = f" [{current}]" if current else ""
        val = typer.prompt(f"{prompt_text}{display_default}", default=current, show_default=False)
        collected[key] = val.strip()

    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = [f"{k}={v}" for k, v in collected.items()]
    _CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(_CONFIG_PATH, 0o600)
    typer.echo(f"\nConfiguration saved to {_CONFIG_PATH} (mode 600).")


@config_app.command("show")
def show() -> None:
    if not _CONFIG_PATH.exists():
        typer.echo("No config found. Run 'qa-gen config' first.", err=True)
        raise typer.Exit(1)

    env = _load_existing()
    for key, val in env.items():
        if any(pattern in key for pattern in _REDACT_PATTERNS):
            val = "***"
        typer.echo(f"{key}={val}")
