"""Reading-list screen, usable without an API key or network."""
from __future__ import annotations

from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Input, OptionList, Static
from textual.widgets.option_list import Option

from paper_daily.core.bibtex import export_bibtex
from paper_daily.core.exports import save_export
from paper_daily.core.reading_list import ReadingList
from paper_daily.ui.widgets import Banner


class LibraryScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Back", priority=True),
        Binding("f", "toggle_star", "Star"),
        Binding("r", "toggle_read", "Read/unread"),
        Binding("e", "export_json", "Export JSON"),
        Binding("b", "export_bibtex", "BibTeX"),
        Binding("i", "import_json", "Import JSON"),
    ]
    DEFAULT_CSS = """
    LibraryScreen #library-list { height: 1fr; }
    LibraryScreen #library-status { height: auto; padding: 1; }
    LibraryScreen #import-path { margin: 1; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.store = ReadingList()
        self.items: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Banner(right_text="Local reading list")
        yield Static("  Select a paper with arrows. Stars and read status apply to the work across versions.")
        yield OptionList(id="library-list")
        yield Input(placeholder="Path to a reading-list JSON export; Enter to import", id="import-path")
        yield Static("", id="library-status", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#import-path", Input).display = False
        self._refresh()
        self.query_one("#library-list", OptionList).focus()

    def _status(self, message: str) -> None:
        self.query_one("#library-status", Static).update(message)

    def _refresh(self) -> None:
        try:
            self.items = self.store.load()
        except (OSError, ValueError) as exc:
            self._status(f"Cannot load reading list: {exc}")
            return
        options = self.query_one("#library-list", OptionList)
        previous = options.highlighted
        options.clear_options()
        for item in self.items:
            paper = item["paper"]
            star = "*" if item["starred"] else "-"
            state = "read" if item["read"] else "unread"
            options.add_option(Option(Text(f"[{star}] [{state}] {paper['arxiv_id']}  {paper.get('title', '(title unavailable)')}")))
        if self.items:
            options.highlighted = min(previous or 0, len(self.items) - 1)
        self._status(f"{len(self.items)} papers. Storage: {self.store.path}")

    def _toggle(self, field: str) -> None:
        index = self.query_one("#library-list", OptionList).highlighted
        if index is None or not self.items:
            return
        try:
            self.store.toggle(self.items[index]["paper"]["arxiv_id"], field)
            self._refresh()
        except (OSError, ValueError) as exc:
            self._status(f"Update failed: {exc}")

    def action_toggle_star(self) -> None:
        self._toggle("starred")

    def action_toggle_read(self) -> None:
        self._toggle("read")

    def _export(self, bibtex: bool) -> None:
        try:
            if bibtex:
                content = export_bibtex([item["paper"] for item in self.store.load()])
            else:
                content = self.store.export_json()
            path = save_export(content, "reading-list", "bib" if bibtex else "json")
            self._status(f"Saved: {path}")
        except (OSError, ValueError) as exc:
            self._status(f"Export failed: {exc}")

    def action_export_json(self) -> None:
        self._export(False)

    def action_export_bibtex(self) -> None:
        self._export(True)

    def action_import_json(self) -> None:
        entry = self.query_one("#import-path", Input)
        entry.display = True
        entry.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "import-path":
            return
        try:
            path = Path(event.value.strip().strip('"')).expanduser()
            count = self.store.import_json(path.read_text(encoding="utf-8-sig"))
            event.input.display = False
            self._refresh()
            self._status(f"Imported {count} records; duplicates merged. {len(self.items)} papers total.")
            self.query_one("#library-list", OptionList).focus()
        except (OSError, ValueError) as exc:
            self._status(f"Import failed (existing list preserved): {exc}")

    def action_back(self) -> None:
        entry = self.query_one("#import-path", Input)
        if entry.display:
            entry.display = False
            self.query_one("#library-list", OptionList).focus()
        else:
            self.app.pop_screen()
