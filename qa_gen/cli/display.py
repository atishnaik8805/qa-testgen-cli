import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table

console = Console()
err_console = Console(stderr=True)


def show_with_pager(content: str) -> None:
    if not sys.stdout.isatty():
        sys.stdout.write(content)
        return
    pager = os.environ.get("PAGER", "less")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(content)
        tmp_path = f.name
    try:
        subprocess.run([pager, tmp_path], check=False)
    finally:
        os.unlink(tmp_path)


def action_prompt() -> str:
    choices = ["push", "export", "edit", "discard"]
    while True:
        val = console.input("[bold]Action[/bold] (push/export/edit/discard): ").strip().lower()
        if val in choices:
            return val
        console.print(f"[red]Invalid choice. Choose: {', '.join(choices)}[/red]")


def export_format_prompt() -> str:
    while True:
        val = console.input("[bold]Format[/bold] (md/json): ").strip().lower()
        if val in ("md", "json"):
            return val
        console.print("[red]Invalid format. Choose: md or json[/red]")


def confirm(message: str) -> bool:
    val = console.input(f"{message} (y/n): ").strip().lower()
    return val in ("y", "yes")


def show_table(headers: list[str], rows: list[list]) -> None:
    table = Table(*headers)
    for row in rows:
        table.add_row(*[str(c) for c in row])
    console.print(table)


def show_panel(title: str, content: str) -> None:
    console.print(Panel(content, title=title))


@contextmanager
def spinner(label: str):
    with Live(Spinner("dots", text=label), refresh_per_second=10, console=console):
        yield
