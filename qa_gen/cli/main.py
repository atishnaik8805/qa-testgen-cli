import typer

from qa_gen.cli.commands.aliases import aliases_app
from qa_gen.cli.commands.components import components_app
from qa_gen.cli.commands.config import config_app
from qa_gen.cli.commands.forms import forms_app
from qa_gen.cli.commands.tests import tests_app
# V2: from qa_gen.cli.commands.db import db_app

app = typer.Typer(help="qa-gen: AI-powered QA test case generator")

app.add_typer(tests_app, name="tests")
app.add_typer(forms_app, name="forms")
app.add_typer(components_app, name="components")
app.add_typer(aliases_app, name="aliases")
app.add_typer(config_app, name="config")
# V2: app.add_typer(db_app, name="db")
