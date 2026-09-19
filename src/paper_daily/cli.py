from __future__ import annotations

import typer
from pathlib import Path

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


@app.command()
def library() -> None:
    """Open the local reading list without LLM setup or an API key."""
    from paper_daily.ui.app import PaperDailyApp
    PaperDailyApp(library_only=True).run()


@app.command()
def add(identifier: str) -> None:
    """Fetch authoritative arXiv metadata for an ID/URL and star it (no LLM)."""
    from paper_daily.core.reading_list import ReadingList
    from paper_daily.pipeline.arxiv import fetch_by_id
    import httpx
    import xml.etree.ElementTree as ET
    try:
        paper = fetch_by_id(identifier)
        ReadingList().add(paper)
    except (OSError, ValueError, httpx.HTTPError, ET.ParseError) as exc:
        typer.echo(f"Add failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Saved {paper['arxiv_id']}: {paper['title']}")


@app.command("import-list")
def import_list(path: Path) -> None:
    """Merge a schema-versioned JSON reading list; validate before writing."""
    from paper_daily.core.reading_list import ReadingList
    try:
        count = ReadingList().import_json(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        typer.echo(f"Import failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Imported {count} records (duplicates merged).")


@app.command("export-list")
def export_list(path: Path, bibtex: bool = False) -> None:
    """Export the local list as JSON, or --bibtex. Never overwrite a file."""
    from paper_daily.core.bibtex import export_bibtex
    from paper_daily.core.reading_list import ReadingList
    try:
        store = ReadingList()
        if bibtex:
            content = export_bibtex([item["paper"] for item in store.load()])
        else:
            content = store.export_json()
        with path.open("x", encoding="utf-8") as stream:
            stream.write(content)
    except (OSError, ValueError) as exc:
        typer.echo(f"Export failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Saved {path}")
