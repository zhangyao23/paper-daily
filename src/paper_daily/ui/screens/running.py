from __future__ import annotations

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Footer, Static

from paper_daily.ui.widgets import Banner


class RunningScreen(Screen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, cfg: dict, keywords: list[str]) -> None:
        super().__init__()
        self.cfg = cfg
        self.keywords = keywords

    def compose(self) -> ComposeResult:
        yield Banner()
        with Container(id="running-container"):
            yield Static(
                f"  Fetching papers for: {', '.join(self.keywords)}",
                classes="section-label",
            )
            yield Static("", id="step-1")
            yield Static("", id="step-2")
            yield Static("", id="step-3")
            yield Static("", id="progress-bar")
            yield Static("", id="error-msg")
        yield Footer()

    def on_mount(self) -> None:
        self._set_step(1, "pending", "")
        self._set_step(2, "pending", "")
        self._set_step(3, "pending", "")
        self._run_pipeline()

    def _set_step(self, step: int, state: str, detail: str) -> None:
        labels = {
            1: "Searching arxiv",
            2: "Scoring relevance",
            3: "Summarizing papers",
        }
        label = labels[step]
        text = Text()
        if state == "done":
            text.append(f"  [{step}/3] {label}  ", style="green")
            text.append(detail, style="dim")
        elif state == "active":
            text.append(f"  [{step}/3] {label}  ", style="cyan")
            text.append(detail, style="cyan")
        else:
            text.append(f"  [{step}/3] {label}", style="dim")

        self.query_one(f"#step-{step}", Static).update(text)

    def _set_progress(self, current: int, total: int) -> None:
        if total == 0:
            return
        width = 30
        filled = int(width * current / total)
        pct = int(100 * current / total)
        text = Text()
        text.append("  ")
        text.append("#" * filled, style="green")
        text.append("-" * (width - filled), style="dim")
        text.append(f"  {pct}%", style="cyan")
        self.query_one("#progress-bar", Static).update(text)

    @work(thread=True)
    def _run_pipeline(self) -> None:
        from paper_daily.config import resolve_api_key
        from paper_daily.pipeline import arxiv, scorer, summarizer

        api_key = resolve_api_key(self.cfg)
        if not api_key:
            self.app.call_from_thread(self._show_error, "No API key found. Configure one via Settings or env var.")
            return

        llm = self.cfg.get("llm", {})
        feed = self.cfg.get("feed", {})
        api_base = llm.get("api_base", "")
        model = llm.get("model", "")
        time_window = feed.get("time_window", 24)
        top_n = feed.get("top_n", 10)
        detailed = feed.get("output_style", "compact") == "detailed"

        try:
            self.app.call_from_thread(
                self._set_step, 1, "active", f"{len(self.keywords)} keywords"
            )
            papers = arxiv.search(self.keywords, time_window)
            self.app.call_from_thread(
                self._set_step,
                1,
                "done",
                f"found {len(papers)} papers in the last {time_window}h",
            )

            if not papers:
                self.app.call_from_thread(
                    self._show_error, "No papers found for these keywords."
                )
                return

            total = len(papers)

            def on_score_progress(done: int, batch_total: int) -> None:
                self.app.call_from_thread(
                    self._set_step, 2, "active", f"{done}/{total}"
                )
                self.app.call_from_thread(self._set_progress, done, total)

            self.app.call_from_thread(
                self._set_step, 2, "active", f"0/{total}"
            )
            top_papers = scorer.score_papers(
                papers,
                self.keywords,
                api_base,
                api_key,
                model,
                top_n=top_n,
                on_progress=on_score_progress,
            )
            self.app.call_from_thread(
                self._set_step, 2, "done", f"top {len(top_papers)} selected"
            )

            summary_total = len(top_papers)

            def on_summary_progress(done: int, _total: int) -> None:
                self.app.call_from_thread(
                    self._set_step, 3, "active", f"{done}/{summary_total}"
                )
                self.app.call_from_thread(
                    self._set_progress, done, summary_total
                )

            self.app.call_from_thread(
                self._set_step, 3, "active", f"0/{summary_total}"
            )
            summarized = summarizer.summarize_papers(
                top_papers,
                api_base,
                api_key,
                model,
                detailed=detailed,
                on_progress=on_summary_progress,
            )
            self.app.call_from_thread(self._set_step, 3, "done", "complete")

            from paper_daily.core.calendar import record_session
            from paper_daily.config import HISTORY_FILE
            record_session(HISTORY_FILE)

            self.app.call_from_thread(self.dismiss, summarized)
        except Exception as exc:
            self.app.call_from_thread(self._show_error, f"Pipeline failed: {exc}")

    def _show_error(self, msg: str) -> None:
        self.query_one("#error-msg", Static).update(
            Text(f"  {msg}", style="red")
        )

    def action_cancel(self) -> None:
        self.workers.cancel_all()
        self.dismiss(None)
