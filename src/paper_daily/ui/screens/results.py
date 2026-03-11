from __future__ import annotations

from datetime import date

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Static

from paper_daily.ui.widgets import Banner, score_style


class ResultsScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Back", priority=True),
        Binding("enter", "back", "Back"),
        Binding("c", "copy_results", "Copy", priority=True),
        Binding("d", "generate_report", "Report", priority=True),
        Binding("q", "quit_app", "Quit", priority=True),
    ]

    def __init__(self, cfg: dict, papers: list[dict]) -> None:
        super().__init__()
        self.cfg = cfg
        self.papers = papers

    def compose(self) -> ComposeResult:
        kw_info = f"{len(self.papers)} papers -- {date.today().isoformat()}"
        yield Banner(right_text=kw_info)
        with VerticalScroll():
            for i, paper in enumerate(self.papers):
                yield Static(
                    self._render_paper(i, paper), classes="result-card"
                )
            yield Static("", id="report-status")
        yield Footer()

    def _render_paper(self, index: int, paper: dict) -> Text:
        score = paper.get("score", 0.0)
        style = score_style(score)
        show_abstract = self.cfg.get("feed", {}).get("show_abstract", False)

        text = Text()
        text.append(f"#{index + 1}  ", style="bold")
        text.append(f"[{score:.2f}] ", style=style)
        text.append(paper.get("title", ""), style="bold")
        text.append("\n")

        authors = paper.get("authors", [])
        if authors:
            if len(authors) > 3:
                author_str = f"{authors[0]} et al."
            else:
                author_str = ", ".join(authors)
            text.append(f"  Authors: {author_str}\n", style="dim")

        summary = paper.get("summary", "")
        if summary:
            for line in self._wrap(summary, 70):
                text.append(f"  {line}\n")

        if show_abstract:
            abstract = paper.get("abstract", "")
            if abstract:
                text.append("  Abstract:\n", style="dim")
                for line in self._wrap(abstract, 70):
                    text.append(f"  {line}\n", style="dim")

        url = paper.get("url", "")
        if url:
            text.append(f"  {url}", style="bright_blue")

        return text

    @staticmethod
    def _wrap(text: str, width: int) -> list[str]:
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            if current and len(current) + 1 + len(word) > width:
                lines.append(current)
                current = word
            else:
                current = f"{current} {word}" if current else word
        if current:
            lines.append(current)
        return lines

    def action_back(self) -> None:
        self.dismiss(None)

    def action_copy_results(self) -> None:
        import pyperclip

        lines = [f"Paper Daily -- {date.today().isoformat()}\n"]
        for i, paper in enumerate(self.papers):
            lines.append(f"#{i + 1} [{paper.get('score', 0):.2f}] {paper.get('title', '')}")
            authors = paper.get("authors", [])
            if authors:
                author_str = f"{authors[0]} et al." if len(authors) > 3 else ", ".join(authors)
                lines.append(f"  Authors: {author_str}")
            summary = paper.get("summary", "")
            if summary:
                lines.append(f"  {summary}")
            url = paper.get("url", "")
            if url:
                lines.append(f"  {url}")
            lines.append("")
        pyperclip.copy("\n".join(lines))
        status = self.query_one("#report-status", Static)
        status.update("\n  Results copied to clipboard. Paste with Ctrl+V.")

    def action_generate_report(self) -> None:
        from paper_daily.ui.screens.report_running import ReportRunningScreen

        def on_done(result: str | None) -> None:
            if result:
                status = self.query_one("#report-status", Static)
                status.update("\n  Report copied to clipboard. Paste with Ctrl+V.")

        self.app.push_screen(
            ReportRunningScreen(self.cfg, self.papers),
            callback=on_done,
        )

    def action_quit_app(self) -> None:
        self.app.exit()
