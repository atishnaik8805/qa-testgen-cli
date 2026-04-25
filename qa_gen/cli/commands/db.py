# V2 ONLY — not used in v1 (flat-file KB, no database setup needed)
# Restore in v2: re-register db_app in cli/main.py

import typer

from qa_gen.config.settings import load_settings

db_app = typer.Typer(help="Manage Supabase database")


@db_app.command("init")
def init() -> None:
    settings = load_settings()

    if not settings.SUPABASE_DB_URL:
        typer.echo(
            "SUPABASE_DB_URL not set — run 'qa-gen config' and supply the direct PostgreSQL connection string",
            err=True,
        )
        raise typer.Exit(1)

    from qa_gen.kb.migrations import run_migrations
    typer.echo("Initializing Supabase database...")
    run_migrations(settings.SUPABASE_DB_URL)
    typer.echo("Database initialization complete.")
