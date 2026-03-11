from __future__ import annotations

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Footer, Static

from paper_daily.ui.widgets import Banner


class ReportRunningScreen(Screen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, cfg: dict, papers: list[dict]) -> None:
        super().__init__()
        self.cfg = cfg
        self.papers = papers

    def compose(self) -> ComposeResult:
        yield Banner()
        with Container(id="report-container"):
            yield Static(
                "  Generating report for current results",
                classes="section-label",
            )
            yield Static("", id="step-1")
            yield Static("", id="step-2")
            yield Static("", id="step-3")
            yield Static("", id="progress-bar")
            yield Static("", id="error-msg")
        yield Footer()

    def on_mount(self) -> None:
        self._run_report()

    def _set_step(self, step: int, state: str, detail: str) -> None:
        labels = {
            1: "Downloading PDFs",
            2: "Deep reviewing",
            3: "Formatting to Markdown",
        }
        label = labels.get(step, "")
        text = Text()
        if state == "done":
            text.append(f"  [{step}/3] {label}  ", style="green")
            text.append(detail, style="dim")
        elif state == "active":
            text.append(f"  [{step}/3] {label}  ", style="cyan")
            text.append(detail, style="cyan")
        else:
            text.append(f"  [{step}/3] {label}", style="dim")

        try:
            self.query_one(f"#step-{step}", Static).update(text)
        except Exception:
            pass

    def _set_progress(self, current: int, total: int) -> None:
        if total == 0:
            return
        width = 30
        filled = int(width * current / total)
        pct = int(100 * current / total)
        text = Text()
        text.append("  ")
        text.append("\u2501" * filled, style="green")
        text.append("\u2501" * (width - filled), style="dim")
        text.append(f"  {pct}%", style="cyan")
        self.query_one("#progress-bar", Static).update(text)

    @work(thread=True)
    def _run_report(self) -> None:
        from paper_daily.config import resolve_api_key
        from paper_daily.pipeline import (
            deep_reviewer,
            formatter as formatter_mod,
            pdf_fetcher,
        )

        api_key = resolve_api_key(self.cfg)
        if not api_key:
            self.app.call_from_thread(
                self._show_error,
                "No API key found. Configure one via Settings or env var.",
            )
            return

        llm_cfg = self.cfg.get("llm", {})
        feed = self.cfg.get("feed", {})
        api_base = llm_cfg.get("api_base", "")
        model = llm_cfg.get("model", "")
        deep_top_n = feed.get("deep_top_n", 3)
        to_deep = self.papers[:deep_top_n]

        self.app.call_from_thread(self._set_step, 1, "pending", "")
        self.app.call_from_thread(self._set_step, 2, "pending", "")
        self.app.call_from_thread(self._set_step, 3, "pending", "")

        try:
            self.app.call_from_thread(
                self._set_step, 1, "active", f"0/{len(to_deep)}"
            )
            full_texts = []
            for i, paper in enumerate(to_deep):
                self.app.call_from_thread(
                    self._set_step, 1, "active", f"{i + 1}/{len(to_deep)}"
                )
                pdf_path = pdf_fetcher.download_pdf(paper["arxiv_id"])
                if pdf_path:
                    full_texts.append(pdf_fetcher.extract_text(pdf_path))
                else:
                    full_texts.append(paper.get("abstract", ""))
            self.app.call_from_thread(
                self._set_step, 1, "done", f"{len(full_texts)} papers"
            )

            def on_review_progress(done: int, rev_total: int) -> None:
                self.app.call_from_thread(
                    self._set_step, 2, "active", f"{done}/{rev_total}"
                )
                self.app.call_from_thread(
                    self._set_progress, done, rev_total
                )

            self.app.call_from_thread(
                self._set_step, 2, "active", f"0/{len(to_deep)}"
            )
            reviewed = deep_reviewer.review_papers(
                to_deep,
                full_texts,
                api_base,
                api_key,
                model,
                on_progress=on_review_progress,
            )
            self.app.call_from_thread(
                self._set_step, 2, "done", f"{len(reviewed)} reviewed"
            )

            self.app.call_from_thread(
                self._set_step, 3, "active", ""
            )
            markdown_content = formatter_mod.format_to_markdown(
                reviewed, api_base, api_key, model
            )
            import pyperclip
            pyperclip.copy(markdown_content)
            self.app.call_from_thread(
                self._set_step, 3, "done", "Copied to clipboard"
            )

            self.app.call_from_thread(self.dismiss, "clipboard")
        except Exception as exc:
            self.app.call_from_thread(
                self._show_error, f"Report failed: {exc}"
            )
            self.app.call_from_thread(self.dismiss, None)

    def _show_error(self, msg: str) -> None:
        self.query_one("#error-msg", Static).update(
            Text(f"  {msg}", style="red")
        )

    def action_cancel(self) -> None:
        self.workers.cancel_all()
        self.dismiss(None)
