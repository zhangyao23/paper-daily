from typer.testing import CliRunner
import httpx

from paper_daily.cli import app
from paper_daily.core.reading_list import ReadingList
from paper_daily.pipeline import arxiv


def test_cli_add_and_roundtrip(tmp_path, monkeypatch, paper):
    runner = CliRunner()
    monkeypatch.setattr(arxiv, "fetch_by_id", lambda _: paper)
    assert runner.invoke(app, ["add", paper["arxiv_id"]]).exit_code == 0
    destination = tmp_path / "backup.json"
    assert runner.invoke(app, ["export-list", str(destination)]).exit_code == 0
    assert runner.invoke(app, ["export-list", str(destination)]).exit_code == 1
    assert runner.invoke(app, ["import-list", str(destination)]).exit_code == 0
    assert len(ReadingList().load()) == 1
    bib = tmp_path / "papers.bib"
    assert runner.invoke(app, ["export-list", str(bib), "--bibtex"]).exit_code == 0
    assert "@misc" in bib.read_text()


def test_add_failure_does_not_save(monkeypatch):
    def unavailable(_):
        raise httpx.ConnectError("offline")
    monkeypatch.setattr(arxiv, "fetch_by_id", unavailable)
    result = CliRunner().invoke(app, ["add", "2401.00001"])
    assert result.exit_code == 1 and "Add failed" in result.output
    assert ReadingList().load() == []
