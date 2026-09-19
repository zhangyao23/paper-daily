import copy

import pyperclip
import pytest
from textual.widgets import Input, OptionList, Static

from paper_daily import config
from paper_daily.core import llm
from paper_daily.core.reading_list import ReadingList
from paper_daily.pipeline import arxiv, pdf_fetcher
from paper_daily.ui.app import PaperDailyApp
from paper_daily.ui.screens.library import LibraryScreen
from paper_daily.ui.screens.results import ResultsScreen


async def test_results_and_library_actual_ui(tmp_path, monkeypatch, paper):
    """Pilot operates real Textual widgets/key bindings, not action-method mocks."""
    monkeypatch.setattr(config, "exists", lambda: True)
    monkeypatch.setattr(config, "load", lambda: copy.deepcopy(config.DEFAULTS))
    app = PaperDailyApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("l")
        assert isinstance(app.screen, LibraryScreen)
        await pilot.press("escape")
        app.push_screen(ResultsScreen(config.DEFAULTS, [{**paper, "score": 0.8, "summary": "Fixture summary"}]))
        await pilot.pause()
        assert await pilot.click("#save-paper-0")
        assert len(ReadingList().load()) == 1
        await pilot.press("b")
        assert len(list((tmp_path / "exports").glob("results-*.bib"))) == 1
        await pilot.press("l", "r", "f", "e", "b")
        assert isinstance(app.screen, LibraryScreen)
        assert ReadingList().load()[0]["read"] is True
        assert ReadingList().load()[0]["starred"] is False
        backup = next((tmp_path / "exports").glob("reading-list-*.json"))
        await pilot.press("i")
        app.screen.query_one("#import-path", Input).value = str(backup)
        await pilot.press("enter")
        assert "Imported" in str(app.screen.query_one("#library-status", Static).render())
        assert len(ReadingList().load()) == 1
        await pilot.press("escape", "escape", "l")
        assert isinstance(app.screen, LibraryScreen)
        assert app.screen.query_one("#library-list", OptionList).option_count == 1


async def test_library_without_setup():
    app = PaperDailyApp(library_only=True)
    async with app.run_test() as pilot:
        assert isinstance(app.screen, LibraryScreen)
        await pilot.press("escape")


@pytest.mark.parametrize("clipboard_available", [True, False])
async def test_search_to_report_with_mock_services(tmp_path, monkeypatch, paper, clipboard_available):
    cfg = copy.deepcopy(config.DEFAULTS)
    cfg["llm"]["api_key"] = "offline-test-placeholder"
    monkeypatch.setattr(config, "exists", lambda: True)
    monkeypatch.setattr(config, "load", lambda: cfg)
    monkeypatch.setattr(arxiv, "search", lambda *a, **k: [paper])
    monkeypatch.setattr(pdf_fetcher, "download_pdf", lambda _: None)
    copied = []
    def copy_text(text):
        if not clipboard_available:
            raise pyperclip.PyperclipException("synthetic clipboard unavailable")
        copied.append(text)
    monkeypatch.setattr(pyperclip, "copy", copy_text)
    def chat(*args, **kwargs):
        system = args[3][0]["content"]
        if "scoring system" in system:
            return '[{"index": 0, "relevance": 0.8}]'
        if "summarizer" in system:
            return "Synthetic abstract summary"
        if "conference reviewer" in system:
            return '{"innovations": [], "experiments": {"ablation_present": null}}'
        return "## Synthetic formatted report"
    monkeypatch.setattr(llm, "chat", chat)
    app = PaperDailyApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("space", "enter")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert isinstance(app.screen, ResultsScreen)
        assert app.screen.papers[0]["summary"] == "Synthetic abstract summary"
        await pilot.press("c")
        if clipboard_available:
            assert "Abstract only" in copied[-1]
        else:
            assert "Clipboard unavailable" in str(app.screen.query_one("#report-status", Static).render())
        await pilot.press("d")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert isinstance(app.screen, ResultsScreen)
        exported = list((tmp_path / "exports").glob("digest-*.md"))
        assert len(exported) == 1
        assert "FALLBACK" in exported[0].read_text(encoding="utf-8")
        if clipboard_available:
            assert "Abstract only" in copied[-1]
        else:
            assert "clipboard unavailable" in str(app.screen.query_one("#report-status", Static).render())
