from __future__ import annotations

import typer

from paper_daily.ui.app import run


app = typer.Typer(
    name="paper-daily",
    help="Your daily arxiv digest, powered by LLM.",
    add_completion=False,
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        run()
